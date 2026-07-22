from dataclasses import dataclass
from typing import Any


@dataclass
class ProviderAdapter:
    provider_name: str
    display_name: str
    supports_api_import: bool = False
    supports_file_import: bool = True
    supports_project_import: bool = False
    supports_attachment_import: bool = False
    supports_memory_import: bool = False
    supports_chat_history_import: bool = True
    preferred_import_mode: str = "upload export"
    supported_data_types: tuple[str, ...] = ("chats", "messages")

    def capability(self) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "display_name": self.display_name,
            "supports_api_import": self.supports_api_import,
            "supports_file_import": self.supports_file_import,
            "supports_project_import": self.supports_project_import,
            "supports_attachment_import": self.supports_attachment_import,
            "supports_memory_import": self.supports_memory_import,
            "supports_chat_history_import": self.supports_chat_history_import,
            "preferred_import_mode": self.preferred_import_mode,
            "supported_data_types": list(self.supported_data_types),
            "privacy_note": "Imported data stays local by default. Tokens are not stored after import.",
            "api_status": self.get_auth_url(),
        }

    def get_auth_url(self) -> dict[str, Any]:
        if not self.supports_api_import:
            return {
                "supported": False,
                "reason": "Provider does not expose full chat export API. Use uploaded export file instead.",
            }
        return {"supported": True, "url": None, "reason": "OAuth wiring placeholder for future official export API."}

    def exchange_auth_code(self, code: str | None) -> dict[str, Any]:
        return {"supported": False, "reason": "Official full account import is not implemented for this provider."}

    def fetch_available_exports(self) -> dict[str, Any]:
        return {"supported": False, "reason": "Use uploaded export files or paste import for this provider."}

    def parse_uploaded_export(self, filename: str, payload: bytes) -> dict[str, Any]:
        raise NotImplementedError

    def normalize_conversation(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload

    def normalize_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload

    def normalize_file(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload

    def estimate_coverage(self, normalized: dict[str, Any]) -> dict[str, Any]:
        return {}

    def revoke_credentials(self) -> dict[str, Any]:
        return {"revoked": True, "stored_credentials": False}
