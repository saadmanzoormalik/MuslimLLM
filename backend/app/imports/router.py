import csv
import io
import json
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ..auth.sessions import require_principal
from fastapi.responses import Response

from ..db import get_conn
from .adapters import get_adapter, provider_adapters
from .context_graph import build_context_graph
from .coverage import estimate_coverage
from .dedupe import conversation_fingerprint, existing_imported_chat
from .models import init_import_schema
from .privacy import (
    classify_imported_content_as_user_context,
    prevent_imported_context_instruction_override,
    redact_tokens_from_logs,
    revoke_provider_credentials,
    scan_import_for_prompt_injection,
    strip_provider_system_prompts_if_needed,
)
from .schemas import (
    CallbackRequest,
    ConfirmImportRequest,
    ConnectRequest,
    DeleteJobRequest,
    PasteImportRequest,
    ScanRequest,
)
from .summarizer import summarize_conversation


router = APIRouter(prefix="/imports", tags=["context-import"], dependencies=[Depends(require_principal)])


def ensure_imports_ready() -> None:
    with get_conn() as conn:
        init_import_schema(conn)


@router.get("/providers")
def providers():
    return [adapter.capability() for adapter in provider_adapters().values()]


@router.post("/connect/{provider}")
def connect_provider(provider: str, _payload: ConnectRequest | None = None):
    adapter = get_adapter(provider)
    response = adapter.get_auth_url()
    audit(None, adapter.provider_name, "provider_connected_attempted", response)
    return response


@router.post("/callback/{provider}")
def provider_callback(provider: str, payload: CallbackRequest):
    adapter = get_adapter(provider)
    return adapter.exchange_auth_code(payload.code)


