from typing import Any


def estimate_coverage(normalized: dict[str, Any]) -> dict[str, Any]:
    conversations = normalized.get("conversations", [])
    projects = normalized.get("projects", [])
    files = normalized.get("files", [])
    preferences = normalized.get("preferences", [])
    message_count = sum(len(conversation.get("messages", [])) for conversation in conversations)
    attachment_count = sum(len(conversation.get("attachments", [])) for conversation in conversations)
    dimensions = {
        "Chats": 100 if conversations else 0,
        "Messages": 100 if message_count else 0,
        "Projects": 100 if projects else 35,
        "Files": 100 if files else 25,
        "Preferences": 100 if preferences else 35,
        "Metadata": metadata_score(conversations),
        "Attachments": 100 if attachment_count else 30,
        "Context summaries": 100 if conversations else 0,
    }
    overall = round(sum(dimensions.values()) / len(dimensions), 1)
    return {
        "overall": overall,
        "dimensions": dimensions,
        "detected": {
            "chats": len(conversations),
            "messages": message_count,
            "projects": len(projects),
            "files": len(files),
            "preferences": len(preferences),
            "attachments": attachment_count,
        },
        "unsupported_fields": normalized.get("unsupported_fields", []),
        "note": "Coverage measures available context imported locally. Some providers do not expose every field.",
    }


def metadata_score(conversations: list[dict[str, Any]]) -> int:
    if not conversations:
        return 0
    checks = 0
    total = 0
    for conversation in conversations:
        total += 3
        checks += 1 if conversation.get("created_at") else 0
        checks += 1 if conversation.get("updated_at") else 0
        checks += 1 if conversation.get("source_id") else 0
    return round((checks / max(total, 1)) * 100)
