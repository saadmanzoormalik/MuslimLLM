import hashlib
import os
import re
from collections import defaultdict

from ..schemas import ContextInventory
from .base import SecureImportConnector
from .openai_export import PARSER_VERSION, parse_openai_export


class ChatGPTConnector(SecureImportConnector):
    provider_id = "chatgpt"

    async def parse_official_export(self, local_path: str) -> ContextInventory:
        parsed = parse_openai_export(local_path)
        conversations = []
        for item in parsed.conversations:
            conversations.append(
                {
                    "source_id": item["source_conversation_id"],
                    "title": item["title"],
                    "created_at": item["created_at"],
                    "updated_at": item["updated_at"],
                    "project_source_id": item.get("project_source_id"),
                    "messages": [
                        {
                            "source_message_id": message["source_message_id"],
                            "source_parent_id": message["parent_id"],
                            "role": message["role"],
                            "content": message["content"],
                            "created_at": message["source_timestamp"],
                            "model": message["model_metadata"].get("model_slug"),
                            "attachments": message.get("attachments") or [],
                            "citations": message.get("citations") or [],
                            "content_hash": message["content_hash"],
                            "raw_metadata": message["raw_metadata"],
                        }
                        for message in item["messages"]
                    ],
                    "attachments": item.get("attachments") or [],
                    "raw_metadata": {
                        **item["raw_metadata"],
                        "archive_hash": parsed.archive_hash,
                        "parser_version": PARSER_VERSION,
                        "current_node_id": item.get("current_node_id"),
                        "node_count": item["node_count"],
                        "alternate_branch_count": item["branch_count"],
                        "project_status": item["project_status"],
                        "source_content_hash": item["content_hash"],
                    },
                }
            )

        projects = _confirmed_projects(parsed.conversations)
        projects.extend(_reconstruct_projects(conversations))
        files = [
            {
                "source_id": f"archive:{item['source_path']}",
                "name": item["filename"],
                "archive_path": item["source_path"],
                "size_bytes": item["size_bytes"],
                "mime_type": item["mime_type"],
                "content_hash": item["content_hash"],
                "scan_status": item["scan_status"],
                "archive_hash": parsed.archive_hash,
                "preserved_as": "source_reference",
            }
            for item in parsed.files
        ]
        normalized = {
            "provider": self.provider_id,
            "conversations": conversations,
            "projects": projects,
            "files": files,
            "preferences": [],
            "raw_source_type": "official_chatgpt_export",
            "archive_hash": parsed.archive_hash,
            "parser_version": PARSER_VERSION,
            "openai_raw": {
                "archive_hash": parsed.archive_hash,
                "parser_version": PARSER_VERSION,
                "conversations": [item["raw_source"] for item in parsed.conversations],
                "nodes": parsed.nodes,
                "branches": parsed.branches,
                "exceptions": parsed.exceptions,
            },
        }
        return ContextInventory(
            provider_id=self.provider_id,
            conversations_found=len(conversations),
            projects_found=len(projects),
            files_found=len(files),
            estimated_seconds=max(5, len(conversations) // 8),
            normalized=normalized,
        )


def _confirmed_projects(conversations: list[dict]) -> list[dict]:
    grouped: dict[str, dict] = {}
    for item in conversations:
        source_id = item.get("project_source_id")
        if not source_id:
            continue
        project = grouped.setdefault(
            str(source_id),
            {
                "source_id": str(source_id),
                "title": item.get("project_title") or "Imported project",
                "description": "Imported from confirmed ChatGPT export metadata.",
                "raw_metadata": {"project_relationship_source": "provider_confirmed", "conversation_source_ids": []},
                "inferred": False,
            },
        )
        project["raw_metadata"]["conversation_source_ids"].append(item["source_conversation_id"])
    return list(grouped.values())


def _reconstruct_projects(conversations: list[dict]) -> list[dict]:
    confidence_threshold = float(os.getenv("CONTEXT_SYNC_PROJECT_CONFIDENCE_THRESHOLD", "0.80"))
    stopwords = {"about", "build", "create", "explain", "help", "make", "plan", "the", "this", "what", "with"}
    buckets: dict[str, list[dict]] = defaultdict(list)
    for item in conversations:
        if item.get("project_source_id"):
            continue
        tokens = [token for token in re.findall(r"[a-z0-9]+", item["title"].lower()) if len(token) > 3 and token not in stopwords]
        if len(tokens) >= 2:
            buckets[" ".join(tokens[:2])].append(item)
    projects = []
    for key, members in buckets.items():
        if len(members) < 3:
            continue
        source_id = "reconstructed:" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
        confidence = 0.85
        if confidence < confidence_threshold:
            continue
        for member in members:
            member["project_source_id"] = source_id
            member["raw_metadata"]["project_status"] = "reconstructed_high_confidence"
            member["raw_metadata"]["project_confidence"] = confidence
        projects.append(
            {
                "source_id": source_id,
                "title": key.title(),
                "description": "Reconstructed locally from recurring conversation goals.",
                "raw_metadata": {
                    "project_relationship_source": "reconstructed_high_confidence",
                    "confidence": confidence,
                    "conversation_source_ids": [member["source_id"] for member in members],
                },
                "inferred": True,
            }
        )
    return projects
