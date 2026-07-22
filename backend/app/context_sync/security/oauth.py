import base64
import hashlib
import secrets


def pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(40)).decode().rstrip("=")
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    return verifier, challenge


def new_state() -> str:
    return secrets.token_urlsafe(32)


def validate_state(expected: str, actual: str) -> None:
    if not expected or not actual or not secrets.compare_digest(expected, actual):
        raise ValueError("Invalid authorization state.")

