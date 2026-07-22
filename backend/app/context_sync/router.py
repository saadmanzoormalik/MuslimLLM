import asyncio
import json
import os
from pathlib import Path

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile

from ..auth.sessions import require_principal
from fastapi.responses import RedirectResponse, StreamingResponse
from joserfc.errors import JoseError

from ..db import get_conn
from .cloud_broker_client import exchange_broker_grant, revoke_broker_connection, start_broker_connection
from .jobs.queue import enqueue_job
from .model_connections import (
    ModelConnectionIn,
    active_model_connection,
    connect_model,
    disconnect_model,
    test_model_connection,
)
from .openai_sync import (
    OPENAI_EXPORT_URL,
    latest_openai_status,
    openai_report,
    public_openai_job,
    resolve_openai_context_sync_method,
)
from .openai.export_flow import OFFICIAL_OPENAI_EXPORT_GUIDE, begin_openai_export_flow, resolve_best_acquisition_method, resume_export_flow
from .openai_folder_watch import authorize_export_folder, latest_folder_watch, revoke_all_folder_watches, revoke_folder_watch
from .providers.registry import get_provider, provider_list, update_provider
from .security.oauth_service import (
    begin_oauth_connection,
    complete_oauth_connection,
    fetch_oauth_context,
    provider_oauth_config,
    revoke_oauth_connection,
)
from .service import create_job, create_upload_inventory, latest_status, load_upload, portable_export
from .state_machine import (
    cancel_transfer_session,
    create_transfer_consent,
    get_transfer_session,
    session_events,
    transition_session,
)

router = APIRouter(prefix="/context-sync", tags=["context-sync"], dependencies=[Depends(require_principal)])

DISPLAY_MESSAGES = {
    "authorized": "Securely connecting",
    "connecting": "Securely connecting",
    "inventory": "Finding your conversations",
    "deduplicating": "Processing your context",
    "creating_projects": "Restoring your projects",
    "creating_chats": "Processing your context",
    "building_continuity": "Preparing your workspace",
    "validating": "Almost ready",
    "completed": "Your context is ready",
    "reading_conversations": "Reading conversations",
    "restoring_recent_chats": "Restoring recent chats",
    "recent_context_ready": "Recent context ready",
    "restoring_projects": "Restoring projects",
    "processing_files": "Processing files",
    "importing_older_history": "Importing older history",
    "building_working_context": "Building working context",
    "validating_transfer": "Validating transfer",
    "context_ready": "Context ready",
}


def _start_durable_job(job_id: str) -> None:
    if os.getenv("CONTEXT_SYNC_INLINE_JOBS", "true").lower() == "true":
        asyncio.create_task(asyncio.to_thread(enqueue_job, job_id))


def _public_provider(provider: dict) -> dict:
    if provider["provider_id"] == "demo":
        enabled = os.getenv("CONTEXT_SYNC_ALLOW_MOCK_PROVIDER", "true").lower() == "true" and os.getenv("APP_ENVIRONMENT", "development") != "production"
        return {
            "provider_id": "demo",
            "display_name": "Demo AI Account",
            "integration_status": "direct_sync" if enabled else "coming_soon",
            "available": enabled,
            "oauth_ready": enabled,
            "button_label": "Connect" if enabled else "Coming soon",
            "trust_label": "Development OAuth",
            "connection_method": "broker_oauth" if enabled else "unavailable",
        }
    oauth_ready = provider_oauth_config(provider["provider_id"]).available
    export_ready = "official_export" in provider.get("connection_methods", [])
    available = oauth_ready or export_ready
    return {
        "provider_id": provider["provider_id"],
        "display_name": provider["display_name"],
        "integration_status": "direct_sync" if oauth_ready else ("export_sync" if export_ready else "coming_soon"),
        "available": available,
        "oauth_ready": oauth_ready,
        "button_label": "Connect" if available else "Coming soon",
        "trust_label": "Official sign-in" if oauth_ready else ("Official export" if export_ready else "Unavailable"),
        "connection_method": "oauth" if oauth_ready else ("official_export" if export_ready else "unavailable"),
    }


