from .base import ProviderAdapter
from ..normalizer import normalize_json_or_text


class ClaudeAdapter(ProviderAdapter):
    def __init__(self):
        super().__init__(
            provider_name="claude",
            display_name="Claude",
            supports_api_import=False,
            supports_file_import=True,
            supports_project_import=True,
            supports_attachment_import=True,
            supports_memory_import=False,
            preferred_import_mode="upload export",
            supported_data_types=("chats", "messages", "projects/artifacts when present"),
        )

    def parse_uploaded_export(self, filename: str, payload: bytes) -> dict:
        return normalize_json_or_text(filename, payload, provider="claude")
