import base64
import hashlib
import json
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

from ..config import settings


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.encryption_key.encode()).digest())
    return Fernet(key)


def encrypt_at_rest(payload: dict) -> dict:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return {"alg": "fernet-v1", "ciphertext": _fernet().encrypt(raw).decode()}


def decrypt_at_rest(record: dict) -> dict:
    if not record or record.get("alg") != "fernet-v1":
        raise ValueError("Encrypted broker record is invalid")
    try:
        return json.loads(_fernet().decrypt(record["ciphertext"].encode()).decode())
    except (InvalidToken, KeyError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("Encrypted broker record could not be opened") from exc


def encrypt_for_device(payload: dict, device_public_key: str, grant_id: str) -> dict:
    recipient = X25519PublicKey.from_public_bytes(_unb64(device_public_key))
    ephemeral = X25519PrivateKey.generate()
    shared = ephemeral.exchange(recipient)
    key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"muslim-llm-context-grant-v1").derive(shared)
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, json.dumps(payload, separators=(",", ":")).encode(), grant_id.encode())
    ephemeral_public = ephemeral.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return {"alg": "x25519-aesgcm-v1", "ephemeral_public_key": _b64(ephemeral_public), "nonce": _b64(nonce), "ciphertext": _b64(ciphertext)}
