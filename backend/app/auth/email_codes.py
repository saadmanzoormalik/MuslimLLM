import os
import threading
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, Request

from ..db import get_conn
from .audit import request_ip_hash
from .rate_limits import enforce
from .security import numeric_code, token_hash


_mailbox: dict[str, tuple[str, datetime]] = {}
_lock = threading.Lock()


def normalize_email(email: str) -> str:
    local, _, domain = email.strip().partition("@")
    return f"{local.lower()}@{domain.encode('idna').decode('ascii').lower()}"


def _deliver(email: str, code: str) -> None:
    provider = os.getenv("AUTH_EMAIL_PROVIDER", "local").lower()
    if provider != "local":
        raise HTTPException(status_code=503, detail="Email sign-in is temporarily unavailable")
    with _lock:
        _mailbox[email] = (code, datetime.now(UTC))


def issue(request: Request, email: str, purpose: str = "sign_in") -> None:
    normalized = normalize_email(email)
    ip = request_ip_hash(request)
    enforce(f"email:{token_hash(normalized)}", 5, 600)
    enforce(f"email-ip:{ip}", 20, 600)
    ttl = int(os.getenv("AUTH_CODE_TTL_MINUTES", "10"))
    cooldown = int(os.getenv("AUTH_CODE_RESEND_SECONDS", "60"))
    with get_conn() as conn:
        latest = conn.execute(
            "select created_at from email_auth_codes where email_normalized=%s order by created_at desc limit 1",
            (normalized,),
        ).fetchone()
        if latest and latest["created_at"] > datetime.now(UTC) - timedelta(seconds=cooldown):
            raise HTTPException(status_code=429, detail="Wait a moment before requesting another code")
        code = numeric_code()
        conn.execute("update email_auth_codes set consumed_at=now() where email_normalized=%s and consumed_at is null", (normalized,))
        conn.execute(
            "insert into email_auth_codes (email_normalized,code_hash,purpose,expires_at) values (%s,%s,%s,%s)",
            (normalized, token_hash(f"{normalized}:{code}"), purpose, datetime.now(UTC) + timedelta(minutes=ttl)),
        )
    _deliver(normalized, code)


def verify(request: Request, email: str, code: str, purpose: str = "sign_in") -> str:
    normalized = normalize_email(email)
    enforce(f"verify-ip:{request_ip_hash(request)}", 30, 600)
    maximum = int(os.getenv("AUTH_CODE_MAX_ATTEMPTS", "5"))
    with get_conn() as conn:
        row = conn.execute(
            """select * from email_auth_codes where email_normalized=%s and purpose=%s
               and consumed_at is null order by created_at desc limit 1 for update""",
            (normalized, purpose),
        ).fetchone()
        if not row or row["expires_at"] <= datetime.now(UTC):
            raise HTTPException(status_code=400, detail="That code has expired")
        if row["attempts"] >= maximum:
            raise HTTPException(status_code=429, detail="Too many attempts. Request a new code")
        if token_hash(f"{normalized}:{code}") != row["code_hash"]:
            conn.execute("update email_auth_codes set attempts=attempts+1 where id=%s", (row["id"],))
            raise HTTPException(status_code=400, detail="That code is not correct")
        conn.execute("update email_auth_codes set consumed_at=now() where id=%s", (row["id"],))
    return normalized


def development_code(email: str) -> str | None:
    if os.getenv("AUTH_EMAIL_PROVIDER", "local").lower() != "local" or os.getenv("ENVIRONMENT", "development") == "production":
        return None
    with _lock:
        item = _mailbox.get(normalize_email(email))
    return item[0] if item else None
