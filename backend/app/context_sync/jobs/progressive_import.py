from __future__ import annotations

import json
import os
from typing import Any

from psycopg import Connection

from ...db import get_conn
from ..continuity import build_continuity_package
from ..dedupe import conversation_fingerprint
from ..provenance import content_hash
from ..security.import_safety import scan_text, wrap_untrusted_context
from .checkpoints import save_checkpoint
from .notifications import notify_in_app
from .orchestrator import _persist_openai_raw, demo_pacing, emit_progress
from .progress import ThroughputEstimator


def _source_id(item: dict[str, Any]) -> str:
    return str(item.get("source_id") or item.get("source_conversation_id") or content_hash(item))


def _save_continuity(
    conn: Connection,
    job_id: str,
    provider_id: str,
    conversation: dict[str, Any],
    local_chat_id: str,
) -> dict[str, Any]:
    source_id = _source_id(conversation)
    package = build_continuity_package(provider_id, conversation, conversation.get("messages", []), local_chat_id)
    conn.execute(
        """
        insert into continuity_packages
          (job_id,local_chat_id,source_provider,source_conversation_id,package_json,confidence)
        values (%s,%s,%s,%s,%s::jsonb,%s)
        on conflict (source_provider,source_conversation_id) do update
        set job_id=excluded.job_id,local_chat_id=excluded.local_chat_id,
            package_json=excluded.package_json,confidence=excluded.confidence,created_at=now()
        """,
        (job_id, local_chat_id, provider_id, source_id, json.dumps(package, default=str), package["confidence"]),
    )
    return package


def _import_conversation(
    conn: Connection,
    job_id: str,
    provider_id: str,
    conversation: dict[str, Any],
    project_map: dict[str, str],
) -> dict[str, Any]:
    source_id = _source_id(conversation)
    fingerprint = conversation_fingerprint(provider_id, conversation)
    existing = conn.execute(
        """
        select item.local_object_id
        from normalized_context_items item
        join chats chat on chat.id=item.local_object_id
        where item.provider_id=%s and item.source_object_type='conversation'
          and (item.source_object_id=%s or item.content_hash=%s)
        order by item.imported_at desc limit 1
        """,
        (provider_id, source_id, fingerprint),
    ).fetchone()
    if existing and existing["local_object_id"]:
        local_chat_id = str(existing["local_object_id"])
        message_count = conn.execute("select count(*) as count from messages where chat_id=%s", (local_chat_id,)).fetchone()["count"]
        _save_continuity(conn, job_id, provider_id, conversation, local_chat_id)
        return {
            "chat_id": local_chat_id,
            "created": False,
            "duplicate": True,
            "messages_created": 0,
            "messages_available": int(message_count),
        }

    source_project_id = conversation.get("project_source_id")
    project_id = project_map.get(str(source_project_id)) if source_project_id else None
    chat = conn.execute(
        """
        insert into chats
          (title,model,project_id,imported_from_provider,imported_at,import_job_id,
           import_metadata_json,created_at,updated_at)
        values (%s,'imported-context',%s,%s,now(),%s,%s::jsonb,
                coalesce(%s::timestamptz,now()),
                coalesce(%s::timestamptz,%s::timestamptz,now()))
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
                    "source_conversation_id": source_id,
                    "imported_context_is_untrusted": True,
                },
                default=str,
            ),
            conversation.get("created_at"),
            conversation.get("updated_at"),
            conversation.get("created_at"),
        ),
    ).fetchone()
    local_chat_id = str(chat["id"])
    messages_created = 0
    for order, message in enumerate(conversation.get("messages") or []):
        role = message.get("role") if message.get("role") in {"user", "assistant", "system"} else "user"
        raw_content = message.get("content") or ""
        safety = scan_text(raw_content)
        content = raw_content
        if role == "system":
            role = "user"
            content = "[Imported provider system context]\n" + content
        if safety["quarantine"]:
            content = "[Potential prompt-injection content marked as untrusted]\n" + content
        source_timestamp = message.get("created_at")
        conn.execute(
            """
            insert into messages
              (chat_id,role,content,citations,model,created_at,import_job_id,
               source_message_id,source_timestamp,import_order,imported_untrusted)
            values (%s,%s,%s,%s::jsonb,%s,
                    coalesce(%s::timestamptz,%s::timestamptz + (%s * interval '1 microsecond'),now()),
                    %s,%s,%s::timestamptz,%s,true)
            """,
            (
                local_chat_id,
                role,
                wrap_untrusted_context(content, "ChatGPT") if provider_id == "chatgpt" else wrap_untrusted_context(content),
                json.dumps(message.get("citations") or []),
                message.get("model"),
                source_timestamp,
                conversation.get("created_at"),
                order,
                job_id,
                message.get("source_message_id"),
                source_timestamp,
                order,
            ),
        )
        messages_created += 1

    conn.execute(
        """
        insert into normalized_context_items
          (job_id,provider_id,source_object_type,source_object_id,local_object_type,
           local_object_id,source_created_at,source_updated_at,raw_metadata_json,
           content_hash,parent_relationship_json,relationship_inferred,parser_version)
        values (%s,%s,'conversation',%s,'chat',%s,%s,%s,%s::jsonb,%s,%s::jsonb,%s,%s)
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
            bool(source_project_id and not project_id),
            (conversation.get("raw_metadata") or {}).get("parser_version") or "openai_export_v2",
        ),
    )
    _save_continuity(conn, job_id, provider_id, conversation, local_chat_id)
    return {
        "chat_id": local_chat_id,
        "created": True,
        "duplicate": False,
        "messages_created": messages_created,
        "messages_available": messages_created,
    }


