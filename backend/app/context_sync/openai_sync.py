import os
from pathlib import Path

from ..db import get_conn
from .providers.registry import get_provider
from .security.oauth_service import provider_oauth_config

OPENAI_EXPORT_URL = "https://help.openai.com/en/articles/7260999-how-do-i-export-my-data"
TERMINAL_STATUSES = {"completed", "completed_with_exceptions", "cancelled", "failed_terminal"}

PUBLIC_STAGES = {
    "authorized": ("validating_archive", "Connecting securely"),
    "inventory": ("discovering", "Reading your conversations"),
    "deduplicating": ("discovering", "Preparing your ChatGPT context"),
    "creating_projects": ("restoring_projects", "Restoring your projects"),
    "creating_chats": ("importing_recent_chats", "Reading your conversations"),
    "building_continuity": ("building_continuity", "Building continuity"),
    "validating": ("validating_results", "Almost ready"),
    "completed": ("completed", "Context ready"),
    "reading_conversations": ("reading_conversations", "Reading conversations"),
    "restoring_recent_chats": ("restoring_recent_chats", "Restoring recent chats"),
    "recent_context_ready": ("recent_context_ready", "Recent context ready"),
    "restoring_projects": ("restoring_projects", "Restoring projects"),
    "processing_files": ("processing_files", "Processing files"),
    "importing_older_history": ("importing_older_history", "Importing older history"),
    "building_working_context": ("building_working_context", "Building working context"),
    "validating_transfer": ("validating_transfer", "Validating transfer"),
    "context_ready": ("context_ready", "Context ready"),
}


async def resolve_openai_context_sync_method() -> str:
    """Choose only a verified, supported ChatGPT-history transfer method."""
    direct_history_verified = all(
        os.getenv(key, "false").lower() == "true"
        for key in (
            "CONTEXT_SYNC_OPENAI_HISTORY_API_DOCUMENTED",
            "CONTEXT_SYNC_OPENAI_HISTORY_SCOPES_DOCUMENTED",
            "CONTEXT_SYNC_OPENAI_HISTORY_CONTRACT_VERIFIED",
            "CONTEXT_SYNC_OPENAI_HISTORY_PROJECT_FILES_TESTED",
            "CONTEXT_SYNC_OPENAI_HISTORY_API_ENABLED",
        )
    )
    if direct_history_verified and provider_oauth_config("chatgpt").available:
        return "official_history_oauth"

    approved_export = os.getenv("CONTEXT_SYNC_OPENAI_APPROVED_EXPORT_PATH", "").strip()
    if approved_export and Path(approved_export).expanduser().is_file():
        return "local_export_import"

    provider = get_provider("chatgpt")
    if "official_export" in provider.get("connection_methods", []):
        return "official_export"
    return "unavailable"


def public_openai_job(job: dict) -> dict:
    internal_stage = job.get("stage") or "authorized"
    stage, message = PUBLIC_STAGES.get(internal_stage, (internal_stage, "Preparing your ChatGPT context"))
    status = job.get("status") or "authorized"
    if status == "failed_recoverable":
        message = "Import paused"
    elif status == "failed_terminal":
        message = "Export file not recognized"
    elif status in {"completed", "completed_with_exceptions"}:
        stage, message = ("completed", "Context ready")
    elif job.get("ready_for_use"):
        message = "Recent context ready"
    inventory = job.get("inventory_json") or {}
    return {
        "id": str(job["id"]),
        "job_id": str(job["id"]),
        "provider_id": "chatgpt",
        "status": status,
        "stage": stage,
        "processed": job.get("processed") or 0,
        "processed_items": job.get("processed") or 0,
        "total": job.get("total") or 0,
        "total_items": job.get("total") or 0,
        "percent": float(job.get("percent") or 0),
        "estimated_seconds_remaining": job.get("estimated_seconds_remaining"),
        "display_message": message,
        "ready_for_use": bool(job.get("ready_for_use")),
        "entry_chat_id": str(job["entry_chat_id"]) if job.get("entry_chat_id") else None,
        "counts": {
            "conversations": inventory.get("conversations_found") or 0,
            "projects": inventory.get("projects_found") or 0,
            "files": inventory.get("files_found") or 0,
        },
    }


def latest_openai_status() -> dict:
    with get_conn() as conn:
        rows = conn.execute(
            "select * from sync_jobs where provider_id='chatgpt' order by created_at desc limit 10"
        ).fetchall()
    active = next((row for row in rows if row["status"] not in TERMINAL_STATUSES), None)
    latest = rows[0] if rows else None
    return {
        "method": None,
        "active_job": public_openai_job(active) if active else None,
        "latest_job": public_openai_job(latest) if latest else None,
        "chatgpt_context": "imported_through_official_export" if latest and latest["status"] in {"completed", "completed_with_exceptions"} else "not_imported",
    }


def openai_report(job_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            """
            select report.report_json
            from sync_validation_reports report
            join sync_jobs job on job.id=report.job_id
            where report.job_id=%s and job.provider_id='chatgpt'
            """,
            (job_id,),
        ).fetchone()
    return row["report_json"] if row else None
