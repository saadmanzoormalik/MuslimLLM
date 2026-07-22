from __future__ import annotations

import hashlib
import json
import mimetypes
import posixpath
import re
import stat
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from ..security.import_safety import scan_text


PARSER_VERSION = "openai_export_v2"
CONVERSATION_FILE = re.compile(r"(^|/)conversations(?:-\d+)?\.json$|(^|/)\d+\.json$", re.I)
FORBIDDEN_SUFFIXES = {
    ".app", ".bat", ".cmd", ".command", ".com", ".dmg", ".dll", ".exe",
    ".jar", ".msi", ".pkg", ".ps1", ".scr", ".sh", ".vbs",
}
SCRIPT_SUFFIXES = {".js", ".mjs", ".cjs", ".py", ".rb", ".php"}


class ExportSecurityError(ValueError):
    pass


@dataclass
class OpenAIExport:
    archive_hash: str
    conversations: list[dict[str, Any]] = field(default_factory=list)
    nodes: list[dict[str, Any]] = field(default_factory=list)
    branches: list[dict[str, Any]] = field(default_factory=list)
    files: list[dict[str, Any]] = field(default_factory=list)
    exceptions: list[dict[str, Any]] = field(default_factory=list)
    account_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def inventory(self) -> dict[str, int]:
        return {
            "conversations_found": len(self.conversations),
            "messages_found": sum(len(item["messages"]) for item in self.conversations),
            "nodes_found": len(self.nodes),
            "branches_found": len(self.branches),
            "files_found": len(self.files),
            "exceptions": len(self.exceptions),
        }


def parse_openai_export(
    archive_path: str | Path,
    *,
    max_files: int = 10_000,
    max_uncompressed_bytes: int = 2 * 1024 * 1024 * 1024,
    max_compression_ratio: float = 200.0,
) -> OpenAIExport:
    path = Path(archive_path)
    if path.suffix.lower() != ".zip" or not zipfile.is_zipfile(path):
        raise ExportSecurityError("Select an official ChatGPT export ZIP.")
    result = OpenAIExport(archive_hash=_sha256_file(path))
    seen: set[tuple[str, str]] = set()
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        _validate_archive(members, max_files, max_uncompressed_bytes, max_compression_ratio)
        conversation_members = [item for item in members if not item.is_dir() and CONVERSATION_FILE.search(item.filename)]
        if not conversation_members:
            raise ExportSecurityError("This ZIP does not contain a supported ChatGPT conversations export.")

        for member in sorted(conversation_members, key=lambda item: (item.filename.lower() != "conversations.json", item.filename)):
            try:
                payload = json.loads(archive.read(member).decode("utf-8"))
                items = _conversation_items(payload)
                for index, raw in enumerate(items):
                    normalized, nodes, branches, exceptions = _normalize_conversation(raw, index, member.filename)
                    dedupe_key = (normalized["source_conversation_id"], normalized["content_hash"])
                    if dedupe_key in seen:
                        result.exceptions.append(_exception("duplicate_conversation", normalized["source_conversation_id"], member.filename, True))
                        continue
                    seen.add(dedupe_key)
                    result.conversations.append(normalized)
                    result.nodes.extend(nodes)
                    result.branches.extend(branches)
                    result.exceptions.extend(exceptions)
            except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
                result.exceptions.append(_exception("malformed_conversation_file", member.filename, str(exc), True))

        for member in members:
            if member.is_dir() or member in conversation_members:
                continue
            suffix = Path(member.filename).suffix.lower()
            raw = archive.read(member)
            mime = mimetypes.guess_type(member.filename)[0] or "application/octet-stream"
            status = "quarantined" if suffix in SCRIPT_SUFFIXES or _looks_executable(raw) else "scanned"
            result.files.append({
                "source_path": member.filename,
                "filename": PurePosixPath(member.filename).name,
                "size_bytes": member.file_size,
                "mime_type": mime,
                "content_hash": hashlib.sha256(raw).hexdigest(),
                "scan_status": status,
                "metadata": {"compressed_size": member.compress_size},
            })
            if status == "quarantined":
                result.exceptions.append(_exception("suspicious_file_quarantined", member.filename, "File was retained only as metadata and was not executed.", True))

    result.conversations.sort(key=lambda item: item.get("updated_at") or item.get("created_at") or "", reverse=True)
    return result


def _validate_archive(members: list[zipfile.ZipInfo], max_files: int, max_bytes: int, max_ratio: float) -> None:
    files = [item for item in members if not item.is_dir()]
    if len(files) > max_files:
        raise ExportSecurityError(f"Archive contains more than {max_files:,} files.")
    total = 0
    for member in files:
        normalized = posixpath.normpath(member.filename.replace("\\", "/"))
        if normalized.startswith("../") or normalized == ".." or normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized):
            raise ExportSecurityError("Archive path traversal was blocked.")
        mode = member.external_attr >> 16
        if stat.S_ISLNK(mode):
            raise ExportSecurityError("Archive symlinks are not allowed.")
        suffix = Path(normalized).suffix.lower()
        if suffix in FORBIDDEN_SUFFIXES:
            raise ExportSecurityError(f"Executable content is not allowed: {PurePosixPath(normalized).name}")
        total += member.file_size
        if total > max_bytes:
            raise ExportSecurityError("Archive exceeds the decompressed-size limit.")
        if member.file_size and member.file_size / max(member.compress_size, 1) > max_ratio:
            raise ExportSecurityError("Suspicious archive compression ratio was blocked.")


def _conversation_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        if isinstance(payload.get("conversations"), list):
            return [item for item in payload["conversations"] if isinstance(item, dict)]
        if "mapping" in payload or "conversation_id" in payload:
            return [payload]
    raise ValueError("Unsupported conversation JSON structure")


