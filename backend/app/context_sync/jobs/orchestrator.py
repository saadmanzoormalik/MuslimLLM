import json
import os
import time
from typing import Any

from psycopg import Connection

from ...db import get_conn
from ..continuity import build_continuity_package
from ..dedupe import conversation_fingerprint
from ..jobs.checkpoints import save_checkpoint
from ..jobs.notifications import notify_in_app
from ..jobs.progress import ThroughputEstimator
from ..provenance import content_hash
from ..security.import_safety import scan_text, wrap_untrusted_context

STAGES = [
    ("reading_conversations", "Reading conversations"),
    ("restoring_recent_chats", "Restoring recent chats"),
    ("recent_context_ready", "Recent context ready"),
    ("restoring_projects", "Restoring projects"),
    ("processing_files", "Processing files"),
    ("importing_older_history", "Importing older history"),
    ("building_working_context", "Building working context"),
    ("validating_transfer", "Validating transfer"),
    ("context_ready", "Context ready"),
]


def demo_pacing(provider_id: str) -> None:
    if provider_id == "demo":
        time.sleep(max(0, min(float(os.getenv("CONTEXT_SYNC_DEMO_STEP_DELAY", "0.08")), 0.25)))


def emit_progress(
    conn: Connection,
    job_id: str,
    stage: str,
    status: str,
    processed: int,
    total: int,
    message: str,
    eta: int | None = None,
    *,
    bytes_processed: int = 0,
    bytes_discovered: int = 0,
) -> None:
    percent = round((processed / max(total, 1)) * 100, 2)
    event_status = "active" if status == "running" else status
    conn.execute(
        """
        insert into sync_job_events (job_id, stage, status, processed, total, percent, estimated_seconds_remaining, message)
        values (%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (job_id, stage, event_status, processed, total, percent, eta, message),
    )
    conn.execute(
        """
        update sync_jobs set stage=%s,status=%s,processed=%s,total=%s,percent=%s,
          items_processed=%s,items_discovered=%s,bytes_processed=%s,
          bytes_discovered=greatest(bytes_discovered,%s),estimated_seconds_remaining=%s,
          display_message=%s,updated_at=now()
        where id=%s
        """,
        (
            stage,
            status,
            processed,
            total,
            percent,
            processed,
            total,
            bytes_processed,
            bytes_discovered,
            eta,
            message,
            job_id,
        ),
    )
    conn.commit()


def _persist_openai_raw(conn: Connection, job_id: str, normalized: dict[str, Any]) -> dict[str, int]:
    raw = normalized.get("openai_raw") or {}
    if not raw:
        return {"conversations": 0, "nodes": 0, "branches": 0, "exceptions": 0, "prompt_injection_flags": 0}
    archive_hash = raw.get("archive_hash") or normalized.get("archive_hash") or normalized.get("archive_content_hash") or "unknown"
    parser_version = raw.get("parser_version") or normalized.get("parser_version") or "openai_export_v1"
    files = normalized.get("files") or []
    conn.execute(
        """
        insert into openai_export_archives
          (job_id, archive_hash, file_name, file_count, decompressed_bytes, parser_version, integrity_status)
        values (%s,%s,%s,%s,%s,%s,'validated')
        on conflict (job_id) do nothing
        """,
        (
            job_id,
            archive_hash,
            normalized.get("source_file_name"),
            len(files),
            sum(int(item.get("size_bytes") or 0) for item in files),
            parser_version,
        ),
    )
    for index, raw_conversation in enumerate(raw.get("conversations") or []):
        source_id = str(raw_conversation.get("id") or raw_conversation.get("conversation_id") or f"openai-{index}")
        conn.execute(
            """
            insert into openai_raw_conversations
              (job_id, source_conversation_id, source_content_hash, archive_hash, parser_version, raw_json)
            values (%s,%s,%s,%s,%s,%s::jsonb)
            on conflict (job_id, source_conversation_id) do nothing
            """,
            (job_id, source_id, content_hash(raw_conversation), archive_hash, parser_version, json.dumps(raw_conversation, default=str)),
        )
    for node in raw.get("nodes") or []:
        conn.execute(
            """
            insert into openai_raw_message_nodes
              (job_id, source_conversation_id, source_message_id, source_node_id, source_parent_id,
               child_node_ids_json, role, raw_content, normalized_content, source_timestamp,
               source_content_hash, source_model_metadata_json, source_metadata_json, archive_hash,
               parser_version, is_active_branch, is_orphan, is_untrusted_instruction)
            values (%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s,%s,%s,%s)
            on conflict (job_id, source_conversation_id, source_node_id) do nothing
            """,
            (
                job_id,
                node.get("source_conversation_id"),
                node.get("source_message_id"),
                node.get("source_node_id"),
                node.get("parent_id"),
                json.dumps(node.get("children") or []),
                node.get("role"),
                node.get("content"),
                node.get("content"),
                node.get("source_timestamp"),
                node.get("content_hash"),
                json.dumps(node.get("model_metadata") or {}, default=str),
                json.dumps({**(node.get("raw_metadata") or {}), "attachments": node.get("attachments") or [], "citations": node.get("citations") or [], "security_scan": node.get("security_scan") or {}}, default=str),
                archive_hash,
                parser_version,
                bool(node.get("is_active")),
                bool(node.get("is_orphan")),
                bool(node.get("is_untrusted_instruction")),
            ),
        )
    for branch in raw.get("branches") or []:
        conn.execute(
            """
            insert into openai_conversation_branches
              (job_id, source_conversation_id, parent_node_id, child_node_id, is_active_branch, archive_hash, parser_version)
            values (%s,%s,%s,%s,%s,%s,%s)
            on conflict (job_id, source_conversation_id, parent_node_id, child_node_id) do nothing
            """,
            (job_id, branch.get("source_conversation_id"), branch.get("parent_node_id"), branch.get("child_node_id"), bool(branch.get("is_active_branch")), archive_hash, parser_version),
        )
    for item in raw.get("exceptions") or []:
        conn.execute(
            """
            insert into sync_exceptions
              (job_id, provider_id, item_type, source_object_id, user_message, error_class, recoverable)
            select %s,'chatgpt',%s,%s,%s,%s,%s
            where not exists (
              select 1 from sync_exceptions
              where job_id=%s and provider_id='chatgpt' and item_type=%s
                and source_object_id is not distinct from %s and error_class is not distinct from %s
            )
            """,
            (
                job_id,
                "openai_export",
                item.get("source_id"),
                "Some exported context could not be processed",
                item.get("kind"),
                bool(item.get("recoverable", True)),
                job_id,
                "openai_export",
                item.get("source_id"),
                item.get("kind"),
            ),
        )
    counts = {
        "conversations": len(raw.get("conversations") or []),
        "nodes": len(raw.get("nodes") or []),
        "branches": len(raw.get("branches") or []),
        "exceptions": len(raw.get("exceptions") or []),
        "prompt_injection_flags": sum(1 for item in (raw.get("exceptions") or []) if item.get("kind") == "prompt_injection_signal"),
    }
    conn.execute(
        "insert into sync_audit_log (job_id, provider_id, event_type, details_json) values (%s,'chatgpt','openai_raw_export_preserved',%s::jsonb)",
        (job_id, json.dumps(counts)),
    )
    conn.commit()
    return counts


def _run_sync_job_legacy(job_id: str) -> dict[str, Any]:
    with get_conn() as conn:
        job = conn.execute("select * from sync_jobs where id=%s", (job_id,)).fetchone()
        if not job:
            raise ValueError("Sync job not found.")
        normalized = job["upload_payload_json"] or {}
        provider_id = job["provider_id"]
        conversations = sorted(
            normalized.get("conversations", []),
            key=lambda item: item.get("updated_at") or item.get("created_at") or "",
            reverse=True,
        )
        projects = normalized.get("projects", [])
        files = normalized.get("files", [])
        total = max(len(conversations) + len(projects) + len(files) + len(conversations), 1)
        estimator = ThroughputEstimator(total)
        conn.execute("update sync_jobs set status='running', started_at=coalesce(started_at, now()) where id=%s", (job_id,))
        emit_progress(conn, job_id, "authorized", "running", 0, total, "Securely connected")
        raw_counts = _persist_openai_raw(conn, job_id, normalized) if provider_id == "chatgpt" else {"conversations": 0, "nodes": 0, "branches": 0, "exceptions": 0, "prompt_injection_flags": 0}

        project_map: dict[str, str] = {}
        processed = 0
        imported_projects = 0
        imported_conversations = 0
        continuity_count = 0
        duplicates_prevented = 0
        messages_retrieved = sum(len(conversation.get("messages", [])) for conversation in conversations)
        messages_created = 0
        files_created = 0

        emit_progress(conn, job_id, "inventory", "running", processed, total, "Reading conversations")
        save_checkpoint(conn, job_id, "inventory", processed, {"conversations": len(conversations), "projects": len(projects), "files": len(files)})

        emit_progress(conn, job_id, "creating_projects", "running", processed, total, "Restoring projects", estimator.remaining(processed))
        for project in projects:
            source_id = str(project.get("source_id") or content_hash(project))
            existing = conn.execute(
                """
                select item.local_object_id
                from normalized_context_items item
                join projects project on project.id=item.local_object_id
                where item.provider_id=%s and item.source_object_type='project' and item.source_object_id=%s
                """,
                (provider_id, source_id),
            ).fetchone()
            if existing and existing["local_object_id"]:
                project_map[source_id] = str(existing["local_object_id"])
                processed += 1
                emit_progress(conn, job_id, "creating_projects", "running", processed, total, "Restoring your projects", estimator.remaining(processed))
                continue
            row = conn.execute(
                """
                insert into projects (name, description, color, imported_from_provider, imported_at, import_job_id, import_inferred, import_metadata_json)
                values (%s,%s,'emerald',%s,now(),%s,%s,%s::jsonb)
                returning id
                """,
                (
                    project.get("title") or "Imported Project",
                    project.get("description") or "Imported context workspace",
                    provider_id,
                    job_id,
                    bool(project.get("inferred")),
                    json.dumps(project.get("raw_metadata") or {}, default=str),
                ),
            ).fetchone()
            project_map[source_id] = str(row["id"])
            conn.execute(
                """
                insert into normalized_context_items
                (job_id, provider_id, source_object_type, source_object_id, local_object_type, local_object_id, raw_metadata_json, content_hash, relationship_inferred)
                values (%s,%s,'project',%s,'project',%s,%s::jsonb,%s,%s)
                on conflict do nothing
                """,
                (job_id, provider_id, source_id, row["id"], json.dumps(project.get("raw_metadata") or {}, default=str), content_hash(project), bool(project.get("inferred"))),
            )
            imported_projects += 1
            processed += 1
            emit_progress(conn, job_id, "creating_projects", "running", processed, total, "Restoring your projects", estimator.remaining(processed))
            demo_pacing(provider_id)
        save_checkpoint(conn, job_id, "creating_projects", processed, {"project_map": project_map})

        for file_item in files:
            source_id = str(file_item.get("source_id") or file_item.get("id") or content_hash(file_item))
            result = conn.execute(
                """
                insert into normalized_context_items
                  (job_id, provider_id, source_object_type, source_object_id, local_object_type, raw_metadata_json, content_hash, parent_relationship_json)
                values (%s,%s,'file',%s,'reference',%s::jsonb,%s,%s::jsonb)
                on conflict do nothing
                """,
                (
                    job_id,
                    provider_id,
                    source_id,
                    json.dumps(file_item, default=str),
                    content_hash(file_item),
                    json.dumps({"conversation_source_id": file_item.get("conversation_source_id")}, default=str),
                ),
            )
            if result.rowcount:
                files_created += 1
            processed += 1
            emit_progress(conn, job_id, "creating_chats", "running", processed, total, "Processing your context", estimator.remaining(processed))
            demo_pacing(provider_id)

        emit_progress(conn, job_id, "creating_chats", "running", processed, total, "Restoring conversations", estimator.remaining(processed))
        for conversation in conversations:
            source_id = str(conversation.get("source_id") or content_hash(conversation))
            fingerprint = conversation_fingerprint(provider_id, conversation)
            existing = conn.execute(
                """
                select item.local_object_id
                from normalized_context_items item
                join chats chat on chat.id=item.local_object_id
                where item.provider_id=%s and item.source_object_type='conversation'
                  and (item.source_object_id=%s or item.content_hash=%s)
                """,
                (provider_id, source_id, fingerprint),
            ).fetchone()
            if existing and existing["local_object_id"]:
                duplicates_prevented += 1
                processed += 1
                emit_progress(conn, job_id, "creating_chats", "running", processed, total, "Skipping duplicate conversation", estimator.remaining(processed))
                continue
            source_project_id = conversation.get("project_source_id")
            project_id = project_map.get(str(source_project_id)) if source_project_id else None
            chat = conn.execute(
                """
                insert into chats
                  (title, model, project_id, imported_from_provider, imported_at, import_job_id, import_metadata_json, created_at, updated_at)
                values (%s,'imported-context',%s,%s,now(),%s,%s::jsonb,coalesce(%s::timestamptz,now()),coalesce(%s::timestamptz,%s::timestamptz,now()))
                returning id
                """,
                (
                    conversation.get("title") or "Imported conversation",
                    project_id,
                    provider_id,
                    job_id,
                    json.dumps(
                        {
                            **(conversation.get("raw_metadata") or {}),
                            "attachments": conversation.get("attachments") or [],
                            "source_badge": f"Imported from {provider_id}",
                        },
                        default=str,
                    ),
                    conversation.get("created_at"),
                    conversation.get("updated_at"),
                    conversation.get("created_at"),
                ),
            ).fetchone()
            local_chat_id = str(chat["id"])
            conn.execute(
                """
                update sync_jobs
                set ready_for_use=true,entry_chat_id=coalesce(entry_chat_id,%s),display_message='Processing your context',updated_at=now()
                where id=%s
                """,
                (local_chat_id, job_id),
            )
            messages = conversation.get("messages", [])
            for message in messages:
                role = message.get("role") if message.get("role") in {"user", "assistant", "system"} else "user"
                content = message.get("content") or ""
                safety = scan_text(content)
                if role == "system":
                    role = "user"
                    content = "[Imported provider system context]\n" + content
                if safety["quarantine"]:
                    content = "[Potential prompt-injection content marked as untrusted]\n" + content
                conn.execute(
                    """
                    insert into messages (chat_id, role, content, citations, model, created_at)
                    values (%s,%s,%s,%s::jsonb,%s,coalesce(%s::timestamptz, now()))
                    """,
                    (local_chat_id, role, wrap_untrusted_context(content, "ChatGPT") if provider_id == "chatgpt" else wrap_untrusted_context(content), json.dumps(message.get("citations") or []), message.get("model"), message.get("created_at")),
                )
                messages_created += 1
            conn.execute(
                """
                insert into normalized_context_items
                (job_id, provider_id, source_object_type, source_object_id, local_object_type, local_object_id, source_created_at, source_updated_at,
                 raw_metadata_json, content_hash, parent_relationship_json, relationship_inferred)
                values (%s,%s,'conversation',%s,'chat',%s,%s,%s,%s::jsonb,%s,%s::jsonb,%s)
                on conflict do nothing
                """,
                (
                    job_id,
                    provider_id,
                    source_id,
                    local_chat_id,
                    conversation.get("created_at"),
                    conversation.get("updated_at"),
                    json.dumps(conversation.get("raw_metadata") or {}, default=str),
                    fingerprint,
                    json.dumps({"project_source_id": source_project_id, "local_project_id": project_id}),
                    bool(project_id is None and source_project_id),
                ),
            )
            imported_conversations += 1
            processed += 1
            emit_progress(conn, job_id, "creating_chats", "running", processed, total, "Processing your context", estimator.remaining(processed))
            demo_pacing(provider_id)
        save_checkpoint(conn, job_id, "creating_chats", processed, {"imported_conversations": imported_conversations})

        emit_progress(conn, job_id, "building_continuity", "running", processed, total, "Preparing your workspace", estimator.remaining(processed))
        for conversation in conversations:
            source_id = str(conversation.get("source_id") or content_hash(conversation))
            item = conn.execute(
                """
                select item.local_object_id
                from normalized_context_items item
                join chats chat on chat.id=item.local_object_id
                where item.provider_id=%s and item.source_object_type='conversation' and item.source_object_id=%s
                """,
                (provider_id, source_id),
            ).fetchone()
            if not item or not item["local_object_id"]:
                continue
            package = build_continuity_package(provider_id, conversation, conversation.get("messages", []), str(item["local_object_id"]))
            conn.execute(
                """
                insert into continuity_packages (job_id, local_chat_id, source_provider, source_conversation_id, package_json, confidence)
                values (%s,%s,%s,%s,%s::jsonb,%s)
                on conflict (source_provider, source_conversation_id) do update set package_json=excluded.package_json, local_chat_id=excluded.local_chat_id
                """,
                (job_id, item["local_object_id"], provider_id, source_id, json.dumps(package, default=str), package["confidence"]),
            )
            continuity_count += 1
            processed += 1
            emit_progress(conn, job_id, "building_continuity", "running", processed, total, "Preparing your workspace", estimator.remaining(processed))
            demo_pacing(provider_id)
        save_checkpoint(conn, job_id, "building_continuity", processed, {"continuity_packages": continuity_count})

        validation_status = "passed" if imported_conversations + duplicates_prevented == len(conversations) else "passed_with_exceptions"
        status = "completed" if validation_status == "passed" else "completed_with_exceptions"
        report = {
            "provider": provider_id,
            "connection_id": str(job["connection_id"]) if job.get("connection_id") else None,
            "job_id": job_id,
            "conversations_retrieved": len(conversations),
            "conversations_detected": len(conversations),
            "conversations_created": imported_conversations,
            "conversations_imported": imported_conversations,
            "messages_retrieved": messages_retrieved,
            "messages_detected": messages_retrieved,
            "messages_created": messages_created,
            "messages_imported": messages_created,
            "projects_retrieved": len(projects),
            "projects_created": imported_projects,
            "projects_confirmed": sum(1 for item in projects if not item.get("inferred")),
            "projects_reconstructed": sum(1 for item in projects if item.get("inferred")),
            "files_retrieved": len(files),
            "files_detected": len(files),
            "files_created": files_created,
            "files_imported": files_created,
            "duplicates_prevented": duplicates_prevented,
            "branches_preserved": raw_counts["branches"],
            "malformed_items_skipped": raw_counts["exceptions"],
            "continuity_packages_generated": continuity_count,
            "prompt_injection_flags": raw_counts["prompt_injection_flags"],
            "archive_integrity_status": "validated" if provider_id == "chatgpt" else "not_applicable",
            "exceptions": raw_counts["exceptions"],
            "validation_status": validation_status,
        }
        conn.execute(
            """
            insert into sync_validation_reports (provider_id,connection_id,job_id,report_json,validation_status)
            values (%s,%s,%s,%s::jsonb,%s)
            on conflict (job_id) do update set report_json=excluded.report_json,validation_status=excluded.validation_status
            """,
            (provider_id, job.get("connection_id"), job_id, json.dumps(report), validation_status),
        )
        emit_progress(conn, job_id, "completed", status, total, total, "Your context is ready", 0)
        conn.execute("update sync_jobs set status=%s,stage='completed',processed=%s,total=%s,percent=100,display_message='Your context is ready',completed_at=now(),updated_at=now() where id=%s", (status, total, total, job_id))
        notify_in_app(conn, job_id, provider_id, "Your context is ready")
        return {"job_id": job_id, "status": status, "conversations": imported_conversations, "projects": imported_projects, "continuity_packages": continuity_count}


def run_sync_job(job_id: str) -> dict[str, Any]:
    from .progressive_import import run_progressive_sync_job

    return run_progressive_sync_job(job_id)