def _restore_project(
    conn: Connection,
    job_id: str,
    provider_id: str,
    project: dict[str, Any],
) -> tuple[str, bool]:
    source_id = _source_id(project)
    existing = conn.execute(
        """
        select item.local_object_id
        from normalized_context_items item
        join projects project on project.id=item.local_object_id
        where item.provider_id=%s and item.source_object_type='project' and item.source_object_id=%s
        order by item.imported_at desc limit 1
        """,
        (provider_id, source_id),
    ).fetchone()
    if existing and existing["local_object_id"]:
        local_id = str(existing["local_object_id"])
        return local_id, False
    row = conn.execute(
        """
        insert into projects
          (name,description,color,imported_from_provider,imported_at,import_job_id,
           import_inferred,import_metadata_json)
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
    local_id = str(row["id"])
    conn.execute(
        """
        insert into normalized_context_items
          (job_id,provider_id,source_object_type,source_object_id,local_object_type,
           local_object_id,raw_metadata_json,content_hash,relationship_inferred)
        values (%s,%s,'project',%s,'project',%s,%s::jsonb,%s,%s)
        on conflict do nothing
        """,
        (
            job_id,
            provider_id,
            source_id,
            local_id,
            json.dumps(project.get("raw_metadata") or {}, default=str),
            content_hash(project),
            bool(project.get("inferred")),
        ),
    )
    return local_id, True


def _link_project_chats(conn: Connection, provider_id: str, source_project_id: str, local_project_id: str) -> None:
    conn.execute(
        """
        update chats chat set project_id=%s
        from normalized_context_items item
        where item.local_object_id=chat.id and item.provider_id=%s
          and item.source_object_type='conversation'
          and item.parent_relationship_json->>'project_source_id'=%s
        """,
        (local_project_id, provider_id, source_project_id),
    )


def _validate_continuity(
    conn: Connection,
    job_id: str,
    provider_id: str,
    conversation: dict[str, Any],
) -> bool:
    source_id = _source_id(conversation)
    package_row = conn.execute(
        """
        select local_chat_id,package_json from continuity_packages
        where source_provider=%s and source_conversation_id=%s
        """,
        (provider_id, source_id),
    ).fetchone()
    if not package_row:
        return False
    message_rows = conn.execute(
        """
        select role,content,source_timestamp,import_order from messages
        where chat_id=%s order by coalesce(import_order,2147483647),created_at,id
        """,
        (package_row["local_chat_id"],),
    ).fetchall()
    package = package_row["package_json"] or {}
    transcript_retrievable = bool(message_rows) and all(row["role"] in {"user", "assistant"} for row in message_rows)
    objective_found = bool(package.get("current_objective"))
    decisions_found = bool(package.get("decisions"))
    tasks_found = bool(package.get("open_tasks") or package.get("unfinished_tasks"))
    entities_found = bool(package.get("people") or package.get("organizations") or package.get("files"))
    continuation_ready = transcript_retrievable and objective_found and bool(package.get("continuation_prompt"))
    test_prompt = f"Continue the imported conversation toward this objective: {package.get('current_objective') or conversation.get('title') or 'Continue'}"
    details = {
        "private_local_validation": True,
        "external_model_called": False,
        "message_count": len(message_rows),
        "roles": sorted({row["role"] for row in message_rows}),
        "continuity_package_retrieved": True,
    }
    conn.execute(
        """
        insert into continuity_validation_results
          (job_id,local_chat_id,source_conversation_id,test_prompt,objective_found,
           decisions_found,unresolved_tasks_found,entities_found,transcript_retrievable,
           continuation_ready,details_json)
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
        on conflict (job_id,local_chat_id) do update
        set test_prompt=excluded.test_prompt,objective_found=excluded.objective_found,
            decisions_found=excluded.decisions_found,unresolved_tasks_found=excluded.unresolved_tasks_found,
            entities_found=excluded.entities_found,transcript_retrievable=excluded.transcript_retrievable,
            continuation_ready=excluded.continuation_ready,details_json=excluded.details_json,
            created_at=now()
        """,
        (
            job_id,
            package_row["local_chat_id"],
            source_id,
            test_prompt,
            objective_found,
            decisions_found,
            tasks_found,
            entities_found,
            transcript_retrievable,
            continuation_ready,
            json.dumps(details),
        ),
    )
    return continuation_ready


def run_progressive_sync_job(job_id: str) -> dict[str, Any]:
    with get_conn() as conn:
        lock = conn.execute("select pg_try_advisory_lock(hashtext(%s)) as locked", (job_id,)).fetchone()
        if not lock or not lock["locked"]:
            return {"job_id": job_id, "status": "already_running"}
        try:
            job = conn.execute("select * from sync_jobs where id=%s", (job_id,)).fetchone()
            if not job:
                raise ValueError("Sync job not found.")
            if job["status"] in {"completed", "completed_with_exceptions", "failed_terminal", "cancelled"}:
                return {"job_id": job_id, "status": job["status"]}

            normalized = job["upload_payload_json"] or {}
            provider_id = job["provider_id"]
            conversations = sorted(
                normalized.get("conversations") or [],
                key=lambda item: item.get("updated_at") or item.get("created_at") or "",
                reverse=True,
            )
            projects = normalized.get("projects") or []
            files = normalized.get("files") or []
            continuity_targets = conversations[: min(20, len(conversations))]
            total = max(len(conversations) + len(projects) + len(files) + len(continuity_targets), 1)
            total_file_bytes = sum(int(item.get("size_bytes") or 0) for item in files)
            estimator = ThroughputEstimator(total, total_file_bytes)
            conn.execute(
                """
                update sync_jobs set status='running',started_at=coalesce(started_at,now()),
                  total=%s,items_discovered=%s,bytes_discovered=%s,last_error=null,
                  last_error_code=null,updated_at=now()
                where id=%s
                """,
                (total, total, total_file_bytes, job_id),
            )
            conn.commit()

            raw_counts = _persist_openai_raw(conn, job_id, normalized) if provider_id == "chatgpt" else {
                "conversations": 0,
                "nodes": 0,
                "branches": 0,
                "exceptions": 0,
                "prompt_injection_flags": 0,
            }
            processed = 0
            bytes_processed = 0
            project_map: dict[str, str] = {}
            chats_created = 0
            projects_created = 0
            files_created = 0
            messages_created = 0
            messages_available = 0
            duplicates_prevented = 0
            continuity_ready = 0
            latest_chat_id: str | None = None

            def progress(stage: str, message: str, status: str = "running") -> None:
                emit_progress(
                    conn,
                    job_id,
                    stage,
                    status,
                    processed,
                    total,
                    message,
                    estimator.remaining(processed, bytes_processed),
                    bytes_processed=bytes_processed,
                    bytes_discovered=total_file_bytes,
                )

            progress("reading_conversations", "Reading conversations")
            save_checkpoint(
                conn,
                job_id,
                "reading_conversations",
                processed,
                {"conversations": len(conversations), "projects": len(projects), "files": len(files)},
            )

            batch_size = max(1, int(os.getenv("CONTEXT_SYNC_RECENT_BATCH_SIZE", "20")))
            recent = conversations[:batch_size]
            older = conversations[batch_size:]
            progress("restoring_recent_chats", "Restoring recent chats")
            for conversation in recent:
                result = _import_conversation(conn, job_id, provider_id, conversation, project_map)
                latest_chat_id = latest_chat_id or result["chat_id"]
                chats_created += int(result["created"])
                duplicates_prevented += int(result["duplicate"])
                messages_created += result["messages_created"]
                messages_available += result["messages_available"]
                processed += 1
                progress("restoring_recent_chats", "Restoring recent chats")
                demo_pacing(provider_id)
            save_checkpoint(
                conn,
                job_id,
                "restoring_recent_chats",
                processed,
                {"recent_batch": len(recent), "latest_chat_id": latest_chat_id},
                cursor=_source_id(recent[-1]) if recent else None,
            )
            if recent and latest_chat_id:
                conn.execute(
                    """
                    update sync_jobs set ready_for_use=true,entry_chat_id=coalesce(entry_chat_id,%s),
                      display_message='Recent context ready',updated_at=now()
                    where id=%s
                    """,
                    (latest_chat_id, job_id),
                )
                progress("recent_context_ready", "Recent context ready")

            progress("restoring_projects", "Restoring projects")
            for project in projects:
                source_project_id = _source_id(project)
                local_project_id, created = _restore_project(conn, job_id, provider_id, project)
                project_map[source_project_id] = local_project_id
                projects_created += int(created)
                _link_project_chats(conn, provider_id, source_project_id, local_project_id)
                processed += 1
                progress("restoring_projects", "Restoring projects")
                demo_pacing(provider_id)
            save_checkpoint(conn, job_id, "restoring_projects", processed, {"project_map": project_map})

            progress("processing_files", "Processing files")
            for file_item in files:
                source_file_id = _source_id(file_item)
                result = conn.execute(
                    """
                    insert into normalized_context_items
                      (job_id,provider_id,source_object_type,source_object_id,local_object_type,
                       raw_metadata_json,content_hash,parent_relationship_json,parser_version)
                    select %s,%s,'file',%s,'reference',%s::jsonb,%s,%s::jsonb,%s
                    where not exists (
                      select 1 from normalized_context_items
                      where provider_id=%s and source_object_type='file' and source_object_id=%s
                    )
                    """,
                    (
                        job_id,
                        provider_id,
                        source_file_id,
                        json.dumps(file_item, default=str),
                        file_item.get("content_hash") or content_hash(file_item),
                        json.dumps({"conversation_source_id": file_item.get("conversation_source_id")}),
                        normalized.get("parser_version") or "openai_export_v2",
                        provider_id,
                        source_file_id,
                    ),
                )
                files_created += int(bool(result.rowcount))
                bytes_processed += int(file_item.get("size_bytes") or 0)
                processed += 1
                progress("processing_files", "Processing files")
                demo_pacing(provider_id)
            save_checkpoint(conn, job_id, "processing_files", processed, {"files_processed": len(files), "bytes_processed": bytes_processed})

            if older:
                progress("importing_older_history", "Importing older history")
            for conversation in older:
                result = _import_conversation(conn, job_id, provider_id, conversation, project_map)
                chats_created += int(result["created"])
                duplicates_prevented += int(result["duplicate"])
                messages_created += result["messages_created"]
                messages_available += result["messages_available"]
                processed += 1
                progress("importing_older_history", "Importing older history")
                demo_pacing(provider_id)
            save_checkpoint(conn, job_id, "importing_older_history", processed, {"older_history": len(older)})

            progress("building_working_context", "Building working context")
            for conversation in continuity_targets:
                continuity_ready += int(_validate_continuity(conn, job_id, provider_id, conversation))
                processed += 1
                progress("building_working_context", "Building working context")
                demo_pacing(provider_id)
            save_checkpoint(
                conn,
                job_id,
                "building_working_context",
                processed,
                {"validated": len(continuity_targets), "ready": continuity_ready},
            )

            progress("validating_transfer", "Validating transfer")
            exception_rows = conn.execute(
                """
                select item_type,source_object_id,user_message,error_class,recoverable
                from sync_exceptions where job_id=%s order by created_at
                """,
                (job_id,),
            ).fetchall()
            projects_available = conn.execute(
                """
                select count(*) as count from normalized_context_items
                where provider_id=%s and source_object_type='project'
                  and source_object_id=any(%s)
                """,
                (provider_id, [_source_id(item) for item in projects] or ["__none__"]),
            ).fetchone()["count"]
            files_available = conn.execute(
                """
                select count(*) as count from normalized_context_items
                where provider_id=%s and source_object_type='file'
                  and source_object_id=any(%s)
                """,
                (provider_id, [_source_id(item) for item in files] or ["__none__"]),
            ).fetchone()["count"]
            branches_preserved = conn.execute(
                "select count(*) as count from openai_conversation_branches where job_id=%s",
                (job_id,),
            ).fetchone()["count"]
            duration = conn.execute(
                "select extract(epoch from (now()-started_at))::int as seconds from sync_jobs where id=%s",
                (job_id,),
            ).fetchone()["seconds"]
            conversation_available = chats_created + duplicates_prevented
            critical_ok = (
                conversation_available == len(conversations)
                and messages_available >= sum(len(item.get("messages") or []) for item in conversations)
                and int(projects_available) == len(projects)
                and int(files_available) == len(files)
                and int(branches_preserved) == raw_counts["branches"]
                and continuity_ready == len(continuity_targets)
            )
            exception_payload = [dict(row) for row in exception_rows]
            if not critical_ok:
                validation_status = "failed"
                final_status = "failed_terminal"
            elif exception_payload:
                validation_status = "passed_with_exceptions"
                final_status = "completed_with_exceptions"
            else:
                validation_status = "passed"
                final_status = "completed"

            report = {
                "provider": provider_id,
                "connection_id": str(job["connection_id"]) if job.get("connection_id") else None,
                "job_id": job_id,
                "transfer_method": job.get("transfer_method") or "official_export_file_picker",
                "archive_hash": job.get("archive_hash") or normalized.get("archive_hash"),
                "archive_integrity_status": "validated" if provider_id == "chatgpt" else "not_applicable",
                "validation_status": validation_status,
                "conversations_discovered": len(conversations),
                "conversations_retrieved": len(conversations),
                "conversations_detected": len(conversations),
                "conversations_imported": conversation_available,
                "conversations_created": chats_created,
                "messages_discovered": sum(len(item.get("messages") or []) for item in conversations),
                "messages_retrieved": sum(len(item.get("messages") or []) for item in conversations),
                "messages_detected": sum(len(item.get("messages") or []) for item in conversations),
                "messages_imported": messages_available,
                "messages_created": messages_created,
                "projects_discovered": len(projects),
                "projects_retrieved": len(projects),
                "projects_transferred": int(projects_available),
                "projects_created": projects_created,
                "projects_confirmed": sum(1 for item in projects if not item.get("inferred")),
                "projects_reconstructed": sum(1 for item in projects if item.get("inferred")),
                "files_discovered": len(files),
                "files_retrieved": len(files),
                "files_detected": len(files),
                "files_imported": int(files_available),
                "files_created": files_created,
                "branches_discovered": raw_counts["branches"],
                "branches_preserved": int(branches_preserved),
                "duplicates_prevented": duplicates_prevented,
                "malformed_items_skipped": raw_counts["exceptions"],
                "continuity_packages_generated": conversation_available,
                "continuity_validations_run": len(continuity_targets),
                "continuity_validations_passed": continuity_ready,
                "prompt_injection_flags": raw_counts["prompt_injection_flags"],
                "security_flags": raw_counts["prompt_injection_flags"],
                "exceptions": exception_payload,
                "sync_duration_seconds": int(duration or 0),
            }
            conn.execute(
                """
                insert into sync_validation_reports
                  (provider_id,connection_id,job_id,report_json,validation_status)
                values (%s,%s,%s,%s::jsonb,%s)
                on conflict (job_id) do update
                set report_json=excluded.report_json,validation_status=excluded.validation_status,
                    created_at=now()
                """,
                (provider_id, job.get("connection_id"), job_id, json.dumps(report, default=str), validation_status),
            )

            if validation_status == "failed":
                emit_progress(
                    conn,
                    job_id,
                    "validating_transfer",
                    final_status,
                    processed,
                    total,
                    "Transfer integrity check failed",
                    None,
                    bytes_processed=bytes_processed,
                    bytes_discovered=total_file_bytes,
                )
                conn.execute(
                    """
                    update sync_jobs set status='failed_terminal',ready_for_use=false,
                      last_error='transfer_integrity_failed',last_error_code='transfer_integrity_failed',
                      completed_at=now(),updated_at=now() where id=%s
                    """,
                    (job_id,),
                )
            else:
                emit_progress(
                    conn,
                    job_id,
                    "context_ready",
                    final_status,
                    total,
                    total,
                    "Context ready",
                    0,
                    bytes_processed=total_file_bytes,
                    bytes_discovered=total_file_bytes,
                )
                conn.execute(
                    """
                    update sync_jobs set status=%s,stage='context_ready',processed=%s,total=%s,
                      items_processed=%s,items_discovered=%s,percent=100,
                      estimated_seconds_remaining=0,display_message='Context ready',
                      ready_for_use=true,completed_at=now(),updated_at=now()
                    where id=%s
                    """,
                    (final_status, total, total, total, total, job_id),
                )
                notify_in_app(conn, job_id, provider_id, "Your ChatGPT context is ready")
            conn.commit()
            return {
                "job_id": job_id,
                "status": final_status,
                "conversations": conversation_available,
                "projects": int(projects_available),
                "continuity_packages": conversation_available,
                "validation_status": validation_status,
            }
        finally:
            conn.execute("select pg_advisory_unlock(hashtext(%s))", (job_id,))
            conn.commit()
