import base64
import hashlib
import json
import os

from cryptography.fernet import Fernet, InvalidToken


def _fernet() -> Fernet:
    secret = os.getenv("CONTEXT_SYNC_TOKEN_KEY", "local-dev-context-sync-key").encode()
    key = base64.urlsafe_b64encode(hashlib.sha256(secret).digest())
    return Fernet(key)


def encrypt_token(payload: dict) -> dict:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return {"ciphertext": _fernet().encrypt(raw).decode(), "alg": "fernet-v1"}


def decrypt_token(record: dict) -> dict:
    if not record or record.get("alg") != "fernet-v1" or "ciphertext" not in record:
        return {}
    try:
        return json.loads(_fernet().decrypt(record["ciphertext"].encode()).decode())
    except (InvalidToken, ValueError, json.JSONDecodeError):
        return {}


def redact_secret(value: str) -> str:
    return value[:4] + "..." if value else ""
