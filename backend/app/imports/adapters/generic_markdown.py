from .base import ProviderAdapter
from ..normalizer import normalize_markdown_transcript


class GenericMarkdownAdapter(ProviderAdapter):
    def __init__(self):
        super().__init__(
            provider_name="generic_markdown",
            display_name="Generic Markdown",
            supports_project_import=True,
            preferred_import_mode="upload Markdown",
            supported_data_types=("chats", "messages", "projects"),
        )

    def parse_uploaded_export(self, filename: str, payload: bytes) -> dict:
        text = payload.decode("utf-8", errors="ignore")
        return normalize_markdown_transcript(text, provider="generic_markdown", title=filename)
