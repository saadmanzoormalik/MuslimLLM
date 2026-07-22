from urllib.parse import urlparse

from ..config import settings


def validate_device_callback(uri: str) -> str:
    parsed = urlparse(uri)
    if uri in settings.allowed_redirect_uris:
        return uri
    if parsed.scheme == "muslimllm" and parsed.netloc == "context-sync" and parsed.path == "/callback":
        return uri
    if settings.environment == "development" and settings.allow_localhost_callbacks:
        if parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"} and parsed.path.startswith("/context-sync/device-callback/"):
            return uri
    raise ValueError("Device callback URI is not allowed")
