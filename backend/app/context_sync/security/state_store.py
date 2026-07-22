import hashlib
import json
from datetime import UTC, datetime, timedelta

from ...db import get_conn
from .token_vault import decrypt_token, encrypt_token


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def put_state(
    connection_id: str,
    state: str,
    code_verifier: str,
    nonce: str,
    redirect_uri: str,
    return_uri: str,
    ttl_seconds: int = 600,
) -> None:
    encrypted = encrypt_token({"code_verifier": code_verifier, "nonce": nonce})
    with get_conn() as conn:
        conn.execute(
            """
            update provider_connections
            set oauth_state_hash=%s,encrypted_oauth_state_json=%s::jsonb,oidc_nonce_hash=%s,
                oauth_redirect_uri=%s,return_uri=%s,state_expires_at=%s,updated_at=now()
            where id=%s
            """,
            (
                _digest(state),
                json.dumps(encrypted),
                _digest(nonce),
                redirect_uri,
                return_uri,
                datetime.now(UTC) + timedelta(seconds=ttl_seconds),
                connection_id,
            ),
        )


def pop_state(state: str) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            """
            update provider_connections
            set oauth_state_hash=null,state_expires_at=null,updated_at=now()
            where oauth_state_hash=%s and state_expires_at>now() and status='connecting'
            returning id,provider_id,encrypted_oauth_state_json,oauth_redirect_uri,return_uri
            """,
            (_digest(state),),
        ).fetchone()
    if not row:
        raise ValueError("Authorization state expired or invalid.")
    secrets = decrypt_token(row["encrypted_oauth_state_json"] or {})
    if not secrets.get("code_verifier") or not secrets.get("nonce"):
        raise ValueError("Authorization state could not be verified.")
    return {
        "connection_id": str(row["id"]),
        "provider_id": row["provider_id"],
        "code_verifier": secrets["code_verifier"],
        "nonce": secrets["nonce"],
        "redirect_uri": row["oauth_redirect_uri"],
        "return_uri": row["return_uri"],
    }