def _public_job(job: dict) -> dict:
    stage = job.get("stage") or "authorized"
    status = job.get("status") or "authorized"
    message = job.get("display_message") or DISPLAY_MESSAGES.get(stage, "Processing your context")
    if status == "paused_auth_required":
        message = "Reconnect required"
    elif status == "failed_recoverable":
        message = "Sync paused"
    elif status in {"completed", "completed_with_exceptions"}:
        message = "Context ready"
    elif job.get("ready_for_use"):
        message = "Recent context ready; older history still syncing"
    return {
        "id": str(job["id"]),
        "provider_id": job["provider_id"],
        "status": status,
        "stage": stage,
        "processed": job.get("processed") or 0,
        "processed_items": job.get("items_processed") or job.get("processed") or 0,
        "total": job.get("total") or 0,
        "total_items": job.get("items_discovered") or job.get("total") or 0,
        "percent": float(job.get("percent") or 0),
        "estimated_seconds_remaining": job.get("estimated_seconds_remaining"),
        "display_message": message,
        "ready_for_use": bool(job.get("ready_for_use")),
        "entry_chat_id": str(job["entry_chat_id"]) if job.get("entry_chat_id") else None,
        "transfer_method": job.get("transfer_method"),
        "archive_hash": job.get("archive_hash"),
        "updated_at": job.get("updated_at"),
    }


async def _create_openai_import(file: UploadFile, session_id: str | None = None) -> dict:
    filename = file.filename or ""
    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Export file not recognized")
    try:
        upload = await create_upload_inventory("chatgpt", file)
        stored = load_upload(upload["inventory"]["upload_token"])
        if not stored:
            raise ValueError("Import could not be prepared")
        inventory = stored["inventory"]
        normalized = inventory.pop("normalized", {})
        transfer_method = "official_export_file_picker"
        if session_id:
            with get_conn() as conn:
                transfer = conn.execute(
                    "select acquisition_method from context_transfer_sessions where id=%s",
                    (session_id,),
                ).fetchone()
            if transfer and transfer["acquisition_method"]:
                transfer_method = transfer["acquisition_method"]
        job_id = create_job(
            "chatgpt",
            stored["connection_id"],
            inventory,
            normalized,
            transfer_method=transfer_method,
        )
        if session_id:
            transition_session(
                session_id,
                "importing_recent_context",
                event_type="import_started",
                sync_job_id=job_id,
                ready_for_use=False,
                background_sync_continues=True,
                last_error_code=None,
            )
        _start_durable_job(job_id)
        return {
            "method": "official_export",
            "next_action": "start_sync",
            "authorization_url": "",
            "job_id": job_id,
        }
    except (ValueError, json.JSONDecodeError) as exc:
        if session_id:
            transition_session(
                session_id,
                "failed_recoverable",
                event_type="archive_rejected",
                details={"error_class": type(exc).__name__},
                last_error_code="export_not_recognized",
            )
        raise HTTPException(status_code=400, detail="Export file not recognized") from exc


@router.post("/openai/agree-and-connect")
async def agree_and_connect_openai(payload: dict):
    accepted = bool(payload.get("accepted"))
    device_id = str(payload.get("device_id") or "local-device")[:200]
    try:
        consent = create_transfer_consent(device_id, accepted=accepted)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Transfer consent is required") from exc
    flow = await begin_openai_export_flow(str(consent["id"]), device_id)
    method = await resolve_best_acquisition_method(flow)
    direct = method.method in {"official_history_api", "official_export_api", "official_export_email", "official_export_folder_watch"}
    return {
        "session_id": flow.session_id,
        "next_action": "sync" if direct else "open_official_export",
        "action_url": "" if direct else OFFICIAL_OPENAI_EXPORT_GUIDE,
        "display_message": "Connecting securely",
        "transfer_method": method.method,
        "granted_capabilities": {
            "account_identity": False,
            "model_api_access": False,
            "chat_history_access": method.method == "official_history_api",
            "projects_access": method.method == "official_history_api",
            "files_access": method.method == "official_history_api",
            "official_export_access": method.method.startswith("official_export"),
        },
    }


