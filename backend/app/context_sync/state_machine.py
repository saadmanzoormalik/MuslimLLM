from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from ..db import get_conn

TRANSFER_STATES = {
    "consent_required", "consented", "opening_openai", "awaiting_openai_confirmation",
    "waiting_for_export", "permission_required", "watching_email", "watching_folder",
    "awaiting_file_selection", "export_detected", "downloading", "validating_archive",
    "extracting", "inventorying", "importing_recent_context", "restoring_projects",
    "processing_files", "building_continuity", "recent_context_ready",
    "importing_older_history", "validating_results", "completed",
    "completed_with_exceptions", "failed_recoverable", "failed_terminal", "cancelled",
}

TERMINAL_STATES = {"completed", "completed_with_exceptions", "failed_terminal", "cancelled"}

DISPLAY_MESSAGES = {
    "consented": "Connecting to OpenAI",
    "opening_openai": "Connecting to OpenAI",
    "awaiting_openai_confirmation": "Waiting for OpenAI approval",
    "waiting_for_export": "Waiting for your ChatGPT export",
    "permission_required": "Allow one folder to detect the export automatically",
    "watching_email": "Waiting for your ChatGPT export",
    "watching_folder": "Waiting for your ChatGPT export",
    "awaiting_file_selection": "Select your ChatGPT export",
    "export_detected": "Export found",
    "downloading": "Downloading securely",
    "validating_archive": "Verifying archive",
    "extracting": "Verifying archive",
    "inventorying": "Reading conversations",
    "importing_recent_context": "Restoring recent chats",
    "restoring_projects": "Restoring projects",
    "processing_files": "Processing files",
    "building_continuity": "Building working context",
    "recent_context_ready": "Recent context ready",
    "importing_older_history": "Importing older history",
    "validating_results": "Validating transfer",
    "completed": "Context ready",
    "completed_with_exceptions": "Context ready",
    "failed_recoverable": "Sync paused",
    "failed_terminal": "The export could not be imported",
    "cancelled": "Transfer cancelled",
}

JOB_STAGE_TO_STATE = {
    "authorized": "validating_archive",
    "inventory": "inventorying",
    "deduplicating": "inventorying",
    "creating_projects": "restoring_projects",
    "creating_chats": "importing_recent_context",
    "building_continuity": "building_continuity",
    "validating": "validating_results",
    "completed": "completed",
    "reading_conversations": "inventorying",
    "restoring_recent_chats": "importing_recent_context",
    "recent_context_ready": "recent_context_ready",
    "restoring_projects": "restoring_projects",
    "processing_files": "processing_files",
    "importing_older_history": "importing_older_history",
    "building_working_context": "building_continuity",
    "validating_transfer": "validating_results",
    "context_ready": "completed",
}


def create_transfer_consent(device_id: str, *, accepted: bool) -> dict:
    if not accepted:
        raise ValueError("transfer_consent_required")
    accepted_at = datetime.now(UTC).isoformat()
    receipt_payload = {
        "provider": "chatgpt",
        "purpose": "context_transfer",
        "consent_version": "openai-export-transfer-v1",
        "privacy_notice_version": "local-private-v1",
        "accepted_at": accepted_at,
        "data_categories": ["conversations", "projects", "files", "working_context"],
        "local_cloud_mode": "local",
        "device_id_hash": hashlib.sha256(device_id.encode()).hexdigest(),
        "nonce": uuid4().hex,
    }
    receipt_hash = hashlib.sha256(json.dumps(receipt_payload, sort_keys=True).encode()).hexdigest()
    with get_conn() as conn:
        row = conn.execute(
            """
            insert into context_transfer_consents
              (provider,purpose,consent_version,privacy_notice_version,accepted_at,data_categories_json,local_cloud_mode,receipt_hash)
            values ('chatgpt','context_transfer','openai-export-transfer-v1','local-private-v1',%s,%s::jsonb,'local',%s)
            returning *
            """,
            (accepted_at, json.dumps(receipt_payload["data_categories"]), receipt_hash),
        ).fetchone()
    return dict(row)


def create_transfer_session(consent_id: str, device_id: str) -> dict:
    device_hash = hashlib.sha256(device_id.encode()).hexdigest()
    with get_conn() as conn:
        row = conn.execute(
            """
            insert into context_transfer_sessions (provider,consent_id,device_id_hash,state)
            values ('chatgpt',%s,%s,'consented') returning *
            """,
            (consent_id, device_hash),
        ).fetchone()
        conn.execute(
            """
            insert into context_transfer_session_events (session_id,to_state,event_type,details_json)
            values (%s,'consented','consent_recorded','{}'::jsonb)
            """,
            (row["id"],),
        )
    return dict(row)


