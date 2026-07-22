from abc import ABC, abstractmethod

from ..providers.registry import get_provider
from ..schemas import (
    AuthorizationStart,
    CapabilityException,
    ContextInventory,
    ContextPage,
    ProviderConnection,
    SyncCheckpoint,
)


class ContextConnector(ABC):
    provider_id: str

    async def get_capabilities(self):
        return get_provider(self.provider_id)

    async def begin_connection(self, redirect_uri: str) -> AuthorizationStart:
        return await self.begin_authorization(redirect_uri)

    async def begin_authorization(self, redirect_uri: str) -> AuthorizationStart:
        raise CapabilityException(
            "DIRECT_HISTORY_SYNC_UNAVAILABLE",
            self.provider_id,
            "official_export",
            "Secure import is available for this provider.",
        )

    async def complete_authorization(self, code: str, code_verifier: str, state: str) -> ProviderConnection:
        raise CapabilityException("OAUTH_UNAVAILABLE", self.provider_id, "official_export", "Secure import is available for this provider.")

    async def complete_connection(self, authorization_result: dict) -> ProviderConnection:
        return await self.complete_authorization(
            authorization_result.get("code", ""),
            authorization_result.get("code_verifier", ""),
            authorization_result.get("state", ""),
        )

    async def discover_context(self, connection: ProviderConnection) -> ContextInventory:
        return ContextInventory(provider_id=self.provider_id)

    async def fetch_page(self, connection: ProviderConnection, cursor: str | None) -> ContextPage:
        raise CapabilityException("DIRECT_HISTORY_SYNC_UNAVAILABLE", self.provider_id, "official_export", "Secure import is available for this provider.")

    async def fetch_context_batch(self, connection: ProviderConnection, checkpoint: SyncCheckpoint | None = None) -> ContextPage:
        return await self.fetch_page(connection, checkpoint.cursor if checkpoint else None)

    async def refresh_incremental(self, connection: ProviderConnection, checkpoint: SyncCheckpoint) -> ContextPage:
        raise CapabilityException("INCREMENTAL_SYNC_UNAVAILABLE", self.provider_id, "manual_sync", "Manual secure import is available.")

    async def revoke(self, connection: ProviderConnection) -> None:
        return None

    async def revoke_connection(self, connection: ProviderConnection) -> None:
        await self.revoke(connection)

    @abstractmethod
    async def parse_official_export(self, local_path: str) -> ContextInventory:
        ...


class SecureImportConnector(ContextConnector):
    provider_id = "other"

    async def parse_official_export(self, local_path: str) -> ContextInventory:
        from pathlib import Path
        from zipfile import ZipFile

        from ...imports.normalizer import normalize_json_or_text

        path = Path(local_path)
        if path.suffix.lower() == ".zip":
            with ZipFile(path) as archive:
                safe_names = [
                    name for name in archive.namelist()
                    if not name.endswith("/") and Path(name).suffix.lower() in {".json", ".csv", ".txt", ".md"}
                ]
                if not safe_names:
                    raise ValueError("The selected official export does not contain supported conversation data.")
                preferred = next((name for name in safe_names if Path(name).name.lower() == "conversations.json"), safe_names[0])
                normalized = normalize_json_or_text(Path(preferred).name, archive.read(preferred), self.provider_id)
                normalized["files"] = [
                    {
                        "source_id": f"archive:{name}",
                        "name": Path(name).name,
                        "archive_path": name,
                        "preserved_as": "source_reference",
                    }
                    for name in safe_names
                    if name != preferred
                ]
        else:
            normalized = normalize_json_or_text(path.name, path.read_bytes(), self.provider_id)
        return ContextInventory(
            provider_id=self.provider_id,
            conversations_found=len(normalized.get("conversations", [])),
            projects_found=len(normalized.get("projects", [])),
            files_found=len(normalized.get("files", [])),
            estimated_seconds=max(15, len(normalized.get("conversations", [])) * 2),
            normalized=normalized,
        )


# Backwards-compatible name for existing imports while the public connector
# contract uses ContextConnector.
ContextProviderConnector = ContextConnector
