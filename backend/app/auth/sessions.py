import os
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, Request, Response

from ..db import get_conn
from .audit import request_ip_hash
from .security import ACCESS_COOKIE, DEVICE_COOKIE, REFRESH_COOKIE, Principal, opaque_token, token_hash


def _minutes() -> int:
    return int(os.getenv("AUTH_ACCESS_TOKEN_MINUTES", "15"))


def _days() -> int:
    return int(os.getenv("AUTH_REFRESH_TOKEN_DAYS", "30"))


def _secure() -> bool:
    return os.getenv("AUTH_SECURE_COOKIES", "false").lower() == "true"


def _set_cookie(response: Response, key: str, value: str, max_age: int, httponly: bool = True) -> None:
    response.set_cookie(key, value, max_age=max_age, httponly=httponly, secure=_secure(), samesite="lax", path="/")


def clear_session_cookies(response: Response) -> None:
    for key in (ACCESS_COOKIE, REFRESH_COOKIE):
        response.delete_cookie(key, path="/", secure=_secure(), samesite="lax")


def create_session(request: Request, response: Response, *, user_id: str | None = None, guest_id: str | None = None) -> Principal:
    access = opaque_token(36)
    refresh = opaque_token(48)
    device_id = request.cookies.get(DEVICE_COOKIE) or opaque_token(18)
    now = datetime.now(UTC)
    access_expiry = now + timedelta(minutes=_minutes())
    refresh_expiry = now + timedelta(days=_days())
    with get_conn() as conn:
        row = conn.execute(
            """insert into auth_sessions
               (user_id,guest_id,session_token_hash,refresh_token_hash,device_id,user_agent,platform,ip_hash,access_expires_at,expires_at)
               values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) returning id""",
            (user_id, guest_id, token_hash(access), token_hash(refresh), device_id,
             request.headers.get("user-agent", "")[:500], request.headers.get("sec-ch-ua-platform", "")[:80],
             request_ip_hash(request), access_expiry, refresh_expiry),
        ).fetchone()
    _set_cookie(response, ACCESS_COOKIE, access, _minutes() * 60)
    _set_cookie(response, REFRESH_COOKIE, refresh, _days() * 86400)
    _set_cookie(response, DEVICE_COOKIE, device_id, 365 * 86400)
    return Principal(str(row["id"]), "user" if user_id else "guest", str(user_id or guest_id))


def optional_principal(request: Request) -> Principal | None:
    access = request.cookies.get(ACCESS_COOKIE)
    if not access:
        return None
    with get_conn() as conn:
        row = conn.execute(
            """select s.*,u.email,u.display_name,u.status,g.converted_user_id
               from auth_sessions s
               left join users u on u.id=s.user_id
               left join guest_accounts g on g.id=s.guest_id
               where s.session_token_hash=%s and s.revoked_at is null and s.access_expires_at>now() and s.expires_at>now()""",
            (token_hash(access),),
        ).fetchone()
        if not row:
            return None
        if row["user_id"] and row["status"] != "active":
            return None
        if row["guest_id"] and row["converted_user_id"]:
            return None
        conn.execute("update auth_sessions set last_seen_at=now() where id=%s", (row["id"],))
    return Principal(
        str(row["id"]), "user" if row["user_id"] else "guest", str(row["user_id"] or row["guest_id"]),
        row["email"], row["display_name"],
    )


def require_principal(principal: Principal | None = Depends(optional_principal)) -> Principal:
    if not principal:
        raise HTTPException(status_code=401, detail="Your session has expired. Sign in again")
    return principal


def rotate_session(request: Request, response: Response) -> Principal:
    refresh = request.cookies.get(REFRESH_COOKIE)
    if not refresh:
        raise HTTPException(status_code=401, detail="Your session has expired. Sign in again")
    digest = token_hash(refresh)
    with get_conn() as conn:
        replay = conn.execute(
            "select id,user_id,guest_id from auth_sessions where previous_refresh_token_hash=%s and revoked_at is null",
            (digest,),
        ).fetchone()
        if replay:
            column = "user_id" if replay["user_id"] else "guest_id"
            subject = replay["user_id"] or replay["guest_id"]
            conn.execute(f"update auth_sessions set revoked_at=now() where {column}=%s and revoked_at is null", (subject,))
            clear_session_cookies(response)
            raise HTTPException(status_code=401, detail="Your session was secured. Sign in again")
        row = conn.execute(
            """select s.*,u.email,u.display_name from auth_sessions s
               left join users u on u.id=s.user_id
               where s.refresh_token_hash=%s and s.revoked_at is null and s.expires_at>now() for update of s""",
            (digest,),
        ).fetchone()
        if not row:
            clear_session_cookies(response)
            raise HTTPException(status_code=401, detail="Your session has expired. Sign in again")
        new_access = opaque_token(36)
        new_refresh = opaque_token(48)
        access_expiry = datetime.now(UTC) + timedelta(minutes=_minutes())
        conn.execute(
            """update auth_sessions set session_token_hash=%s,previous_refresh_token_hash=refresh_token_hash,
               refresh_token_hash=%s,access_expires_at=%s,last_seen_at=now() where id=%s""",
            (token_hash(new_access), token_hash(new_refresh), access_expiry, row["id"]),
        )
    _set_cookie(response, ACCESS_COOKIE, new_access, _minutes() * 60)
    _set_cookie(response, REFRESH_COOKIE, new_refresh, _days() * 86400)
    return Principal(str(row["id"]), "user" if row["user_id"] else "guest", str(row["user_id"] or row["guest_id"]), row["email"], row["display_name"])


def revoke_current(principal: Principal, response: Response) -> None:
    with get_conn() as conn:
        conn.execute("update auth_sessions set revoked_at=now() where id=%s", (principal.session_id,))
    clear_session_cookies(response)


def revoke_all(principal: Principal, response: Response) -> None:
    with get_conn() as conn:
        conn.execute(f"update auth_sessions set revoked_at=now() where {principal.owner_column}=%s and revoked_at is null", (principal.subject_id,))
    clear_session_cookies(response)
