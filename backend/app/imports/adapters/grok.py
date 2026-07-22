from .base import ProviderAdapter
from ..normalizer import normalize_json_or_text


class GrokAdapter(ProviderAdapter):
    def __init__(self):
        super().__init__(
            provider_name="grok",
            display_name="Grok",
            supports_api_import=False,
            supports_file_import=True,
            preferred_import_mode="generic JSON/Markdown upload",
            supported_data_types=("generic chats", "messages"),
        )

    def parse_uploaded_export(self, filename: str, payload: bytes) -> dict:
        return normalize_json_or_text(filename, payload, provider="grok")
