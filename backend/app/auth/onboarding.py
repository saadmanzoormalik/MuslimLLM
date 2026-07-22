from datetime import UTC, datetime, timedelta

from fastapi import Request, Response

from ..db import get_conn
from .security import DEVICE_COOKIE, ONBOARDING_COOKIE, Principal, opaque_token, token_hash


ALLOWED = {
    "primary_use": {"everyday", "work", "learning", "islamic", "mixed"},
    "response_preference": {"concise", "balanced", "detailed"},
    "privacy_preference": {"local", "best"},
    "context_transfer_preference": {"transfer", "later"},
}


def _cookie(response: Response, value: str) -> None:
    secure = __import__("os").getenv("AUTH_SECURE_COOKIES", "false").lower() == "true"
    response.set_cookie(ONBOARDING_COOKIE, value, max_age=7 * 86400, httponly=True, secure=secure, samesite="lax", path="/")


def get_or_create(request: Request, response: Response) -> dict:
    raw = request.cookies.get(ONBOARDING_COOKIE)
    with get_conn() as conn:
        row = None
        if raw:
            row = conn.execute(
                "select * from temporary_onboarding_sessions where token_hash=%s and expires_at>now() and consumed_at is null",
                (token_hash(raw),),
            ).fetchone()
        if not row:
            raw = opaque_token(32)
            device = request.cookies.get(DEVICE_COOKIE) or opaque_token(18)
            row = conn.execute(
                """insert into temporary_onboarding_sessions (token_hash,device_id,expires_at)
                   values (%s,%s,%s) returning *""",
                (token_hash(raw), device, datetime.now(UTC) + timedelta(days=7)),
            ).fetchone()
            _cookie(response, raw)
    return row


def answer(request: Request, response: Response, key: str, value: str, step: int) -> dict:
    if key not in ALLOWED or value not in ALLOWED[key]:
        raise ValueError("Choose one of the available answers")
    row = get_or_create(request, response)
    with get_conn() as conn:
        return conn.execute(
            """update temporary_onboarding_sessions
               set answers_json=jsonb_set(answers_json,%s,to_jsonb(%s::text),true),current_step=%s,updated_at=now()
               where id=%s returning *""",
            ([key], value, min(step + 1, 3), row["id"]),
        ).fetchone()


def complete(request: Request, response: Response) -> dict:
    row = get_or_create(request, response)
    answers = dict(row["answers_json"] or {})
    answers.setdefault("response_preference", "balanced")
    required = {"primary_use", "response_preference", "privacy_preference"}
    if not required.issubset(answers):
        raise ValueError("Complete the three onboarding choices first")
    with get_conn() as conn:
        return conn.execute(
            "update temporary_onboarding_sessions set answers_json=%s::jsonb,completed=true,current_step=3,updated_at=now() where id=%s returning *",
            (__import__("json").dumps(answers), row["id"]),
        ).fetchone()


def attach_hash(conn, onboarding_hash: str, principal: Principal) -> None:
    row = conn.execute(
        "select * from temporary_onboarding_sessions where token_hash=%s and expires_at>now() and consumed_at is null",
        (onboarding_hash,),
    ).fetchone()
    if not row:
        return
    answers = row["answers_json"] or {}
    owner_column = principal.owner_column
    conn.execute(
        f"""insert into onboarding_profiles
           ({owner_column},primary_use,response_preference,privacy_preference,context_transfer_preference,completed,completed_at)
           values (%s,%s,%s,%s,%s,true,now())
           on conflict ({owner_column}) do update set primary_use=excluded.primary_use,
           response_preference=excluded.response_preference,privacy_preference=excluded.privacy_preference,
           context_transfer_preference=excluded.context_transfer_preference,completed=true,completed_at=now(),updated_at=now()""",
        (principal.subject_id, answers.get("primary_use"), answers.get("response_preference", "balanced"),
         answers.get("privacy_preference"), answers.get("context_transfer_preference", "later")),
    )
    conn.execute("update temporary_onboarding_sessions set consumed_at=now() where id=%s", (row["id"],))


def attach(conn, request: Request, principal: Principal) -> None:
    raw = request.cookies.get(ONBOARDING_COOKIE)
    if not raw:
        return
    attach_hash(conn, token_hash(raw), principal)


def profile(principal: Principal) -> dict | None:
    with get_conn() as conn:
        return conn.execute(f"select * from onboarding_profiles where {principal.owner_column}=%s", (principal.subject_id,)).fetchone()
