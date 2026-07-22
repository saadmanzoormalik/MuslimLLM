import json
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from ..config import settings
from ..database import get_conn
from ..oauth.state import state_hash
from ..oauth.tokens import exchange_demo_code
from ..security.audit import audit
from ..security.encryption import decrypt_at_rest, encrypt_at_rest


router = APIRouter(prefix="/v1/oauth", tags=["oauth"])


@router.get("/{provider}/callback")
async def oauth_callback(provider: str, code: str | None = None, state: str | None = None, error: str | None = None):
    if provider != "demo" or error or not code or not state:
        raise HTTPException(status_code=400, detail="Authorization callback is invalid")
    with get_conn() as conn:
        row = conn.execute(
            """
            update auth_broker_connections
            set status='exchanging'
            where provider_id=%s and oauth_state_hash=%s and status='authorizing' and expires_at>now()
            returning *
            """,
            (provider, state_hash(state)),
        ).fetchone()
    if not row:
        audit("oauth_callback", "rejected", provider, details={"reason": "state"})
        raise HTTPException(status_code=400, detail="Authorization state expired or invalid")

    transaction = decrypt_at_rest(row["encrypted_transaction_json"])
    provider_callback = f"{settings.public_url}/v1/oauth/demo/callback"
    try:
        token = await exchange_demo_code(code, transaction["code_verifier"], provider_callback)
    except httpx.HTTPError as exc:
        with get_conn() as conn:
            conn.execute("update auth_broker_connections set status='failed' where id=%s", (row["id"],))
        audit("token_exchange", "failed", provider, str(row["id"]), details={"error": type(exc).__name__})
        raise HTTPException(status_code=502, detail="Provider token exchange failed") from exc

    grant_expires = datetime.now(UTC) + timedelta(seconds=settings.token_ttl_seconds)
    token_package = {
        "access_token": token["access_token"],
        "token_type": token.get("token_type", "Bearer"),
        "expires_in": token.get("expires_in"),
        "scope": token.get("scope", ""),
        "provider_api_base": f"{settings.mock_provider_url}/v1",
        "provider": provider,
    }
    encrypted_token = encrypt_at_rest(token_package)
    with get_conn() as conn:
        grant = conn.execute(
            """
            insert into auth_broker_grants
              (connection_id,provider_id,encrypted_token_json,device_signing_public_key,device_encryption_public_key,expires_at)
            values (%s,%s,%s::jsonb,%s,%s,%s) returning id
            """,
            (
                row["id"],
                provider,
                json.dumps(encrypted_token),
                row["device_signing_public_key"],
                row["device_encryption_public_key"],
                grant_expires,
            ),
        ).fetchone()
        conn.execute("update auth_broker_connections set status='grant_ready',completed_at=now(),encrypted_transaction_json='{}'::jsonb where id=%s", (row["id"],))
    grant_id = str(grant["id"])
    audit("grant_created", "success", provider, str(row["id"]), grant_id)
    separator = "&" if "?" in row["device_callback_uri"] else "?"
    redirect = f"{row['device_callback_uri']}{separator}{urlencode({'grant_id': grant_id, 'state': transaction['device_state']})}"
    return RedirectResponse(redirect, status_code=303)
