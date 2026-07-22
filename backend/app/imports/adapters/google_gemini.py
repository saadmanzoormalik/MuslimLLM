from .base import ProviderAdapter
from ..normalizer import normalize_json_or_text


class GeminiAdapter(ProviderAdapter):
    def __init__(self):
        super().__init__(
            provider_name="gemini",
            display_name="Gemini",
            supports_api_import=False,
            supports_file_import=True,
            supports_project_import=False,
            supports_attachment_import=True,
            preferred_import_mode="upload Google Takeout export",
            supported_data_types=("chats where available", "messages", "metadata when present"),
        )

    def parse_uploaded_export(self, filename: str, payload: bytes) -> dict:
        return normalize_json_or_text(filename, payload, provider="gemini")
