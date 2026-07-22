from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from ..db import get_conn
from .jobs.queue import enqueue_job
from .service import create_job, create_upload_inventory, load_upload

_WATCH_TASKS: dict[str, asyncio.Task] = {}
ACTIVE_WATCH_STATUSES = {"watching", "validating", "syncing"}


def _choose_folder_macos() -> Path:
    if sys.platform != "darwin":
        raise RuntimeError("native_folder_picker_unavailable")
    script = 'POSIX path of (choose folder with prompt "Choose the folder where ChatGPT will download your export")'
    result = subprocess.run(
        ["osascript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode != 0:
        if "User canceled" in result.stderr:
            raise RuntimeError("folder_selection_cancelled")
        raise RuntimeError("folder_permission_unavailable")
    folder = Path(result.stdout.strip()).expanduser().resolve()
    if not folder.is_dir():
        raise RuntimeError("folder_permission_unavailable")
    return folder


def _archive_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def find_export_candidate(folder: Path, seen_hashes: set[str]) -> tuple[Path, str] | None:
    """Inspect only direct, regular ZIP children of the explicitly approved folder."""
    candidates = sorted(
        (
            item
            for item in folder.iterdir()
            if item.is_file() and not item.is_symlink() and item.suffix.lower() == ".zip"
        ),
        key=lambda item: (
            int("chatgpt" in item.name.lower() or "openai" in item.name.lower() or "export" in item.name.lower()),
            item.stat().st_mtime,
        ),
        reverse=True,
    )
    for candidate in candidates:
        digest = _archive_hash(candidate)
        if digest not in seen_hashes:
            return candidate, digest
    return None


def _public_watch(row: dict[str, Any] | None) -> dict | None:
    if not row:
        return None
    status = row["status"]
    messages = {
        "watching": "Waiting for your OpenAI export",
        "validating": "Reading your export",
        "syncing": "Syncing your ChatGPT context",
        "completed": "Context ready",
        "failed": "Export file not recognized",
        "revoked": "Folder access removed",
    }
    return {
        "id": str(row["id"]),
        "status": status,
        "display_message": messages.get(status, "Preparing your ChatGPT context"),
        "folder_name": row["folder_name"],
        "matched_file_name": row.get("matched_file_name"),
        "job_id": str(row["job_id"]) if row.get("job_id") else None,
        "recoverable": status in {"watching", "failed"},
    }


async def authorize_export_folder() -> dict:
    folder = await asyncio.to_thread(_choose_folder_macos)
    with get_conn() as conn:
        conn.execute(
            """
            update openai_export_folder_watches
            set status='revoked',revoked_at=now(),updated_at=now()
            where revoked_at is null and status in ('watching','validating','failed')
            """
        )
        row = conn.execute(
            """
            insert into openai_export_folder_watches (folder_path,folder_name,status)
            values (%s,%s,'watching') returning *
            """,
            (str(folder), folder.name or "Selected folder"),
        ).fetchone()
        conn.execute(
            """
            insert into sync_audit_log (provider_id,event_type,details_json)
            values ('chatgpt','openai_export_folder_authorized',%s::jsonb)
            """,
            (json.dumps({"watch_id": str(row["id"]), "folder_name": row["folder_name"]}),),
        )
    start_folder_watch(str(row["id"]))
    return _public_watch(row) or {}


def latest_folder_watch() -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "select * from openai_export_folder_watches order by authorized_at desc limit 1"
        ).fetchone()
        if row and row.get("job_id"):
            job = conn.execute("select status from sync_jobs where id=%s", (row["job_id"],)).fetchone()
            if job and job["status"] in {"completed", "completed_with_exceptions"} and row["status"] != "completed":
                row = conn.execute(
                    "update openai_export_folder_watches set status='completed',updated_at=now() where id=%s returning *",
                    (row["id"],),
                ).fetchone()
    return _public_watch(row)


def revoke_folder_watch(watch_id: str) -> dict:
    task = _WATCH_TASKS.pop(watch_id, None)
    if task:
        task.cancel()
    with get_conn() as conn:
        row = conn.execute(
            """
            update openai_export_folder_watches
            set status='revoked',revoked_at=now(),updated_at=now()
            where id=%s returning *
            """,
            (watch_id,),
        ).fetchone()
        if row:
            conn.execute(
                "insert into sync_audit_log (provider_id,event_type,details_json) values ('chatgpt','openai_export_folder_revoked',%s::jsonb)",
                (json.dumps({"watch_id": watch_id}),),
            )
    if not row:
        raise ValueError("folder_watch_not_found")
    return _public_watch(row) or {}


def revoke_all_folder_watches() -> int:
    for task in list(_WATCH_TASKS.values()):
        task.cancel()
    _WATCH_TASKS.clear()
    with get_conn() as conn:
        result = conn.execute(
            "update openai_export_folder_watches set status='revoked',revoked_at=now(),updated_at=now() where revoked_at is null"
        )
    return result.rowcount


def start_folder_watch(watch_id: str) -> None:
    existing = _WATCH_TASKS.get(watch_id)
    if existing and not existing.done():
        return
    _WATCH_TASKS[watch_id] = asyncio.create_task(_watch_folder_loop(watch_id))


async def recover_openai_folder_watches() -> None:
    with get_conn() as conn:
        rows = conn.execute(
            """
            select id,status,last_archive_hash,seen_archive_hashes_json from openai_export_folder_watches
            where revoked_at is null and status in ('watching','validating','failed')
            """
        ).fetchall()
    for row in rows:
        if row["status"] == "validating":
            seen = set(row["seen_archive_hashes_json"] or [])
            seen.discard(row.get("last_archive_hash"))
            with get_conn() as conn:
                conn.execute(
                    "update openai_export_folder_watches set status='watching',seen_archive_hashes_json=%s::jsonb,updated_at=now() where id=%s",
                    (json.dumps(sorted(seen)), row["id"]),
                )
        start_folder_watch(str(row["id"]))


async def _watch_folder_loop(watch_id: str) -> None:
    try:
        while True:
            with get_conn() as conn:
                row = conn.execute("select * from openai_export_folder_watches where id=%s", (watch_id,)).fetchone()
            if not row or row["revoked_at"] or row["status"] not in {"watching", "failed"}:
                return
            folder = Path(row["folder_path"])
            if not folder.is_dir():
                with get_conn() as conn:
                    conn.execute(
                        "update openai_export_folder_watches set status='failed',last_error_code='folder_unavailable',last_checked_at=now(),updated_at=now() where id=%s",
                        (watch_id,),
                    )
                await asyncio.sleep(3)
                continue
            seen = set(row["seen_archive_hashes_json"] or [])
            candidate = await asyncio.to_thread(find_export_candidate, folder, seen)
            if not candidate:
                with get_conn() as conn:
                    conn.execute("update openai_export_folder_watches set status='watching',last_checked_at=now(),updated_at=now() where id=%s", (watch_id,))
                await asyncio.sleep(2)
                continue
            path, archive_hash = candidate
            seen.add(archive_hash)
            with get_conn() as conn:
                conn.execute(
                    """
                    update openai_export_folder_watches
                    set status='validating',matched_file_name=%s,last_archive_hash=%s,
                        seen_archive_hashes_json=%s::jsonb,last_checked_at=now(),updated_at=now()
                    where id=%s
                    """,
                    (path.name, archive_hash, json.dumps(sorted(seen)), watch_id),
                )
            try:
                with path.open("rb") as handle:
                    upload = UploadFile(file=handle, filename=path.name)
                    prepared = await create_upload_inventory("chatgpt", upload)
                stored = load_upload(prepared["inventory"]["upload_token"])
                if not stored:
                    raise ValueError("import_preparation_failed")
                inventory = stored["inventory"]
                normalized = inventory.pop("normalized", {})
                job_id = create_job(
                    "chatgpt",
                    stored["connection_id"],
                    inventory,
                    normalized,
                    transfer_method="official_export_folder_watch",
                )
                with get_conn() as conn:
                    conn.execute(
                        "update openai_export_folder_watches set status='syncing',job_id=%s,last_error_code=null,updated_at=now() where id=%s",
                        (job_id, watch_id),
                    )
                if os.getenv("CONTEXT_SYNC_INLINE_JOBS", "true").lower() == "true":
                    asyncio.create_task(asyncio.to_thread(enqueue_job, job_id))
                return
            except (OSError, ValueError, json.JSONDecodeError):
                with get_conn() as conn:
                    conn.execute(
                        "update openai_export_folder_watches set status='failed',last_error_code='export_not_recognized',updated_at=now() where id=%s",
                        (watch_id,),
                    )
                await asyncio.sleep(2)
    finally:
        _WATCH_TASKS.pop(watch_id, None)
