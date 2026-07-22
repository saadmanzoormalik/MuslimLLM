import json
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Request

from ..config import settings
from ..database import get_conn
from ..oauth.pkce import pkce_pair
from ..oauth.state import new_state, state_hash
from ..providers.demo import authorization_url as demo_authorization_url
from ..providers.registry import PROVIDERS
from ..schemas import ConnectionStart
from ..security.audit import audit
from ..security.encryption import encrypt_at_rest
from ..security.rate_limits import enforce_rate_limit
from ..security.redirects import validate_device_callback


router = APIRouter(prefix="/v1/connections", tags=["connections"])


@router.post("/{provider}/start")
def start_connection(provider: str, payload: ConnectionStart, request: Request):
    enforce_rate_limit(request)
    definition = PROVIDERS.get(provider)
    if not definition:
        raise HTTPException(status_code=404, detail="Provider not found")
    if provider != "demo" or not definition.available:
        return {"connection_id": "", "authorization_url": "", "expires_at": None, "method": definition.method if definition else "unavailable"}

    try:
        callback = validate_device_callback(payload.device_callback_uri)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    state = new_state()
    verifier, challenge = pkce_pair()
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.state_ttl_seconds)
    transaction = encrypt_at_rest({"code_verifier": verifier, "device_state": payload.device_state})
    with get_conn() as conn:
        row = conn.execute(
            """
            insert into auth_broker_connections
              (provider_id,oauth_state_hash,encrypted_transaction_json,device_signing_public_key,
               device_encryption_public_key,device_callback_uri,platform,app_version,requested_capability,expires_at)
            values (%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s,%s)
            returning id
            """,
            (
                provider,
                state_hash(state),
                json.dumps(transaction),
                payload.device_signing_public_key,
                payload.device_encryption_public_key,
                callback,
                payload.platform,
                payload.app_version,
                payload.requested_capability,
                expires_at,
            ),
        ).fetchone()
    connection_id = str(row["id"])
    provider_callback = f"{settings.public_url}/v1/oauth/demo/callback"
    audit("connection_started", "success", provider, connection_id, details={"platform": payload.platform})
    return {
        "connection_id": connection_id,
        "authorization_url": demo_authorization_url(state, challenge, provider_callback),
        "expires_at": expires_at.isoformat(),
        "method": "oauth",
    }


@router.post("/{connection_id}/revoke")
def revoke_connection(connection_id: str):
    with get_conn() as conn:
        row = conn.execute(
            """
            update auth_broker_connections set status='revoked',revoked_at=now()
            where id=%s and status<>'revoked' returning provider_id
            """,
            (connection_id,),
        ).fetchone()
        conn.execute(
            "update auth_broker_grants set status='revoked',encrypted_token_json='{}'::jsonb where connection_id=%s and status='ready'",
            (connection_id,),
        )
    if not row:
        raise HTTPException(status_code=404, detail="Connection not found")
    audit("connection_revoked", "success", row["provider_id"], connection_id)
    return {"connection_id": connection_id, "status": "revoked"}
