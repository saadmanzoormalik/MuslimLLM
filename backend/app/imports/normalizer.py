import csv
import io
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROLE_MAP = {
    "human": "user",
    "user": "user",
    "assistant": "assistant",
    "ai": "assistant",
    "system": "system",
    "tool": "tool",
}


def normalize_json_or_text(filename: str, payload: bytes, provider: str) -> dict[str, Any]:
    suffix = Path(filename).suffix.lower()
    text = payload.decode("utf-8", errors="ignore")
    if suffix in {".md", ".txt"}:
        return normalize_markdown_transcript(text, provider=provider, title=filename)
    if suffix == ".csv":
        return normalize_csv_export(text, provider=provider, source_name=filename)
    data = json.loads(text)
    return normalize_json_payload(data, provider=provider, source_name=filename)


def normalize_json_payload(data: Any, provider: str, source_name: str = "export.json") -> dict[str, Any]:
    conversations = []
    projects = []
    preferences = []

    root = data
    if isinstance(data, dict):
        conversations_raw = data.get("conversations") or data.get("chats") or data.get("threads") or data.get("items") or []
        projects_raw = data.get("projects") or data.get("folders") or data.get("spaces") or []
        memories_raw = data.get("memories") or data.get("preferences") or data.get("custom_instructions") or []
    elif isinstance(data, list):
        conversations_raw = data
        projects_raw = []
        memories_raw = []
    else:
        conversations_raw = []
        projects_raw = []
        memories_raw = []

    for index, item in enumerate(conversations_raw):
        if not isinstance(item, dict):
            continue
        messages = item.get("messages") or item.get("mapping") or item.get("transcript") or []
        if isinstance(messages, dict):
            messages = chatgpt_mapping_to_messages(messages)
        conversations.append(
            {
                "source_id": str(item.get("id") or item.get("conversation_id") or item.get("uuid") or f"{provider}-{index}"),
                "title": clean_title(item.get("title") or item.get("name") or source_name),
                "created_at": parse_timestamp(item.get("created_at") or item.get("create_time")),
                "updated_at": parse_timestamp(item.get("updated_at") or item.get("update_time")),
                "project_source_id": item.get("project_id") or item.get("folder_id") or item.get("space_id"),
                "messages": normalize_messages(messages),
                "attachments": item.get("attachments") or item.get("files") or [],
                "raw_metadata": safe_metadata(item),
            }
        )

    for index, item in enumerate(projects_raw):
        if not isinstance(item, dict):
            continue
        projects.append(
            {
                "source_id": str(item.get("id") or item.get("project_id") or item.get("folder_id") or f"{provider}-project-{index}"),
                "title": clean_title(item.get("title") or item.get("name") or "Imported Project"),
                "description": item.get("description") or "Imported context workspace",
                "raw_metadata": safe_metadata(item),
                "inferred": False,
            }
        )

    for item in memories_raw if isinstance(memories_raw, list) else [memories_raw]:
        if item:
            preferences.append(normalize_preference(item, provider))

    return {
        "provider": provider,
        "conversations": conversations,
        "projects": projects or infer_projects(conversations, provider),
        "files": [],
        "preferences": preferences,
        "unsupported_fields": unsupported_fields_for(provider),
        "raw_source_type": type(root).__name__,
    }


def normalize_chatgpt_export(data: list[dict[str, Any]]) -> dict[str, Any]:
    conversations = []
    preferences = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        mapping = item.get("mapping") or {}
        conversations.append(
            {
                "source_id": str(item.get("id") or f"chatgpt-{index}"),
                "title": clean_title(item.get("title") or "ChatGPT Import"),
                "created_at": parse_timestamp(item.get("create_time")),
                "updated_at": parse_timestamp(item.get("update_time")),
                "project_source_id": None,
                "messages": chatgpt_mapping_to_messages(mapping),
                "attachments": extract_chatgpt_attachments(mapping),
                "raw_metadata": {"source": "ChatGPT conversations.json", "conversation_id": item.get("id")},
            }
        )
    return {
        "provider": "chatgpt",
        "conversations": conversations,
        "projects": [],
        "files": [],
        "preferences": preferences,
        "unsupported_fields": ["Projects unavailable unless present in export.", "Hidden model memory unavailable.", "Deleted chats unavailable."],
        "raw_source_type": "chatgpt_conversations_json",
    }


