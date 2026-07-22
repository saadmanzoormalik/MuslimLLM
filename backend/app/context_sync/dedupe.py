from .provenance import content_hash


def conversation_fingerprint(provider_id: str, conversation: dict) -> str:
    return content_hash({"provider": provider_id, "source_id": conversation.get("source_id"), "title": conversation.get("title"), "messages": conversation.get("messages", [])})

