import json

from .base import ProviderAdapter
from ..normalizer import normalize_json_payload


class GenericJsonAdapter(ProviderAdapter):
    def __init__(self):
        super().__init__(
            provider_name="generic_json",
            display_name="Generic JSON",
            supports_project_import=True,
            supports_memory_import=True,
            supports_attachment_import=True,
            preferred_import_mode="upload JSON",
            supported_data_types=("chats", "messages", "projects", "preferences", "metadata"),
        )

    def parse_uploaded_export(self, filename: str, payload: bytes) -> dict:
        data = json.loads(payload.decode("utf-8", errors="ignore"))
        return normalize_json_payload(data, provider="generic_json", source_name=filename)