def transition_session(session_id: str, to_state: str, *, event_type: str = "state_transition", details: dict[str, Any] | None = None, **updates) -> dict:
    if to_state not in TRANSFER_STATES:
        raise ValueError("invalid_transfer_state")
    safe_details = {key: value for key, value in (details or {}).items() if key in {"error_class", "permission_type", "job_status", "source"}}
    with get_conn() as conn:
        current = conn.execute("select * from context_transfer_sessions where id=%s for update", (session_id,)).fetchone()
        if not current:
            raise ValueError("transfer_session_not_found")
        if current["state"] in TERMINAL_STATES and current["state"] != to_state:
            raise ValueError("transfer_session_is_terminal")
        assignments = ["state=%s", "updated_at=now()"]
        values: list[Any] = [to_state]
        allowed_updates = {"acquisition_method", "sync_job_id", "folder_watch_id", "ready_for_use", "background_sync_continues", "last_error_code", "retry_count"}
        for key, value in updates.items():
            if key in allowed_updates:
                assignments.append(f"{key}=%s")
                values.append(value)
        if to_state in {"completed", "completed_with_exceptions"}:
            assignments.append("completed_at=now()")
        if to_state == "cancelled":
            assignments.append("cancelled_at=now()")
        values.append(session_id)
        row = conn.execute(f"update context_transfer_sessions set {', '.join(assignments)} where id=%s returning *", tuple(values)).fetchone()
        if current["state"] != to_state or event_type != "state_transition":
            conn.execute(
                """
                insert into context_transfer_session_events (session_id,from_state,to_state,event_type,details_json)
                values (%s,%s,%s,%s,%s::jsonb)
                """,
                (session_id, current["state"], to_state, event_type, json.dumps(safe_details)),
            )
    return dict(row)


def _sync_counts(conn, job_id: str | None) -> dict[str, int]:
    if not job_id:
        return {"chats": 0, "projects": 0, "files": 0}
    chats = conn.execute("select count(*) as count from chats where import_job_id=%s", (job_id,)).fetchone()["count"]
    projects = conn.execute("select count(*) as count from projects where import_job_id=%s", (job_id,)).fetchone()["count"]
    files = conn.execute("select count(*) as count from normalized_context_items where job_id=%s and source_object_type='file'", (job_id,)).fetchone()["count"]
    return {"chats": chats, "projects": projects, "files": files}


def refresh_transfer_session(session_id: str) -> dict:
    with get_conn() as conn:
        session = conn.execute("select * from context_transfer_sessions where id=%s", (session_id,)).fetchone()
        if not session:
            raise ValueError("transfer_session_not_found")
        if not session["sync_job_id"] and session["folder_watch_id"]:
            watch = conn.execute("select job_id,status,last_error_code from openai_export_folder_watches where id=%s", (session["folder_watch_id"],)).fetchone()
            if watch and watch["job_id"]:
                session = conn.execute("update context_transfer_sessions set sync_job_id=%s,updated_at=now() where id=%s returning *", (watch["job_id"], session_id)).fetchone()
            elif watch and watch["status"] == "failed":
                return transition_session(session_id, "failed_recoverable", details={"error_class": watch["last_error_code"] or "folder_watch_failed"}, last_error_code=watch["last_error_code"] or "folder_watch_failed")
        job = conn.execute("select * from sync_jobs where id=%s", (session["sync_job_id"],)).fetchone() if session["sync_job_id"] else None

    if job and session["state"] not in TERMINAL_STATES:
        if job["status"] in {"completed", "completed_with_exceptions"}:
            desired = job["status"]
        elif job["status"] == "failed_terminal":
            desired = "failed_terminal"
        elif job["status"] in {"failed_recoverable", "paused_auth_required"}:
            desired = "failed_recoverable"
        else:
            desired = JOB_STAGE_TO_STATE.get(job["stage"], session["state"])
        if desired != session["state"]:
            session = transition_session(
                session_id,
                desired,
                details={"job_status": job["status"]},
                ready_for_use=bool(job["ready_for_use"]),
                background_sync_continues=bool(job["ready_for_use"] and desired not in {"completed", "completed_with_exceptions"}),
                last_error_code=job.get("last_error_code") or job["last_error"],
            )
    return get_transfer_session(session_id, refresh=False)


