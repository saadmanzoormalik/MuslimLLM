import json
import tempfile
import hashlib
import os
from pathlib import Path

from fastapi import UploadFile

from ..db import get_conn
from .connectors import get_connector
from .models import init_context_sync_schema
from .providers.registry import get_provider, provider_list
from .security.archive_security import validate_archive_for_extraction


def ensure_context_sync_ready() -> None:
    with get_conn() as conn:
        init_context_sync_schema(conn)


async def create_upload_inventory(provider_id: str, file: UploadFile, connection_id: str | None = None) -> dict:
    connector = get_connector(provider_id)
    suffix = Path(file.filename or "export.json").suffix or ".json"
    maximum = int(os.getenv("CONTEXT_SYNC_MAX_ARCHIVE_BYTES", str(2 * 1024 * 1024 * 1024)))
    digest = hashlib.sha256()
    bytes_received = 0
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
        temp_path = handle.name
        while chunk := await file.read(1024 * 1024):
            bytes_received += len(chunk)
            if bytes_received > maximum:
                Path(temp_path).unlink(missing_ok=True)
                raise ValueError("archive_too_large")
            digest.update(chunk)
            handle.write(chunk)
    try:
        if suffix.lower() == ".zip" and provider_id == "chatgpt":
            archive_validation = validate_archive_for_extraction(Path(temp_path))
            if not archive_validation.valid:
                raise ValueError(archive_validation.code)
        inventory = await connector.parse_official_export(temp_path)
    finally:
        Path(temp_path).unlink(missing_ok=True)
    inventory_data = inventory.model_dump()
    normalized = inventory_data.pop("normalized", {})
    normalized["source_file_name"] = file.filename or "chatgpt-export.zip"
    normalized["archive_content_hash"] = digest.hexdigest()
    with get_conn() as conn:
        if connection_id:
            connection = conn.execute(
                """
                update provider_connections
                set auth_method='official_export',status='connected',updated_at=now()
                where id=%s and provider_id=%s
                returning id
                """,
                (connection_id, provider_id),
            ).fetchone()
        else:
            connection = None
        if not connection:
            connection = conn.execute(
                """
                insert into provider_connections (provider_id, display_name, auth_method, status)
                values (%s,%s,'official_export','connected')
                returning id
                """,
                (provider_id, get_provider(provider_id)["display_name"]),
            ).fetchone()
        upload = conn.execute(
            """
            insert into context_sync_uploads
              (provider_id, connection_id, file_name, inventory_json, payload_json, content_hash, byte_size)
            values (%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s)
            returning id
            """,
            (
                provider_id,
                connection["id"],
                file.filename,
                json.dumps(inventory_data, default=str),
                json.dumps(normalized, default=str),
                digest.hexdigest(),
                bytes_received,
            ),
        ).fetchone()
        conn.execute(
            "update context_sync_uploads set archive_path_reference=%s where id=%s",
            (f"upload://{upload['id']}", upload["id"]),
        )
    inventory_data["upload_token"] = str(upload["id"])
    return {"provider_id": provider_id, "connection_id": str(connection["id"]), "inventory": inventory_data}


def load_upload(upload_token: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("select * from context_sync_uploads where id=%s", (upload_token,)).fetchone()
    if not row:
        return None
    inventory = dict(row["inventory_json"] or {})
    inventory["normalized"] = row["payload_json"] or {}
    inventory["upload_token"] = str(row["id"])
    return {"provider_id": row["provider_id"], "connection_id": str(row["connection_id"]), "inventory": inventory}


def create_job(
    provider_id: str,
    connection_id: str | None,
    inventory: dict,
    normalized: dict,
    *,
    transfer_method: str | None = None,
) -> str:
    total = (inventory.get("conversations_found") or 0) + (inventory.get("projects_found") or 0) + (inventory.get("files_found") or 0)
    upload_token = inventory.get("upload_token")
    archive_reference = f"upload://{upload_token}" if upload_token else None
    archive_hash = normalized.get("archive_hash") or normalized.get("archive_content_hash")
    bytes_discovered = sum(int(item.get("size_bytes") or 0) for item in (normalized.get("files") or []))
    with get_conn() as conn:
        row = conn.execute(
            """
            insert into sync_jobs
              (provider_id, connection_id, status, stage, total, items_discovered,
               bytes_discovered, transfer_method, archive_path_reference, archive_hash,
               inventory_json, upload_payload_json)
            values (%s,%s,'authorized','authorized',%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)
            returning id
            """,
            (
                provider_id,
                connection_id,
                total,
                total,
                bytes_discovered,
                transfer_method,
                archive_reference,
                archive_hash,
                json.dumps(inventory, default=str),
                json.dumps(normalized, default=str),
            ),
        ).fetchone()
        conn.execute(
            "insert into sync_job_events (job_id, stage, status, total, message) values (%s,'authorized','authorized',%s,'Securely connected')",
            (row["id"], total),
        )
        if upload_token:
            conn.execute("update context_sync_uploads set status='consumed',consumed_at=now() where id=%s", (upload_token,))
    return str(row["id"])


def latest_status() -> dict:
    with get_conn() as conn:
        jobs = conn.execute("select * from sync_jobs order by created_at desc limit 5").fetchall()
    active = next((job for job in jobs if job["status"] in {"authorized", "running", "failed_recoverable", "paused_auth_required"}), None)
    return {"active_job": active, "recent_jobs": jobs}


def recover_pending_jobs() -> None:
    from .jobs.queue import enqueue_job

    with get_conn() as conn:
        rows = conn.execute(
            """
            select id from sync_jobs
            where status in ('authorized','running','failed_recoverable')
            order by created_at asc
            """
        ).fetchall()
    for row in rows:
        try:
            enqueue_job(str(row["id"]))
        except Exception as exc:
            with get_conn() as conn:
                conn.execute(
                    """
                    update sync_jobs
                    set status='failed_recoverable',display_message='Sync paused',last_error=%s,updated_at=now()
                    where id=%s
                    """,
                    (type(exc).__name__, row["id"]),
                )


def portable_export(provider_id: str | None = None) -> dict:
    with get_conn() as conn:
        params = (provider_id,) if provider_id else ()
        where = "where provider_id=%s" if provider_id else ""
        items = conn.execute(f"select * from normalized_context_items {where} order by imported_at desc limit 500", params).fetchall()
        packages = conn.execute("select * from continuity_packages order by created_at desc limit 500").fetchall()
    return {"format": "muslim_llm_context_archive_v1", "items": items, "continuity_packages": packages}
