import base64
import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass

from cryptography.fernet import Fernet


ACCESS_COOKIE = "mllm_access"
REFRESH_COOKIE = "mllm_refresh"
ONBOARDING_COOKIE = "mllm_onboarding"
DEVICE_COOKIE = "mllm_device"


def secret_key() -> bytes:
    value = os.getenv("AUTH_SECRET_KEY", "local-development-auth-key-change-before-production")
    return value.encode("utf-8")


def token_hash(value: str) -> str:
    return hmac.new(secret_key(), value.encode("utf-8"), hashlib.sha256).hexdigest()


def opaque_token(size: int = 32) -> str:
    return secrets.token_urlsafe(size)


def numeric_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def encrypt_short_lived(value: str) -> str:
    key = base64.urlsafe_b64encode(hashlib.sha256(secret_key()).digest())
    return Fernet(key).encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_short_lived(value: str) -> str:
    key = base64.urlsafe_b64encode(hashlib.sha256(secret_key()).digest())
    return Fernet(key).decrypt(value.encode("ascii")).decode("utf-8")


def safe_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)


@dataclass(frozen=True)
class Principal:
    session_id: str
    kind: str
    subject_id: str
    email: str | None = None
    display_name: str | None = None

    @property
    def owner_column(self) -> str:
        return "user_id" if self.kind == "user" else "guest_id"