@router.get("/openai/session/{session_id}")
def get_openai_transfer_session(session_id: str):
    try:
        return get_transfer_session(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Transfer session not found") from exc


@router.get("/openai/session/{session_id}/events")
async def openai_transfer_events(session_id: str):
    try:
        get_transfer_session(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Transfer session not found") from exc

    async def stream():
        previous = ""
        while True:
            try:
                current = get_transfer_session(session_id)
            except ValueError:
                yield "event: error\ndata: {\"message\":\"Transfer session not found\"}\n\n"
                return
            encoded = json.dumps(current, default=str, sort_keys=True)
            if encoded != previous:
                yield f"event: progress\ndata: {encoded}\n\n"
                previous = encoded
            else:
                yield f"event: heartbeat\ndata: {json.dumps({'session_id': session_id})}\n\n"
            if current["state"] in {"completed", "completed_with_exceptions", "failed_terminal", "cancelled"}:
                return
            await asyncio.sleep(2)

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.post("/openai/session/{session_id}/grant-folder-access")
async def grant_openai_folder_access(session_id: str):
    try:
        get_transfer_session(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Transfer session not found") from exc
    try:
        watch = await authorize_export_folder()
    except RuntimeError:
        transition_session(session_id, "awaiting_file_selection", event_type="folder_permission_unavailable", last_error_code="folder_unavailable")
        return get_transfer_session(session_id)
    with get_conn() as conn:
        conn.execute(
            """
            insert into context_transfer_permissions (provider,permission_type,status,grant_reference_id)
            values ('chatgpt','selected_folder','active',%s)
            """,
            (watch["id"],),
        )
    transition_session(
        session_id,
        "watching_folder",
        event_type="folder_permission_granted",
        details={"permission_type": "selected_folder"},
        acquisition_method="authorized_folder",
        folder_watch_id=watch["id"],
        last_error_code=None,
    )
    return get_transfer_session(session_id)


@router.post("/openai/session/{session_id}/grant-email-access")
async def grant_openai_email_access(session_id: str):
    try:
        get_transfer_session(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Transfer session not found") from exc
    raise HTTPException(status_code=501, detail="Mailbox detection is not enabled; use the selected-folder or file flow")


@router.post("/openai/session/{session_id}/select-export")
async def select_openai_session_export(session_id: str, file: UploadFile = File(...)):
    try:
        get_transfer_session(session_id)
        transition_session(session_id, "export_detected", event_type="export_selected")
        transition_session(session_id, "validating_archive", event_type="archive_validation_started")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Transfer session not found") from exc
    return await _create_openai_import(file, session_id)


@router.post("/openai/session/{session_id}/resume")
async def resume_openai_transfer(session_id: str):
    try:
        await resume_export_flow(session_id)
        session = get_transfer_session(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Transfer session not found") from exc
    with get_conn() as conn:
        row = conn.execute("select sync_job_id,folder_watch_id from context_transfer_sessions where id=%s", (session_id,)).fetchone()
    if row and row["sync_job_id"]:
        transition_session(session_id, "importing_recent_context", event_type="transfer_resumed", retry_count=1, last_error_code=None)
        _start_durable_job(str(row["sync_job_id"]))
    elif row and row["folder_watch_id"]:
        transition_session(session_id, "watching_folder", event_type="transfer_resumed", last_error_code=None)
    else:
        transition_session(session_id, "awaiting_file_selection", event_type="transfer_resumed", last_error_code=None)
    return get_transfer_session(session_id)


@router.post("/openai/session/{session_id}/cancel")
def cancel_openai_transfer(session_id: str):
    try:
        cancel_transfer_session(session_id)
        return get_transfer_session(session_id, refresh=False)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Transfer session not found") from exc


@router.get("/openai/session/{session_id}/report")
def openai_transfer_report(session_id: str):
    try:
        session = get_transfer_session(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Transfer session not found") from exc
    with get_conn() as conn:
        row = conn.execute("select sync_job_id from context_transfer_sessions where id=%s", (session_id,)).fetchone()
    report = openai_report(str(row["sync_job_id"])) if row and row["sync_job_id"] else None
    return {"session": session, "report": report, "events": session_events(session_id)}


@router.get("/openai/status")
async def openai_status():
    result = latest_openai_status()
    result["method"] = await resolve_openai_context_sync_method()
    result["folder_watch"] = latest_folder_watch()
    return result


@router.post("/openai/connect")
async def connect_openai(payload: dict | None = None):
    method = await resolve_openai_context_sync_method()
    if method == "official_history_oauth":
        result = await connect("chatgpt", payload)
        return {
            "method": method,
            "next_action": "open_browser" if result.get("authorization_url") else "show_unavailable",
            "authorization_url": result.get("authorization_url") or "",
            "job_id": result.get("job_id") or "",
        }
    if method == "local_export_import":
        return {"method": method, "next_action": "start_sync", "authorization_url": "", "job_id": ""}
    if method == "official_export":
        return {"method": method, "next_action": "open_browser", "authorization_url": OPENAI_EXPORT_URL, "job_id": ""}
    return {"method": "unavailable", "next_action": "show_unavailable", "authorization_url": "", "job_id": ""}


@router.post("/openai/select-export")
async def select_openai_export(file: UploadFile = File(...)):
    return await _create_openai_import(file)


@router.get("/openai/watch-export")
def openai_watch_export_status():
    return {"watch": latest_folder_watch()}


@router.post("/openai/watch-export")
async def openai_watch_export():
    try:
        return {"watch": await authorize_export_folder()}
    except RuntimeError as exc:
        code = str(exc)
        if code == "folder_selection_cancelled":
            raise HTTPException(status_code=409, detail="Folder selection cancelled") from exc
        raise HTTPException(status_code=501, detail="Native folder access is unavailable") from exc


@router.delete("/openai/watch-export/{watch_id}")
def remove_openai_watch_export(watch_id: str):
    try:
        watch = revoke_folder_watch(watch_id)
        with get_conn() as conn:
            conn.execute("update context_transfer_permissions set status='revoked',revoked_at=now() where grant_reference_id=%s and permission_type='selected_folder'", (watch_id,))
        return {"watch": watch}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Folder access not found") from exc


@router.post("/openai/start-import")
async def start_openai_import(payload: dict | None = None):
    existing_job_id = (payload or {}).get("job_id")
    if existing_job_id:
        with get_conn() as conn:
            existing = conn.execute(
                "select id from sync_jobs where id=%s and provider_id='chatgpt'",
                (existing_job_id,),
            ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Import paused")
        _start_durable_job(str(existing["id"]))
        return {"method": "official_export", "next_action": "start_sync", "authorization_url": "", "job_id": str(existing["id"])}

    method = await resolve_openai_context_sync_method()
    approved_path = os.getenv("CONTEXT_SYNC_OPENAI_APPROVED_EXPORT_PATH", "").strip()
    if method != "local_export_import" or not approved_path:
        raise HTTPException(status_code=400, detail="Select export again")
    path = Path(approved_path).expanduser()
    with path.open("rb") as handle:
        upload = UploadFile(file=handle, filename=path.name)
        return await _create_openai_import(upload)


@router.get("/jobs/{job_id}/report")
def openai_job_report(job_id: str):
    report = openai_report(job_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Sync details are not ready")
    return report


@router.post("/jobs/{job_id}/open-most-recent")
def open_most_recent(job_id: str):
    with get_conn() as conn:
        job = conn.execute(
            "select entry_chat_id from sync_jobs where id=%s and provider_id='chatgpt'",
            (job_id,),
        ).fetchone()
    if not job or not job["entry_chat_id"]:
        raise HTTPException(status_code=404, detail="Recent context is not ready")
    chat_id = str(job["entry_chat_id"])
    return {"chat_id": chat_id, "url": f"/?chat={chat_id}"}


@router.delete("/openai/imported-context")
@router.delete("/openai/imported-data")
def delete_openai_imported_data():
    revoke_all_folder_watches()
    with get_conn() as conn:
        conn.execute("update context_transfer_consents set revoked_at=coalesce(revoked_at,now()) where provider='chatgpt'")
        conn.execute("update context_transfer_permissions set status='revoked',revoked_at=coalesce(revoked_at,now()) where provider='chatgpt'")
        conn.execute("delete from context_transfer_sessions where provider='chatgpt'")
        conn.execute("delete from continuity_packages where source_provider='chatgpt'")
        conn.execute("delete from normalized_context_items where provider_id='chatgpt'")
        conn.execute("delete from chats where imported_from_provider='chatgpt'")
        conn.execute("delete from projects where imported_from_provider='chatgpt'")
        conn.execute("delete from sync_jobs where provider_id='chatgpt'")
        conn.execute("delete from context_sync_uploads where provider_id='chatgpt'")
        conn.execute("delete from provider_connections where provider_id='chatgpt'")
    return {"provider_id": "chatgpt", "deleted": True}


@router.get("/providers")
def providers():
    return [_public_provider(provider) for provider in provider_list() if provider["provider_id"] != "other"]


@router.get("/model-connections/active")
def get_active_model_connection():
    return {"connection": active_model_connection()}


@router.post("/model-connections/test")
async def test_model(payload: ModelConnectionIn):
    try:
        result = await test_model_connection(payload)
        return {key: value for key, value in result.items() if key != "api_key"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/model-connections")
async def create_model_connection(payload: ModelConnectionIn):
    try:
        return {"connection": await connect_model(payload)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/model-connections/{connection_id}")
def delete_model_connection(connection_id: str):
    result = disconnect_model(connection_id)
    if not result:
        raise HTTPException(status_code=404, detail="Model connection not found.")
    return result


@router.post("/providers/{provider_id}/capabilities")
def edit_provider_capability(provider_id: str, updates: dict):
    try:
        return _public_provider(update_provider(provider_id, updates))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/connect/{provider}")
async def connect(provider: str, payload: dict | None = None):
    capability = _public_provider(get_provider(provider))
    return_uri = (payload or {}).get("return_uri") or (payload or {}).get("redirect_uri") or "http://127.0.0.1:3000/context-sync"
    if provider == "demo":
        try:
            return await start_broker_connection(provider, return_uri)
        except (ValueError, httpx.HTTPError) as exc:
            raise HTTPException(status_code=503, detail="Demo authorization service is unavailable") from exc
    if not capability["oauth_ready"]:
        return {
            "provider_id": provider,
            "connection_id": "",
            "next_action": "unavailable",
            "user_message": f"Secure sign-in for {capability['display_name']} is not available yet.",
        }

    with get_conn() as conn:
        connection = conn.execute(
            """
            insert into provider_connections (provider_id, display_name, auth_method, status)
            values (%s,%s,'oauth_pkce','connecting')
            returning id
            """,
            (provider, capability["display_name"]),
        ).fetchone()
    connection_id = str(connection["id"])
    try:
        return begin_oauth_connection(provider, connection_id, return_uri)
    except ValueError as exc:
        with get_conn() as conn:
            conn.execute("delete from provider_connections where id=%s", (connection_id,))
        raise HTTPException(status_code=400, detail="Connection temporarily unavailable") from exc


@router.post("/connections/{provider}/authorize")
async def authorize(provider: str, payload: dict | None = None):
    return await connect(provider, payload)


@router.post("/official-export/{provider}")
async def official_export(provider: str, background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    capability = get_provider(provider)
    if capability["provider_id"] != provider or "official_export" not in capability.get("connection_methods", []):
        raise HTTPException(status_code=400, detail="Official export import is not supported for this provider")
    filename = file.filename or ""
    if not filename.lower().endswith((".zip", ".json", ".csv", ".txt", ".md")):
        raise HTTPException(status_code=400, detail="Choose an official ZIP, JSON, CSV, TXT, or Markdown export")
    try:
        upload = await create_upload_inventory(provider, file)
        stored = load_upload(upload["inventory"]["upload_token"])
        if not stored:
            raise ValueError("The encrypted local import could not be prepared")
        inventory = stored["inventory"]
        normalized = inventory.pop("normalized", {})
        job_id = create_job(provider, stored["connection_id"], inventory, normalized)
        _start_durable_job(job_id)
        return {
            "provider_id": provider,
            "connection_id": stored["connection_id"],
            "next_action": "sync",
            "job_id": job_id,
            "user_message": None,
        }
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="The selected export could not be read") from exc


@router.get("/callback/{provider}")
@router.get("/connections/{provider}/callback")
async def callback(provider: str, background_tasks: BackgroundTasks, code: str | None = None, state: str | None = None, error: str | None = None):
    default_return = "http://127.0.0.1:3000/context-sync"
    if error:
        return RedirectResponse(f"{default_return}?provider={provider}&error=connection_expired", status_code=303)
    if not code or not state:
        return RedirectResponse(f"{default_return}?provider={provider}&error=connection_expired", status_code=303)
    try:
        connection = await complete_oauth_connection(provider, code, state)
        inventory = await fetch_oauth_context(provider, connection["connection_id"])
        inventory_data = inventory.model_dump()
        normalized = inventory_data.pop("normalized", {})
        job_id = create_job(provider, connection["connection_id"], inventory_data, normalized)
        _start_durable_job(job_id)
        separator = "&" if "?" in connection["return_uri"] else "?"
        return RedirectResponse(
            f"{connection['return_uri']}{separator}job={job_id}&provider={provider}",
            status_code=303,
        )
    except (ValueError, httpx.HTTPError, JoseError):
        return RedirectResponse(f"{default_return}?provider={provider}&error=connection_temporarily_unavailable", status_code=303)


@router.get("/device-callback/{provider}")
async def device_callback(provider: str, background_tasks: BackgroundTasks, grant_id: str | None = None, state: str | None = None):
    default_return = "http://127.0.0.1:3000/context-sync"
    if provider != "demo" or not grant_id or not state:
        return RedirectResponse(f"{default_return}?provider={provider}&error=connection_expired", status_code=303)
    try:
        result = await exchange_broker_grant(provider, grant_id, state)
        inventory_data = result["inventory"].model_dump()
        normalized = inventory_data.pop("normalized", {})
        job_id = create_job(provider, result["connection_id"], inventory_data, normalized)
        _start_durable_job(job_id)
        separator = "&" if "?" in result["return_uri"] else "?"
        return RedirectResponse(f"{result['return_uri']}{separator}job={job_id}&provider={provider}", status_code=303)
    except (ValueError, httpx.HTTPError):
        return RedirectResponse(f"{default_return}?provider={provider}&error=connection_temporarily_unavailable", status_code=303)


@router.post("/disconnect/{connection_id}")
async def disconnect_connection(connection_id: str):
    with get_conn() as conn:
        existing = conn.execute("select provider_id,broker_connection_id from provider_connections where id=%s", (connection_id,)).fetchone()
    if existing and existing["broker_connection_id"]:
        await revoke_broker_connection(str(existing["broker_connection_id"]))
    else:
        await revoke_oauth_connection(connection_id)
    with get_conn() as conn:
        row = conn.execute(
            """
            update provider_connections
            set status='disconnected',encrypted_token_json='{}'::jsonb,disconnected_at=now(),updated_at=now()
            where id=%s returning provider_id
            """,
            (connection_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Connection expired")
    return {"connection_id": connection_id, "status": "disconnected"}


@router.post("/connections/{provider}/disconnect")
def disconnect(provider: str):
    with get_conn() as conn:
        conn.execute(
            "update provider_connections set status='disconnected',encrypted_token_json='{}'::jsonb,disconnected_at=now(),updated_at=now() where provider_id=%s",
            (provider,),
        )
    return {"provider_id": provider, "status": "disconnected"}


@router.get("/connections")
def connections():
    with get_conn() as conn:
        return conn.execute(
            "select id,provider_id,display_name,auth_method,status,created_at,updated_at,disconnected_at from provider_connections order by created_at desc"
        ).fetchall()


@router.get("/jobs")
def list_jobs():
    with get_conn() as conn:
        return conn.execute("select * from sync_jobs order by created_at desc limit 50").fetchall()


@router.get("/jobs/{job_id}")
def job_detail(job_id: str):
    with get_conn() as conn:
        job = conn.execute("select * from sync_jobs where id=%s", (job_id,)).fetchone()
    if not job:
        raise HTTPException(status_code=404, detail="Sync paused")
    return job


@router.get("/jobs/{job_id}/events")
def job_events(job_id: str):
    with get_conn() as conn:
        return conn.execute("select * from sync_job_events where job_id=%s order by created_at asc", (job_id,)).fetchall()


@router.post("/jobs/{job_id}/pause")
def pause(job_id: str):
    with get_conn() as conn:
        conn.execute("update sync_jobs set status='paused_auth_required',updated_at=now() where id=%s", (job_id,))
    return {"job_id": job_id, "status": "paused_auth_required"}


@router.post("/jobs/{job_id}/resume")
def resume(job_id: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(enqueue_job, job_id)
    return {"job_id": job_id, "status": "running"}


@router.post("/jobs/{job_id}/cancel")
def cancel(job_id: str):
    with get_conn() as conn:
        conn.execute("update sync_jobs set status='cancelled',updated_at=now() where id=%s", (job_id,))
    return {"job_id": job_id, "status": "cancelled"}


@router.post("/retry/{job_id}")
@router.post("/jobs/{job_id}/retry")
def retry(job_id: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(enqueue_job, job_id)
    return {"job_id": job_id, "status": "retrying"}


@router.post("/sync-now/{connection_id}")
def sync_now(connection_id: str):
    return {"connection_id": connection_id, "status": "manual_sync_requires_provider_incremental_support"}


@router.get("/status")
def status():
    data = latest_status()
    return {
        "active_job": _public_job(data["active_job"]) if data.get("active_job") else None,
        "recent_jobs": [_public_job(job) for job in data.get("recent_jobs", [])],
    }


@router.get("/status/{job_id}")
def status_detail(job_id: str):
    with get_conn() as conn:
        job = conn.execute("select * from sync_jobs where id=%s", (job_id,)).fetchone()
    if not job:
        raise HTTPException(status_code=404, detail="Sync paused")
    return _public_job(job)


@router.get("/exceptions/{job_id}")
def exceptions(job_id: str):
    with get_conn() as conn:
        return conn.execute("select * from sync_exceptions where job_id=%s order by created_at desc", (job_id,)).fetchall()


@router.get("/coverage/{job_id}")
def coverage(job_id: str):
    with get_conn() as conn:
        job = conn.execute("select * from sync_jobs where id=%s", (job_id,)).fetchone()
        packages = conn.execute("select count(*) as count from continuity_packages where job_id=%s", (job_id,)).fetchone()["count"]
    inventory = job["inventory_json"] if job else {}
    return {"job_id": job_id, "transfer": inventory, "continuity_packages": packages, "status": job["status"] if job else "unknown"}


@router.get("/validation/{job_id}")
def validation_report(job_id: str):
    with get_conn() as conn:
        row = conn.execute("select report_json from sync_validation_reports where job_id=%s", (job_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Validation report is not ready")
    return row["report_json"]


@router.delete("/imported-data/{provider}")
def delete_imported(provider: str):
    with get_conn() as conn:
        conn.execute("delete from continuity_packages where source_provider=%s", (provider,))
        conn.execute("delete from normalized_context_items where provider_id=%s", (provider,))
        conn.execute("delete from chats where imported_from_provider=%s", (provider,))
        conn.execute("delete from projects where imported_from_provider=%s", (provider,))
        conn.execute("delete from provider_connections where provider_id=%s", (provider,))
    return {"provider_id": provider, "deleted": True}


@router.get("/export-portable")
def export_portable(provider_id: str | None = None):
    return portable_export(provider_id)


@router.get("/events/{job_id}")
async def events_stream(job_id: str):
    async def event_generator():
        seen: set[str] = set()
        while True:
            with get_conn() as conn:
                job = conn.execute("select * from sync_jobs where id=%s", (job_id,)).fetchone()
                events = conn.execute("select id from sync_job_events where job_id=%s order by created_at asc", (job_id,)).fetchall()
            if not job:
                yield f"event: progress\ndata: {json.dumps({'status': 'failed_recoverable', 'display_message': 'Sync paused'})}\n\n"
                return
            unseen = [event for event in events if str(event["id"]) not in seen]
            if unseen:
                payload = json.dumps(_public_job(job), default=str)
                for event in unseen:
                    seen.add(str(event["id"]))
                    yield f"event: progress\ndata: {payload}\n\n"
            if job["status"] in {"completed", "completed_with_exceptions", "cancelled"}:
                return
            await asyncio.sleep(0.6)

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
