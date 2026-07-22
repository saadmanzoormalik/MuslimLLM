from datetime import UTC, datetime
from typing import Any


def _cap(
    provider_id: str,
    display_name: str,
    status: str = "secure_import",
    methods: list[str] | None = None,
    conversations: str = "partial",
    projects: str = "inferred",
    files: str = "partial",
) -> dict[str, Any]:
    return {
        "provider_id": provider_id,
        "display_name": display_name,
        "connection_methods": methods if methods is not None else ["official_export", "local_file"],
        "oauth_available": False,
        "conversation_history_api_available": False,
        "projects_api_available": False,
        "files_api_available": False,
        "memory_api_available": False,
        "incremental_sync_available": False,
        "verified_at": datetime.now(UTC).date().isoformat(),
        "integration_status": status,
        "capabilities": {
            "conversations": conversations,
            "projects": projects,
            "files": files,
            "memories": "review_required",
            "custom_instructions": "partial",
            "branches": "flattened",
        },
        "compact_status": {
            "direct": "Direct sync",
            "secure_import": "Secure import",
            "limited": "Limited sync",
            "coming_soon": "Coming soon",
        }.get(status, "Secure import"),
        "test_backed_direct_sync": False,
    }


PROVIDERS: dict[str, dict[str, Any]] = {
    "demo": {
        **_cap("demo", "Demo AI Account", "direct", methods=["broker_oauth"], conversations="full", projects="full", files="metadata"),
        "oauth_available": True,
        "conversation_history_api_available": True,
        "projects_api_available": True,
        "files_api_available": True,
        "verified_at": datetime.now(UTC).date().isoformat(),
        "test_backed_direct_sync": True,
        "development_only": True,
    },
    "chatgpt": _cap("chatgpt", "ChatGPT", files="partial"),
    "claude": _cap("claude", "Claude", projects="partial", files="partial"),
    "gemini": _cap("gemini", "Gemini", "limited", conversations="partial", projects="unavailable"),
    "copilot": _cap("copilot", "Microsoft Copilot", "limited", methods=[], conversations="partial", projects="unavailable"),
    "perplexity": _cap("perplexity", "Perplexity", "limited", methods=[], conversations="partial", projects="unavailable"),
    "deepseek": _cap("deepseek", "DeepSeek", "secure_import"),
    "grok": _cap("grok", "Grok", "limited", conversations="partial", projects="unavailable"),
    "qwen": _cap("qwen", "Qwen", "secure_import"),
    "glm": _cap("glm", "GLM", "secure_import"),
    "other": _cap("other", "Other AI", "secure_import"),
}


def provider_list() -> list[dict[str, Any]]:
    return list(PROVIDERS.values())


def get_provider(provider_id: str) -> dict[str, Any]:
    return PROVIDERS.get(provider_id, PROVIDERS["other"])


def update_provider(provider_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    current = dict(get_provider(provider_id))
    if updates.get("integration_status") == "direct" and not updates.get("test_backed_direct_sync"):
        raise ValueError("Direct sync requires verified official connector tests.")
    current.update({key: value for key, value in updates.items() if value is not None})
    PROVIDERS[provider_id] = current
    return current
