import hashlib

import httpx

from ..imports.normalizer import normalize_json_payload
from .schemas import ContextInventory


async def fetch_provider_inventory(token_package: dict) -> tuple[ContextInventory, str]:
    access_token = token_package.get("access_token", "")
    api_base = token_package.get("provider_api_base", "").rstrip("/")
    if not access_token or not api_base:
        raise ValueError("Provider grant is missing retrieval credentials")
    headers = {"Authorization": f"Bearer {access_token}"}
    conversations: list[dict] = []
    cursor: int | None = 0
    async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
        me_response = await client.get(f"{api_base}/me", headers=headers)
        me_response.raise_for_status()
        account_id = str(me_response.json().get("id") or "unknown")
        while cursor is not None:
            response = await client.get(f"{api_base}/conversations", headers=headers, params={"cursor": cursor, "limit": 5})
            response.raise_for_status()
            page = response.json()
            conversations.extend(page.get("items", []))
            cursor = page.get("next_cursor")
        projects_response = await client.get(f"{api_base}/projects", headers=headers)
        projects_response.raise_for_status()
        files_response = await client.get(f"{api_base}/files", headers=headers)
        files_response.raise_for_status()

    projects = projects_response.json().get("items", [])
    files = files_response.json().get("items", [])
    normalized = normalize_json_payload(
        {"conversations": conversations, "projects": projects},
        provider="demo",
        source_name="Demo AI Account",
    )
    normalized["files"] = [
        {
            "source_id": str(item.get("id")),
            "name": item.get("name"),
            "content_type": item.get("content_type"),
            "size": item.get("size"),
            "conversation_source_id": item.get("conversation_id"),
            "preserved_as": "provider_reference",
        }
        for item in files
    ]
    inventory = ContextInventory(
        provider_id="demo",
        conversations_found=len(normalized["conversations"]),
        projects_found=len(normalized["projects"]),
        files_found=len(normalized["files"]),
        estimated_seconds=max(10, len(normalized["conversations"])),
        normalized=normalized,
    )
    return inventory, hashlib.sha256(account_id.encode()).hexdigest()