def normalize_markdown_transcript(text: str, provider: str, title: str = "Imported transcript") -> dict[str, Any]:
    messages = []
    current_role = "user"
    current_lines: list[str] = []
    for line in text.splitlines():
        role_match = re.match(r"^\s*(user|human|assistant|ai|system|tool)\s*:\s*(.*)$", line, re.I)
        heading_match = re.match(r"^\s*#{1,3}\s*(user|human|assistant|ai|system|tool)\s*$", line, re.I)
        if role_match or heading_match:
            if current_lines:
                messages.append({"role": current_role, "content": "\n".join(current_lines).strip(), "created_at": None, "model": None, "attachments": [], "citations": [], "raw_metadata": {}})
            current_role = ROLE_MAP.get((role_match.group(1) if role_match else heading_match.group(1)).lower(), "unknown")
            current_lines = [role_match.group(2)] if role_match and role_match.group(2) else []
        else:
            current_lines.append(line)
    if current_lines:
        messages.append({"role": current_role, "content": "\n".join(current_lines).strip(), "created_at": None, "model": None, "attachments": [], "citations": [], "raw_metadata": {}})
    messages = [message for message in messages if message["content"]]
    if not messages and text.strip():
        messages = [{"role": "user", "content": text.strip(), "created_at": None, "model": None, "attachments": [], "citations": [], "raw_metadata": {}}]
    return {
        "provider": provider,
        "conversations": [
            {
                "source_id": stable_source_id(provider, title, text),
                "title": clean_title(title),
                "created_at": None,
                "updated_at": None,
                "project_source_id": None,
                "messages": messages,
                "attachments": [],
                "raw_metadata": {"source": "markdown_or_text"},
            }
        ],
        "projects": infer_projects([], provider),
        "files": [],
        "preferences": [],
        "unsupported_fields": ["Project relationships inferred only when folder data is unavailable.", "Provider memories unavailable from transcript."],
        "raw_source_type": "markdown",
    }


def normalize_csv_export(text: str, provider: str, source_name: str) -> dict[str, Any]:
    reader = csv.DictReader(io.StringIO(text))
    messages = []
    for row in reader:
        messages.append(
            {
                "role": ROLE_MAP.get((row.get("role") or "user").lower(), "unknown"),
                "content": row.get("content") or row.get("message") or "",
                "created_at": parse_timestamp(row.get("created_at")),
                "model": row.get("model"),
                "attachments": [],
                "citations": [],
                "raw_metadata": row,
            }
        )
    return {
        "provider": provider,
        "conversations": [
            {
                "source_id": stable_source_id(provider, source_name, text),
                "title": clean_title(source_name),
                "created_at": None,
                "updated_at": None,
                "project_source_id": None,
                "messages": [m for m in messages if m["content"]],
                "attachments": [],
                "raw_metadata": {"source": "csv"},
            }
        ],
        "projects": [],
        "files": [],
        "preferences": [],
        "unsupported_fields": ["Files, memories, citations, and project relationships unavailable unless included as columns."],
        "raw_source_type": "csv",
    }


