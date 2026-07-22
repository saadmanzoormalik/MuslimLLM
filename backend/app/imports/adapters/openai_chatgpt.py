import json
import zipfile
from io import BytesIO

from .base import ProviderAdapter
from ..normalizer import normalize_chatgpt_export, normalize_json_payload


class ChatGPTAdapter(ProviderAdapter):
    def __init__(self):
        super().__init__(
            provider_name="chatgpt",
            display_name="ChatGPT",
            supports_api_import=False,
            supports_file_import=True,
            supports_project_import=False,
            supports_attachment_import=True,
            supports_memory_import=True,
            supports_chat_history_import=True,
            preferred_import_mode="upload export",
            supported_data_types=("chats", "messages", "custom instructions", "attachments when present"),
        )

    def parse_uploaded_export(self, filename: str, payload: bytes) -> dict:
        lower = filename.lower()
        if lower.endswith(".zip"):
            with zipfile.ZipFile(BytesIO(payload)) as archive:
                candidates = [name for name in archive.namelist() if name.endswith("conversations.json")]
                if candidates:
                    data = json.loads(archive.read(candidates[0]).decode("utf-8", errors="ignore"))
                    return normalize_chatgpt_export(data)
                json_files = [name for name in archive.namelist() if name.endswith(".json")]
                if json_files:
                    data = json.loads(archive.read(json_files[0]).decode("utf-8", errors="ignore"))
                    return normalize_json_payload(data, provider="chatgpt", source_name=filename)
        data = json.loads(payload.decode("utf-8", errors="ignore"))
        if isinstance(data, list) and data and "mapping" in data[0]:
            return normalize_chatgpt_export(data)
        return normalize_json_payload(data, provider="chatgpt", source_name=filename)