def _normalize_conversation(raw: dict[str, Any], index: int, source_file: str):
    source_id = str(raw.get("id") or raw.get("conversation_id") or f"openai-{index}")
    mapping = raw.get("mapping") if isinstance(raw.get("mapping"), dict) else {}
    current_node = str(raw.get("current_node") or "")
    active_ids = _active_path(mapping, current_node)
    active_set = set(active_ids)
    nodes: list[dict[str, Any]] = []
    branches: list[dict[str, Any]] = []
    exceptions: list[dict[str, Any]] = []

    for node_id, raw_node in mapping.items():
        if not isinstance(raw_node, dict):
            exceptions.append(_exception("malformed_node", str(node_id), source_id, True))
            continue
        message = raw_node.get("message") if isinstance(raw_node.get("message"), dict) else {}
        role = str((message.get("author") or {}).get("role") or "unknown").lower()
        content = _content_text(message.get("content"))
        timestamp = _timestamp(message.get("create_time"))
        metadata = message.get("metadata") if isinstance(message.get("metadata"), dict) else {}
        scan = scan_text(content)
        parent_id = raw_node.get("parent")
        children = [str(value) for value in (raw_node.get("children") or [])]
        node = {
            "source_conversation_id": source_id,
            "source_message_id": str(message.get("id") or node_id),
            "source_node_id": str(node_id),
            "parent_id": str(parent_id) if parent_id else None,
            "children": children,
            "role": role,
            "content": content,
            "source_timestamp": timestamp,
            "model_metadata": {"model_slug": metadata.get("model_slug"), "recipient": message.get("recipient")},
            "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "parser_version": PARSER_VERSION,
            "is_active": str(node_id) in active_set,
            "is_orphan": bool(parent_id and str(parent_id) not in mapping),
            "is_untrusted_instruction": role in {"system", "developer"} or not scan["safe"],
            "security_scan": scan,
            "raw_metadata": metadata,
            "attachments": metadata.get("attachments") or [],
            "citations": metadata.get("citations") or metadata.get("content_references") or [],
        }
        nodes.append(node)
        if node["is_orphan"]:
            exceptions.append(_exception("orphaned_node", str(node_id), source_id, True))
        if not scan["safe"]:
            exceptions.append(_exception("prompt_injection_signal", str(node_id), ", ".join(scan["matches"]), True))
        for child in children:
            branches.append({
                "source_conversation_id": source_id,
                "parent_node_id": str(node_id),
                "child_node_id": child,
                "is_active_branch": str(node_id) in active_set and child in active_set,
            })

    nodes_by_id = {item["source_node_id"]: item for item in nodes}
    messages = [nodes_by_id[node_id] for node_id in active_ids if node_id in nodes_by_id and nodes_by_id[node_id]["content"]]
    if not messages:
        messages = sorted([item for item in nodes if item["content"]], key=lambda item: item.get("source_timestamp") or "")
    project = raw.get("project") if isinstance(raw.get("project"), dict) else {}
    project_id = raw.get("project_id") or project.get("id")
    normalized = {
        "source_conversation_id": source_id,
        "title": str(raw.get("title") or "Untitled ChatGPT conversation")[:300],
        "created_at": _timestamp(raw.get("create_time")),
        "updated_at": _timestamp(raw.get("update_time")),
        "current_node_id": current_node or (active_ids[-1] if active_ids else None),
        "messages": messages,
        "message_count": len(messages),
        "node_count": len(nodes),
        "branch_count": len([item for item in branches if not item["is_active_branch"]]),
        "project_source_id": str(project_id) if project_id else None,
        "project_title": project.get("title") or raw.get("project_title"),
        "project_status": "provider_confirmed" if project_id else "unassigned",
        "source_file": source_file,
        "parser_version": PARSER_VERSION,
        "content_hash": _json_hash({"id": source_id, "mapping": mapping}),
        "raw_metadata": {key: raw.get(key) for key in ("conversation_template_id", "default_model_slug", "is_archived", "gizmo_id") if raw.get(key) is not None},
        "raw_source": raw,
        "attachments": [attachment for node in nodes for attachment in node.get("attachments", []) if isinstance(attachment, dict)],
    }
    return normalized, nodes, branches, exceptions


def _active_path(mapping: dict[str, Any], current_node: str) -> list[str]:
    target = current_node if current_node in mapping else ""
    if not target:
        leaves = [str(key) for key, value in mapping.items() if isinstance(value, dict) and not value.get("children")]
        target = leaves[-1] if leaves else (str(next(reversed(mapping))) if mapping else "")
    path: list[str] = []
    visited: set[str] = set()
    while target and target in mapping and target not in visited:
        visited.add(target)
        path.append(target)
        parent = mapping[target].get("parent") if isinstance(mapping[target], dict) else None
        target = str(parent) if parent else ""
    return list(reversed(path))


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, dict):
        return ""
    parts = content.get("parts")
    if isinstance(parts, list):
        rendered = []
        for part in parts:
            if isinstance(part, str):
                rendered.append(part)
            elif isinstance(part, dict):
                rendered.append(str(part.get("text") or part.get("content") or ""))
        return "\n".join(value for value in rendered if value).strip()
    return str(content.get("text") or content.get("result") or "").strip()


def _timestamp(value: Any) -> str | None:
    if value in (None, ""):
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=UTC).isoformat()
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).isoformat()
    except (ValueError, TypeError, OSError):
        return None


def _looks_executable(payload: bytes) -> bool:
    return payload.startswith((b"MZ", b"\x7fELF", b"#!"))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()


def _exception(kind: str, source_id: str, message: str, recoverable: bool) -> dict[str, Any]:
    return {"kind": kind, "source_id": source_id, "message": message[:1000], "recoverable": recoverable}
