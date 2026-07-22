from __future__ import annotations

import asyncio
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.context_sync.service import create_job, create_upload_inventory, ensure_context_sync_ready, load_upload
from app.db import get_conn


@dataclass
class PreparedImport:
    job_id: str
    connection_id: str
    upload_token: str
    marker: str


def conversation(marker: str, index: int, *, project_id: str | None = None, orphan: bool = False) -> dict:
    root = f"{marker}-root-{index}"
    user = f"{marker}-user-{index}"
    assistant = f"{marker}-assistant-{index}"
    created = 1_700_000_000 + index * 60
    mapping = {
        root: {"id": root, "parent": None, "children": [user], "message": None},
        user: {
            "id": user,
            "parent": "missing-parent" if orphan else root,
            "children": [assistant],
            "message": {
                "id": f"message-user-{index}",
                "author": {"role": "user"},
                "create_time": created,
                "content": {"content_type": "text", "parts": [f"Help me continue objective {index} for {marker}."]},
                "metadata": {},
            },
        },
        assistant: {
            "id": assistant,
            "parent": user,
            "children": [],
            "message": {
                "id": f"message-assistant-{index}",
                "author": {"role": "assistant"},
                "create_time": created + 10,
                "content": {"content_type": "text", "parts": [f"Prior decision {index}: proceed with the documented plan."]},
                "metadata": {"model_slug": "exported-model"},
            },
        },
    }
    return {
        "id": f"{marker}-conversation-{index}",
        "title": f"{marker} conversation {index}",
        "create_time": created,
        "update_time": created + 20,
        "current_node": assistant,
        "mapping": mapping,
        "project_id": project_id,
        "project_title": "Imported Test Project" if project_id else None,
    }


def make_export(
    path: Path,
    *,
    conversation_count: int = 3,
    include_project: bool = True,
    include_file: bool = True,
    orphan: bool = False,
) -> tuple[Path, str]:
    marker = uuid4().hex
    project_id = f"{marker}-project" if include_project else None
    payload = [conversation(marker, index, project_id=project_id if index < 2 else None, orphan=orphan and index == 0) for index in range(conversation_count)]
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("conversations.json", json.dumps(payload))
        if include_file:
            archive.writestr("user-data/context-note.txt", f"Local export context for {marker}")
    return path, marker


def prepare_import(path: Path, *, transfer_method: str = "official_export_file_picker") -> PreparedImport:
    ensure_context_sync_ready()
    with path.open("rb") as handle:
        upload = UploadFile(file=handle, filename=path.name)
        prepared = asyncio.run(create_upload_inventory("chatgpt", upload))
    stored = load_upload(prepared["inventory"]["upload_token"])
    if not stored:
        raise AssertionError("The test export was not persisted")
    inventory = stored["inventory"]
    normalized = inventory.pop("normalized")
    marker = normalized["conversations"][0]["source_id"].split("-conversation-")[0]
    job_id = create_job(
        "chatgpt",
        stored["connection_id"],
        inventory,
        normalized,
        transfer_method=transfer_method,
    )
    return PreparedImport(
        job_id=job_id,
        connection_id=stored["connection_id"],
        upload_token=inventory["upload_token"],
        marker=marker,
    )


def cleanup_import(prepared: PreparedImport) -> None:
    with get_conn() as conn:
        conn.execute("delete from context_transfer_sessions where sync_job_id=%s", (prepared.job_id,))
        conn.execute("delete from chats where import_job_id=%s", (prepared.job_id,))
        conn.execute("delete from projects where import_job_id=%s", (prepared.job_id,))
        conn.execute("delete from sync_jobs where id=%s", (prepared.job_id,))
        conn.execute("delete from context_sync_uploads where id=%s", (prepared.upload_token,))
        conn.execute("delete from provider_connections where id=%s", (prepared.connection_id,))

