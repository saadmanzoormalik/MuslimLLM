import base64
from datetime import UTC, datetime

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import APIRouter, HTTPException, Request

from ..database import get_conn
from ..schemas import GrantExchange
from ..security.audit import audit
from ..security.encryption import decrypt_at_rest, encrypt_for_device
from ..security.rate_limits import enforce_rate_limit


router = APIRouter(prefix="/v1/grants", tags=["grants"])


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


@router.post("/{grant_id}/exchange")
def exchange_grant(grant_id: str, payload: GrantExchange, request: Request):
    enforce_rate_limit(request)
    with get_conn() as conn:
        row = conn.execute("select * from auth_broker_grants where id=%s for update", (grant_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Grant not found")
        if row["status"] != "ready":
            raise HTTPException(status_code=409, detail="Grant has already been used")
        if row["expires_at"] <= datetime.now(UTC):
            conn.execute("update auth_broker_grants set status='expired',encrypted_token_json='{}'::jsonb where id=%s", (grant_id,))
            raise HTTPException(status_code=410, detail="Grant expired")
        if payload.device_signing_public_key != row["device_signing_public_key"]:
            raise HTTPException(status_code=403, detail="Grant is bound to another device")
        try:
            public_key = Ed25519PublicKey.from_public_bytes(_decode(payload.device_signing_public_key))
            public_key.verify(_decode(payload.signature), grant_id.encode())
        except (ValueError, InvalidSignature) as exc:
            raise HTTPException(status_code=403, detail="Device proof is invalid") from exc

        token_package = decrypt_at_rest(row["encrypted_token_json"])
        envelope = encrypt_for_device(token_package, row["device_encryption_public_key"], grant_id)
        conn.execute(
            "update auth_broker_grants set status='used',used_at=now(),encrypted_token_json='{}'::jsonb where id=%s",
            (grant_id,),
        )
    audit("grant_exchanged", "success", row["provider_id"], str(row["connection_id"]), grant_id)
    return {"grant_id": grant_id, "provider": row["provider_id"], "connection_id": str(row["connection_id"]), "token_envelope": envelope}
