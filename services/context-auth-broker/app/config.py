import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("AUTH_BROKER_ENVIRONMENT", "development")
    public_url: str = os.getenv("AUTH_BROKER_PUBLIC_URL", "http://127.0.0.1:8100").rstrip("/")
    database_url: str = os.getenv("AUTH_BROKER_DATABASE_URL", "postgresql://saadmanzoor@127.0.0.1:5433/muslim_llm")
    encryption_key: str = os.getenv("AUTH_BROKER_ENCRYPTION_KEY", "development-broker-key-change-me")
    mock_provider_url: str = os.getenv("MOCK_CONTEXT_PROVIDER_URL", "http://127.0.0.1:8200").rstrip("/")
    token_ttl_seconds: int = int(os.getenv("CONTEXT_SYNC_TOKEN_TTL_SECONDS", "300"))
    state_ttl_seconds: int = int(os.getenv("CONTEXT_SYNC_STATE_TTL_SECONDS", "600"))
    allow_localhost_callbacks: bool = os.getenv("CONTEXT_SYNC_ALLOW_LOCALHOST_CALLBACKS", "true").lower() == "true"
    allow_mock_provider: bool = os.getenv("CONTEXT_SYNC_ALLOW_MOCK_PROVIDER", "true").lower() == "true"
    allowed_redirect_uris: tuple[str, ...] = tuple(filter(None, os.getenv("AUTH_BROKER_ALLOWED_REDIRECT_URIS", "muslimllm://context-sync/callback,http://127.0.0.1:8000/context-sync/device-callback/demo").split(",")))


settings = Settings()