def get_transfer_session(session_id: str, *, refresh: bool = True) -> dict:
    if refresh:
        return refresh_transfer_session(session_id)
    with get_conn() as conn:
        session = conn.execute("select * from context_transfer_sessions where id=%s", (session_id,)).fetchone()
        if not session:
            raise ValueError("transfer_session_not_found")
        job = conn.execute("select * from sync_jobs where id=%s", (session["sync_job_id"],)).fetchone() if session["sync_job_id"] else None
        counts = _sync_counts(conn, str(session["sync_job_id"]) if session["sync_job_id"] else None)
    progress = float(job["percent"] or 0) if job else (100.0 if session["state"] in {"completed", "completed_with_exceptions"} else 0.0)
    job_status = job["status"] if job else ("completed" if session["state"] in {"completed", "completed_with_exceptions"} else "waiting")
    public_status = "active" if job_status in {"authorized", "running"} else job_status
    transfer_method = (job.get("transfer_method") if job else None) or session["acquisition_method"]
    duration_seconds = None
    if job and job["started_at"]:
        duration_seconds = max(0, int(((job["completed_at"] or datetime.now(UTC)) - job["started_at"]).total_seconds()))
    return {
        "session_id": str(session["id"]),
        "job_id": str(job["id"]) if job else None,
        "state": session["state"],
        "stage": job["stage"] if job else session["state"],
        "status": public_status,
        "display_message": DISPLAY_MESSAGES.get(session["state"], "Syncing your ChatGPT context"),
        "progress_percent": progress,
        "percent": progress,
        "processed_items": int(job["items_processed"] if job and job.get("items_processed") is not None else (job["processed"] if job else 0)),
        "total_items": int(job["items_discovered"] if job and job.get("items_discovered") is not None else (job["total"] if job else 0)),
        "estimated_seconds_remaining": job["estimated_seconds_remaining"] if job else None,
        "chats_restored": counts["chats"],
        "projects_restored": counts["projects"],
        "files_restored": counts["files"],
        "ready_for_use": bool(session["ready_for_use"] or (job and job["ready_for_use"])),
        "background_sync_continues": bool((session["background_sync_continues"] or (job and job["ready_for_use"])) and job_status not in {"completed", "completed_with_exceptions", "failed_terminal", "cancelled"}),
        "latest_chat_id": str(job["entry_chat_id"]) if job and job["entry_chat_id"] else None,
        "latest_imported_chat_id": str(job["entry_chat_id"]) if job and job["entry_chat_id"] else None,
        "available_chat_count": counts["chats"],
        "transfer_method": transfer_method,
        "granted_capabilities": {
            "account_identity": False,
            "model_api_access": False,
            "chat_history_access": transfer_method == "official_history_api",
            "projects_access": transfer_method == "official_history_api",
            "files_access": transfer_method == "official_history_api",
            "official_export_access": bool(transfer_method and transfer_method.startswith("official_export")),
        },
        "sync_duration_seconds": duration_seconds,
        "recoverable": session["state"] == "failed_recoverable",
        "next_action": _next_action(session["state"], session["last_error_code"]),
        "updated_at": session["updated_at"],
    }


def _next_action(state: str, error_code: str | None = None) -> str:
    if state == "permission_required":
        return "grant_folder_access"
    if state == "awaiting_file_selection":
        return "select_file"
    if state == "failed_recoverable":
        if error_code in {"export_not_recognized", "invalid_zip", "chatgpt_export_not_recognized", "archive_incomplete"}:
            return "select_file"
        if error_code in {"folder_unavailable", "folder_permission_removed"}:
            return "grant_folder_access"
        return "resume"
    if state in {"completed", "completed_with_exceptions", "recent_context_ready"}:
        return "continue"
    return "sync"


def session_events(session_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("select id,from_state,to_state,event_type,details_json,created_at from context_transfer_session_events where session_id=%s order by created_at", (session_id,)).fetchall()
    return [dict(row) for row in rows]


def cancel_transfer_session(session_id: str) -> dict:
    with get_conn() as conn:
        session = conn.execute("select sync_job_id from context_transfer_sessions where id=%s", (session_id,)).fetchone()
        if not session:
            raise ValueError("transfer_session_not_found")
        if session["sync_job_id"]:
            conn.execute("update sync_jobs set status='cancelled',display_message='Transfer cancelled',updated_at=now() where id=%s and status not in ('completed','completed_with_exceptions')", (session["sync_job_id"],))
    return transition_session(session_id, "cancelled", event_type="cancelled")