def chatgpt_mapping_to_messages(mapping: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for node in mapping.values():
        message = node.get("message") if isinstance(node, dict) else None
        if not message:
            continue
        author = message.get("author", {})
        role = ROLE_MAP.get((author.get("role") or "unknown").lower(), "unknown")
        content = extract_content(message.get("content") or {})
        if not content:
            continue
        rows.append(
            {
                "role": role,
                "content": content,
                "created_at": parse_timestamp(message.get("create_time")),
                "model": message.get("metadata", {}).get("model_slug"),
                "attachments": message.get("metadata", {}).get("attachments") or [],
                "citations": [],
                "raw_metadata": safe_metadata(message.get("metadata") or {}),
            }
        )
    return rows


def normalize_messages(messages: Any) -> list[dict[str, Any]]:
    normalized = []
    if isinstance(messages, str):
        return [{"role": "user", "content": messages, "created_at": None, "model": None, "attachments": [], "citations": [], "raw_metadata": {}}]
    if not isinstance(messages, list):
        return []
    for message in messages:
        if isinstance(message, str):
            normalized.append({"role": "user", "content": message, "created_at": None, "model": None, "attachments": [], "citations": [], "raw_metadata": {}})
            continue
        if not isinstance(message, dict):
            continue
        role = ROLE_MAP.get(str(message.get("role") or message.get("author") or "unknown").lower(), "unknown")
        content = message.get("content") or message.get("text") or message.get("message") or ""
        if isinstance(content, dict):
            content = extract_content(content)
        if not str(content).strip():
            continue
        normalized.append(
            {
                "role": role,
                "content": str(content),
                "created_at": parse_timestamp(message.get("created_at") or message.get("timestamp")),
                "model": message.get("model") or message.get("model_name"),
                "attachments": message.get("attachments") or message.get("files") or [],
                "citations": message.get("citations") or message.get("sources") or [],
                "raw_metadata": safe_metadata(message),
            }
        )
    return normalized


def extract_content(content: dict[str, Any]) -> str:
    parts = content.get("parts")
    if isinstance(parts, list):
        return "\n".join(str(part) for part in parts if isinstance(part, str)).strip()
    text = content.get("text")
    if isinstance(text, str):
        return text
    return ""


def extract_chatgpt_attachments(mapping: dict[str, Any]) -> list[dict[str, Any]]:
    attachments = []
    for node in mapping.values():
        message = node.get("message") if isinstance(node, dict) else None
        metadata = (message or {}).get("metadata") or {}
        attachments.extend(metadata.get("attachments") or [])
    return attachments


def normalize_preference(item: Any, provider: str) -> dict[str, Any]:
    if isinstance(item, dict):
        content = item.get("content") or item.get("text") or item.get("memory") or json.dumps(item, ensure_ascii=True)
        preference_type = item.get("type") or "memory"
        confidence = item.get("confidence_level") or "medium"
        raw = item
    else:
        content = str(item)
        preference_type = "memory"
        confidence = "low"
        raw = {"value": content}
    return {
        "preference_type": preference_type if preference_type in {"memory", "custom_instruction", "tone", "domain_preference", "identity", "other"} else "other",
        "content": content,
        "confidence_level": confidence,
        "source_provider": provider,
        "raw_metadata": raw,
    }


def infer_projects(conversations: list[dict[str, Any]], provider: str) -> list[dict[str, Any]]:
    buckets: dict[str, int] = {}
    for conversation in conversations:
        title = conversation.get("title", "")
        topic = re.sub(r"[^a-zA-Z0-9 ]", "", title).split(" ")[:2]
        key = " ".join(topic).strip() or "Imported Context"
        buckets[key] = buckets.get(key, 0) + 1
    if not conversations or len(conversations) < 4:
        return []
    return [
        {
            "source_id": f"{provider}-inferred-{index}",
            "title": f"{title} Context",
            "description": "AI-inferred project from imported chat titles.",
            "raw_metadata": {"inferred": True, "conversation_count": count},
            "inferred": True,
        }
        for index, (title, count) in enumerate(buckets.items())
        if count >= 2
    ][:5]


def parse_timestamp(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC).isoformat()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
        except ValueError:
            return None
    return None


def clean_title(value: Any) -> str:
    title = re.sub(r"\s+", " ", str(value or "Imported chat")).strip()
    return title[:120] or "Imported chat"


def safe_metadata(item: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in item.items() if key not in {"content", "messages", "mapping"}}


def stable_source_id(provider: str, title: str, text: str) -> str:
    import hashlib

    return provider + "-" + hashlib.sha256((title + "\n" + text[:5000]).encode("utf-8")).hexdigest()[:16]


def unsupported_fields_for(provider: str) -> list[str]:
    defaults = ["Hidden system prompts unavailable.", "Deleted chats unavailable.", "Private provider metadata unavailable."]
    if provider == "generic_json":
        return ["Unsupported fields depend on export shape. Missing fields are marked unavailable."] + defaults
    return defaults
