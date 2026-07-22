import os

from fastapi import HTTPException, Request, Response

from ..db import get_conn
from .onboarding import attach
from .security import Principal, opaque_token, token_hash
from .sessions import create_session


def public_principal(principal: Principal) -> dict:
    return {
        "authenticated": True,
        "account_type": principal.kind,
        "email": principal.email,
        "display_name": principal.display_name or ("Guest" if principal.kind == "guest" else None),
    }


def _new_user(conn, email: str | None, display_name: str | None, avatar_url: str | None, verified: bool) -> str:
    row = conn.execute(
        """insert into users (email,email_normalized,display_name,avatar_url,email_verified,status,last_login_at)
           values (%s,%s,%s,%s,%s,'active',now()) returning id""",
        (email, email, display_name, avatar_url, verified),
    ).fetchone()
    return str(row["id"])


def user_for_identity(provider: str, subject: str, email: str | None, email_verified: bool, display_name: str | None = None, avatar_url: str | None = None) -> str:
    with get_conn() as conn:
        identity = conn.execute(
            "select user_id from auth_identities where provider=%s and provider_subject=%s for update",
            (provider, subject),
        ).fetchone()
        if identity:
            conn.execute("update auth_identities set last_used_at=now() where provider=%s and provider_subject=%s", (provider, subject))
            conn.execute("update users set last_login_at=now(),updated_at=now() where id=%s", (identity["user_id"],))
            return str(identity["user_id"])

        user_id = None
        if provider == "email" and email_verified and email:
            existing = conn.execute("select id from users where email_normalized=%s and status='active' for update", (email,)).fetchone()
            user_id = str(existing["id"]) if existing else None
        stored_email = email
        if provider != "email" and email:
            collision = conn.execute("select id from users where email_normalized=%s", (email,)).fetchone()
            if collision:
                stored_email = None
        user_id = user_id or _new_user(conn, stored_email, display_name, avatar_url, email_verified)
        conn.execute(
            """insert into auth_identities
               (user_id,provider,provider_subject,provider_email,provider_email_verified)
               values (%s,%s,%s,%s,%s)""",
            (user_id, provider, subject, email, email_verified),
        )
        return user_id


def convert_guest(conn, guest_id: str, user_id: str) -> None:
    guest = conn.execute("select * from guest_accounts where id=%s for update", (guest_id,)).fetchone()
    if not guest:
        raise HTTPException(status_code=409, detail="Guest workspace could not be found")
    if guest["converted_user_id"] and str(guest["converted_user_id"]) != user_id:
        raise HTTPException(status_code=409, detail="Guest workspace was already transferred")
    conn.execute("update projects set user_id=%s,guest_id=null where guest_id=%s", (user_id, guest_id))
    conn.execute("update chats set user_id=%s,guest_id=null where guest_id=%s", (user_id, guest_id))
    rows = conn.execute("select key,value from user_settings where guest_id=%s", (guest_id,)).fetchall()
    for row in rows:
        conn.execute(
            """insert into user_settings (user_id,key,value) values (%s,%s,%s::jsonb)
               on conflict (user_id,key) where user_id is not null do update set value=excluded.value,updated_at=now()""",
            (user_id, row["key"], __import__("json").dumps(row["value"])),
        )
    profile = conn.execute("select * from onboarding_profiles where guest_id=%s", (guest_id,)).fetchone()
    if profile:
        conn.execute("delete from onboarding_profiles where user_id=%s", (user_id,))
        conn.execute("update onboarding_profiles set user_id=%s,guest_id=null,updated_at=now() where id=%s", (user_id, profile["id"]))
    conn.execute("update auth_sessions set revoked_at=now() where guest_id=%s and revoked_at is null", (guest_id,))
    conn.execute("update guest_accounts set converted_user_id=%s,converted_at=now() where id=%s", (user_id, guest_id))


def finish_user_auth(request: Request, response: Response, user_id: str, current: Principal | None = None) -> Principal:
    if current and current.kind == "guest":
        with get_conn() as conn:
            convert_guest(conn, current.subject_id, user_id)
    principal = create_session(request, response, user_id=user_id)
    with get_conn() as conn:
        attach(conn, request, principal)
        row = conn.execute("select email,display_name from users where id=%s", (user_id,)).fetchone()
    return Principal(principal.session_id, "user", user_id, row["email"], row["display_name"])


def create_guest(request: Request, response: Response, claim_existing: bool) -> Principal:
    guest_secret = opaque_token(36)
    device = request.cookies.get("mllm_device") or opaque_token(18)
    with get_conn() as conn:
        row = conn.execute(
            "insert into guest_accounts (guest_token_hash,device_id) values (%s,%s) returning id",
            (token_hash(guest_secret), device),
        ).fetchone()
        guest_id = str(row["id"])
        if claim_existing and os.getenv("AUTH_CLAIM_LEGACY_WORKSPACE", "true").lower() == "true":
            conn.execute("update projects set guest_id=%s where user_id is null and guest_id is null", (guest_id,))
            conn.execute("update chats set guest_id=%s where user_id is null and guest_id is null", (guest_id,))
    principal = create_session(request, response, guest_id=guest_id)
    with get_conn() as conn:
        attach(conn, request, principal)
    return principal
