import hashlib
import secrets


def new_state() -> str:
    return secrets.token_urlsafe(40)


def state_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()
