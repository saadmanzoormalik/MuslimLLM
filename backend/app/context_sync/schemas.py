from typing import Any

from pydantic import BaseModel, Field


class CapabilityException(Exception):
    def __init__(self, code: str, provider: str, fallback: str, user_message: str):
        self.payload = {"code": code, "provider": provider, "fallback": fallback, "user_message": user_message}
        super().__init__(user_message)


class AuthorizationStart(BaseModel):
    provider_id: str
    method: str
    authorization_url: str | None = None
    state: str | None = None
    code_verifier: str | None = None
    fallback: str = "official_export"
    user_message: str = "Secure import is available for this provider."


class ProviderConnection(BaseModel):
    id: str | None = None
    provider_id: str
    status: str = "connected"
    auth_method: str = "official_export"
    source_account_hash: str | None = None
    scopes: list[str] = []


class ContextInventory(BaseModel):
    provider_id: str
    conversations_found: int = 0
    projects_found: int = 0
    files_found: int = 0
    estimated_seconds: int = 30
    upload_token: str | None = None
    normalized: dict[str, Any] = Field(default_factory=dict)


class ContextPage(BaseModel):
    items: list[dict[str, Any]] = []
    next_cursor: str | None = None
    done: bool = True


class SyncCheckpoint(BaseModel):
    cursor: str | None = None
    processed: int = 0
    stage: str = "authorized"


class UploadResult(BaseModel):
    provider_id: str
    inventory: ContextInventory
    connection_id: str


class CreateJobRequest(BaseModel):
    provider_id: str
    connection_id: str | None = None
    upload_token: str | None = None
    auto_start: bool = True


class PortableExportRequest(BaseModel):
    provider_id: str | None = None
