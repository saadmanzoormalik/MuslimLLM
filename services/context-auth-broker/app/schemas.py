from pydantic import BaseModel, Field


class ConnectionStart(BaseModel):
    device_callback_uri: str = Field(max_length=500)
    device_signing_public_key: str = Field(min_length=20, max_length=500)
    device_encryption_public_key: str = Field(min_length=20, max_length=500)
    device_state: str = Field(min_length=24, max_length=500)
    platform: str = Field(max_length=40)
    app_version: str = Field(default="development", max_length=80)
    requested_capability: str = Field(default="context_sync", pattern="^context_sync$")


class GrantExchange(BaseModel):
    device_signing_public_key: str = Field(min_length=20, max_length=500)
    signature: str = Field(min_length=20, max_length=500)