@router.post("/upload/{provider}")
async def upload_import(
    provider: str,
    file: Annotated[UploadFile, File()],
    date_preset: Annotated[str, Form()] = "last_6_months",
    date_start: Annotated[str | None, Form()] = None,
    date_end: Annotated[str | None, Form()] = None,
):
    adapter = get_adapter(provider)
    payload = await file.read()
    try:
        normalized = adapter.parse_uploaded_export(file.filename or "import", payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse import file: {exc}") from exc
    return create_preview_job(adapter.provider_name, "file", normalized, date_preset, date_start, date_end, source_name=file.filename or "upload")


@router.post("/paste")
def paste_import(payload: PasteImportRequest):
    from .normalizer import normalize_markdown_transcript

    normalized = normalize_markdown_transcript(payload.content, provider=payload.provider, title=payload.title or "Pasted transcript")
    return create_preview_job(payload.provider, "paste", normalized, payload.date_range.preset, payload.date_range.start, payload.date_range.end, source_name=payload.title or "paste")


@router.post("/scan")
def scan_import(payload: ScanRequest):
    with get_conn() as conn:
        job = get_job(conn, payload.job_id)
        coverage = coverage_payload(conn, payload.job_id)
    return {"job": job, "coverage": coverage}


@router.get("/jobs")
def list_jobs():
    with get_conn() as conn:
        return conn.execute("select * from import_jobs order by created_at desc limit 50").fetchall()


@router.get("/jobs/{job_id}")
def job_detail(job_id: str):
    with get_conn() as conn:
        job = get_job(conn, job_id)
        conversations = conn.execute("select * from imported_conversations where import_job_id=%s order by title", (job_id,)).fetchall()
        projects = conn.execute("select * from imported_projects where import_job_id=%s order by title", (job_id,)).fetchall()
        preferences = conn.execute("select * from imported_preferences where import_job_id=%s order by id", (job_id,)).fetchall()
    return {"job": job, "conversations": conversations, "projects": projects, "preferences": preferences}


@router.get("/jobs/{job_id}/preview")
def job_preview(job_id: str):
    with get_conn() as conn:
        job = get_job(conn, job_id)
        conversations = conn.execute(
            """
            select id,title,message_count,attachment_count,token_estimate,coverage_json,raw_metadata_json
            from imported_conversations
            where import_job_id=%s
            order by updated_at_source desc nulls last, title
            limit 100
            """,
            (job_id,),
        ).fetchall()
        projects = conn.execute("select id,title,description,conversation_count,file_count,coverage_json,raw_metadata_json from imported_projects where import_job_id=%s order by title", (job_id,)).fetchall()
        warnings = security_warnings(conn, job_id)
    return {"job": job, "conversations": conversations, "projects": projects, "coverage": coverage_payload_from_job(job), "security_warnings": warnings}


@router.post("/jobs/{job_id}/confirm")
def confirm_job(job_id: str, payload: ConfirmImportRequest | None = None):
    options = (payload or ConfirmImportRequest()).options
    if options.cloud_summarization_enabled:
        raise HTTPException(status_code=400, detail="Cloud summarization is disabled in Local Private Mode unless explicitly implemented.")

    with get_conn() as conn:
        job = get_job(conn, job_id)
        if job["status"] not in {"preview_ready", "completed"}:
            raise HTTPException(status_code=400, detail="Import job is not ready to confirm.")
        conn.execute("update import_jobs set status='importing' where id=%s", (job_id,))
        audit(job_id, job["provider"], "import_confirmed", {"options": options.model_dump()}, conn=conn)

        project_map = {}
        if options.import_projects:
            for project in conn.execute("select * from imported_projects where import_job_id=%s", (job_id,)).fetchall():
                row = conn.execute(
                    """
                    insert into projects (name, description, color, imported_from_provider, imported_at, import_job_id, import_inferred, import_metadata_json)
                    values (%s,%s,'emerald',%s,now(),%s,%s,%s::jsonb)
                    returning id
                    """,
                    (
                        project["title"],
                        project["description"] or "Imported context workspace",
                        job["provider"],
                        job_id,
                        bool((project["raw_metadata_json"] or {}).get("inferred")),
                        json.dumps(project["raw_metadata_json"] or {}, default=str),
                    ),
                ).fetchone()
                project_map[project["source_project_id"]] = row["id"]
                conn.execute("update imported_projects set imported_project_id=%s, import_status='imported' where id=%s", (row["id"], project["id"]))

        imported = 0
        skipped = 0
        for conversation in conn.execute("select * from imported_conversations where import_job_id=%s order by created_at_source nulls last, title", (job_id,)).fetchall():
            messages = conn.execute("select * from imported_messages where imported_conversation_id=%s order by id", (conversation["id"],)).fetchall()
            fingerprint = (conversation["raw_metadata_json"] or {}).get("fingerprint")
            existing = existing_imported_chat(conn, job["provider"], conversation["source_conversation_id"], fingerprint)
            if existing:
                skipped += 1
                conn.execute("update imported_conversations set imported_chat_id=%s, import_status='duplicate_skipped' where id=%s", (existing, conversation["id"]))
                continue

            project_id = project_map.get((conversation["raw_metadata_json"] or {}).get("project_source_id"))
            chat = conn.execute(
                """
                insert into chats (title, model, project_id, imported_from_provider, imported_at, import_job_id, import_metadata_json)
                values (%s,'imported-context',%s,%s,now(),%s,%s::jsonb)
                returning id
                """,
                (
                    conversation["title"],
                    project_id if options.import_projects else None,
                    job["provider"],
                    job_id,
                    json.dumps(conversation["raw_metadata_json"] or {}, default=str),
                ),
            ).fetchone()
            chat_id = chat["id"]
            if options.import_chats:
                for message in messages:
                    role, content = strip_provider_system_prompts_if_needed(message["role"], message["content"])
                    role = role if role in {"user", "assistant", "system"} else "user"
                    if message["role"] in {"tool", "unknown"}:
                        content = f"[Imported {message['role']} context]\n{content}"
                    conn.execute(
                        "insert into messages (chat_id, role, content, citations, model, created_at) values (%s,%s,%s,%s::jsonb,%s,coalesce(%s::timestamptz, now()))",
                        (chat_id, role, content, json.dumps(message["citations_json"] or []), message["model_name_source"], message["created_at_source"]),
                    )
            summary = summarize_conversation(conversation["title"], [dict(message) for message in messages])
            if options.generate_summaries:
                graph = build_context_graph(summary) if options.rebuild_context_graph else {}
                conn.execute(
                    """
                    insert into context_snapshots (import_job_id, snapshot_type, title, content, confidence_level, source_refs_json)
                    values (%s,'conversation_summary',%s,%s,'medium',%s::jsonb)
                    """,
                    (job_id, conversation["title"], summary["summary"], json.dumps({"conversation_id": str(conversation["id"]), "graph": graph}, default=str)),
                )
            if options.generate_memory_suggestions:
                for memory in summary["memory_candidates"]:
                    conn.execute(
                        """
                        insert into imported_preferences (import_job_id, preference_type, content, confidence_level, source_provider, requires_user_review, raw_metadata_json)
                        values (%s,'memory',%s,'low',%s,true,%s::jsonb)
                        """,
                        (job_id, memory, job["provider"], json.dumps({"source_conversation_id": str(conversation["id"])}, default=str)),
                    )
            conn.execute("update imported_conversations set imported_chat_id=%s, import_status='imported' where id=%s", (chat_id, conversation["id"]))
            imported += 1

        conn.execute(
            """
            update import_jobs
            set status='completed', completed_at=now(), total_items_imported=%s, total_items_skipped=%s
            where id=%s
            """,
            (imported, skipped, job_id),
        )
        audit(job_id, job["provider"], "import_completed", {"imported": imported, "skipped": skipped}, conn=conn)
    return {"job_id": job_id, "imported": imported, "skipped": skipped, "status": "completed"}


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    with get_conn() as conn:
        job = get_job(conn, job_id)
        conn.execute("update import_jobs set status='cancelled' where id=%s", (job_id,))
        audit(job_id, job["provider"], "import_cancelled", {}, conn=conn)
    return {"job_id": job_id, "status": "cancelled"}


@router.delete("/jobs/{job_id}")
def delete_job(job_id: str, payload: DeleteJobRequest | None = None):
    delete_imported_data = bool(payload and payload.delete_imported_data)
    with get_conn() as conn:
        if delete_imported_data:
            for row in conn.execute("select imported_chat_id from imported_conversations where import_job_id=%s and imported_chat_id is not null", (job_id,)).fetchall():
                conn.execute("delete from chats where id=%s", (row["imported_chat_id"],))
            for row in conn.execute("select imported_project_id from imported_projects where import_job_id=%s and imported_project_id is not null", (job_id,)).fetchall():
                conn.execute("delete from projects where id=%s", (row["imported_project_id"],))
        conn.execute("delete from import_jobs where id=%s", (job_id,))
    return {"deleted": job_id, "deleted_imported_data": delete_imported_data}


@router.get("/jobs/{job_id}/coverage")
def job_coverage(job_id: str):
    with get_conn() as conn:
        get_job(conn, job_id)
        return coverage_payload(conn, job_id)


@router.get("/jobs/{job_id}/report")
def job_report(job_id: str, format: str = "json"):
    with get_conn() as conn:
        report = report_payload(conn, job_id)
    if format == "markdown":
        return Response(markdown_report(report), media_type="text/markdown")
    if format == "csv":
        return Response(csv_report(report), media_type="text/csv")
    return report


@router.get("/memory-suggestions")
def memory_suggestions():
    with get_conn() as conn:
        return conn.execute(
            """
            select * from imported_preferences
            where requires_user_review=true and review_status='pending'
            order by id desc
            limit 100
            """
        ).fetchall()


@router.post("/memory-suggestions/{suggestion_id}/accept")
def accept_memory(suggestion_id: str):
    with get_conn() as conn:
        row = conn.execute(
            "update imported_preferences set imported_into_profile=true, review_status='accepted' where id=%s returning *",
            (suggestion_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Memory suggestion not found.")
    return row


@router.post("/memory-suggestions/{suggestion_id}/reject")
def reject_memory(suggestion_id: str):
    with get_conn() as conn:
        row = conn.execute(
            "update imported_preferences set imported_into_profile=false, review_status='rejected' where id=%s returning *",
            (suggestion_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Memory suggestion not found.")
    return row


@router.post("/revoke/{provider}")
def revoke_provider(provider: str):
    result = revoke_provider_credentials(provider)
    audit(None, provider, "credentials_deleted", result)
    return result


def create_preview_job(provider: str, import_mode: str, normalized: dict[str, Any], date_preset: str, date_start: str | None, date_end: str | None, source_name: str):
    start, end = date_range(date_preset, date_start, date_end)
    normalized = apply_date_filter(normalized, start, end)
    coverage = estimate_coverage(normalized)
    warnings = []
    with get_conn() as conn:
        job = conn.execute(
            """
            insert into import_jobs
            (provider, import_mode, status, selected_date_range_start, selected_date_range_end,
             total_items_detected, coverage_score)
            values (%s,%s,'preview_ready',%s,%s,%s,%s)
            returning *
            """,
            (provider, import_mode, start, end, coverage["detected"]["chats"], coverage["overall"]),
        ).fetchone()
        job_id = str(job["id"])
        audit(job_id, provider, "import_preview_generated", {"source": source_name, "coverage": coverage}, conn=conn)
        for project in normalized.get("projects", []):
            conn.execute(
                """
                insert into imported_projects
                (import_job_id, source_provider, source_project_id, title, description, conversation_count,
                 file_count, coverage_json, raw_metadata_json)
                values (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)
                """,
                (
                    job_id,
                    provider,
                    project.get("source_id"),
                    project.get("title") or "Imported Project",
                    project.get("description"),
                    0,
                    0,
                    json.dumps({"available": True}),
                    json.dumps({**(project.get("raw_metadata") or {}), "inferred": project.get("inferred", False)}, default=str),
                ),
            )
        for conversation in normalized.get("conversations", []):
            messages = conversation.get("messages", [])
            fingerprint = conversation_fingerprint(provider, conversation.get("source_id"), conversation.get("title", ""), messages)
            security = scan_import_for_prompt_injection("\n".join(message.get("content", "") for message in messages))
            warnings.extend(security)
            row = conn.execute(
                """
                insert into imported_conversations
                (import_job_id, source_provider, source_conversation_id, title, created_at_source,
                 updated_at_source, message_count, attachment_count, token_estimate, coverage_json, raw_metadata_json)
                values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)
                returning id
                """,
                (
                    job_id,
                    provider,
                    conversation.get("source_id"),
                    conversation.get("title") or "Imported chat",
                    conversation.get("created_at"),
                    conversation.get("updated_at"),
                    len(messages),
                    len(conversation.get("attachments", [])),
                    sum(len((message.get("content") or "").split()) for message in messages),
                    json.dumps({"prompt_injection_warnings": security, "classification": "user_context"}),
                    json.dumps({**(conversation.get("raw_metadata") or {}), "fingerprint": fingerprint, "project_source_id": conversation.get("project_source_id")}, default=str),
                ),
            ).fetchone()
            for message in messages:
                role, content = strip_provider_system_prompts_if_needed(message.get("role", "unknown"), message.get("content", ""))
                content = prevent_imported_context_instruction_override(content)
                conn.execute(
                    """
                    insert into imported_messages
                    (imported_conversation_id, role, content, created_at_source, model_name_source,
                     attachments_json, citations_json, raw_metadata_json)
                    values (%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb)
                    """,
                    (
                        row["id"],
                        role,
                        content,
                        message.get("created_at"),
                        message.get("model"),
                        json.dumps(message.get("attachments") or []),
                        json.dumps(message.get("citations") or []),
                        json.dumps({**(message.get("raw_metadata") or {}), **classify_imported_content_as_user_context(content)}, default=str),
                    ),
                )
        for preference in normalized.get("preferences", []):
            conn.execute(
                """
                insert into imported_preferences
                (import_job_id, preference_type, content, confidence_level, source_provider, requires_user_review, raw_metadata_json)
                values (%s,%s,%s,%s,%s,true,%s::jsonb)
                """,
                (
                    job_id,
                    preference["preference_type"],
                    preference["content"],
                    preference["confidence_level"],
                    provider,
                    json.dumps(preference.get("raw_metadata") or {}, default=str),
                ),
            )
        if warnings:
            audit(job_id, provider, "prompt_injection_warnings", {"patterns": sorted(set(warnings))}, conn=conn)
    return {"job": job, "coverage": coverage, "security_warnings": sorted(set(warnings)), "preview_url": f"/imports/jobs/{job_id}/preview"}


def date_range(preset: str, start: str | None, end: str | None):
    now = datetime.now(UTC)
    if preset == "all_time":
        return None, now
    if preset == "custom":
        return parse_dt(start), parse_dt(end) or now
    days = {
        "last_30_days": 30,
        "last_90_days": 90,
        "last_6_months": 183,
        "last_12_months": 365,
    }.get(preset, 183)
    return now - timedelta(days=days), now


def apply_date_filter(normalized: dict[str, Any], start, end):
    if not start:
        return normalized
    conversations = []
    for conversation in normalized.get("conversations", []):
        stamp = parse_dt(conversation.get("updated_at") or conversation.get("created_at"))
        if not stamp or start <= stamp <= (end or datetime.now(UTC)):
            conversations.append(conversation)
    return {**normalized, "conversations": conversations}


def parse_dt(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def get_job(conn, job_id: str):
    job = conn.execute("select * from import_jobs where id=%s", (job_id,)).fetchone()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found.")
    return job


def coverage_payload(conn, job_id: str):
    job = get_job(conn, job_id)
    return coverage_payload_from_job(job)


def coverage_payload_from_job(job):
    return {"overall": float(job["coverage_score"] or 0), "note": "Coverage measures available imported context; provider-unavailable fields are shown separately."}


def security_warnings(conn, job_id: str):
    rows = conn.execute(
        "select details_json from import_audit_log where import_job_id=%s and event_type='prompt_injection_warnings'",
        (job_id,),
    ).fetchall()
    warnings = []
    for row in rows:
        warnings.extend((row["details_json"] or {}).get("patterns", []))
    return sorted(set(warnings))


def report_payload(conn, job_id: str):
    job = get_job(conn, job_id)
    stats = conn.execute(
        """
        select
          (select count(*) from imported_conversations where import_job_id=%s) as chats_detected,
          (select count(*) from imported_conversations where import_job_id=%s and imported_chat_id is not null) as chats_imported,
          (select coalesce(sum(message_count),0) from imported_conversations where import_job_id=%s) as messages_imported,
          (select count(*) from imported_projects where import_job_id=%s) as projects_detected,
          (select count(*) from imported_projects where import_job_id=%s and imported_project_id is not null) as projects_imported,
          (select count(*) from imported_files where import_job_id=%s) as files_detected,
          (select count(*) from imported_files where import_job_id=%s and local_document_id is not null) as files_imported,
          (select count(*) from imported_preferences where import_job_id=%s) as memory_suggestions_count
        """,
        (job_id, job_id, job_id, job_id, job_id, job_id, job_id, job_id),
    ).fetchone()
    audits = conn.execute("select event_type, details_json, created_at from import_audit_log where import_job_id=%s order by created_at", (job_id,)).fetchall()
    return {
        "source_provider": job["provider"],
        "import_mode": job["import_mode"],
        "selected_date_range": {"start": job["selected_date_range_start"], "end": job["selected_date_range_end"]},
        "coverage_score": float(job["coverage_score"] or 0),
        "status": job["status"],
        "stats": stats,
        "security_warnings": security_warnings(conn, job_id),
        "audit_log": audits,
        "next_recommended_actions": ["Review memory suggestions.", "Open imported chats from All Chats.", "Delete unsupported or duplicate import jobs if needed."],
    }


def markdown_report(report: dict[str, Any]) -> str:
    stats = report["stats"]
    lines = [
        "# Import Context Report",
        "",
        f"- Source provider: {report['source_provider']}",
        f"- Import mode: {report['import_mode']}",
        f"- Status: {report['status']}",
        f"- Coverage score: {report['coverage_score']}",
        f"- Chats: {stats['chats_imported']} imported / {stats['chats_detected']} detected",
        f"- Projects: {stats['projects_imported']} imported / {stats['projects_detected']} detected",
        f"- Files: {stats['files_imported']} imported / {stats['files_detected']} detected",
        f"- Messages imported: {stats['messages_imported']}",
        f"- Memory suggestions: {stats['memory_suggestions_count']}",
        "",
        "## Security Warnings",
    ]
    warnings = report.get("security_warnings") or []
    lines.extend([f"- {warning}" for warning in warnings] or ["- None"])
    lines.extend(["", "## Next Actions"])
    lines.extend(f"- {item}" for item in report["next_recommended_actions"])
    return "\n".join(lines) + "\n"


def csv_report(report: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["provider", "mode", "status", "coverage", "chats_detected", "chats_imported", "messages_imported", "projects_detected", "projects_imported"])
    stats = report["stats"]
    writer.writerow([report["source_provider"], report["import_mode"], report["status"], report["coverage_score"], stats["chats_detected"], stats["chats_imported"], stats["messages_imported"], stats["projects_detected"], stats["projects_imported"]])
    return output.getvalue()


def audit(job_id: str | None, provider: str | None, event_type: str, details: dict[str, Any], conn=None):
    payload = json.dumps(json.loads(redact_tokens_from_logs(json.dumps(details, default=str))))
    if conn is not None:
        conn.execute(
            "insert into import_audit_log (import_job_id, provider, event_type, details_json) values (%s,%s,%s,%s::jsonb)",
            (job_id, provider, event_type, payload),
        )
        return
    with get_conn() as audit_conn:
        audit_conn.execute(
            "insert into import_audit_log (import_job_id, provider, event_type, details_json) values (%s,%s,%s,%s::jsonb)",
            (job_id, provider, event_type, payload),
        )
