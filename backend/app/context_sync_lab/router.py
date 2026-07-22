import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from .config import enabled
from .promotion import promote
from .service import (
    cancel_job,
    delete_all_data,
    delete_job,
    get_events,
    get_job,
    list_jobs,
    preview,
    retry_job,
    save_upload,
    test_continuation,
    test_openai_api,
    validation,
)


def require_lab() -> None:
    if not enabled():
        raise HTTPException(status_code=404, detail="Not found")


router = APIRouter(prefix="/context-sync-lab", tags=["context-sync-lab"], dependencies=[Depends(require_lab)])


@router.get("/providers")
def providers():
    jobs = list_jobs()
    latest = jobs[0] if jobs else None
    return {
        "environment": "lab",
        "local_processing": os.getenv("CONTEXT_SYNC_LOCAL_PROCESSING", "true").lower() == "true",
        "cloud_content_upload": os.getenv("CONTEXT_SYNC_ALLOW_CLOUD_CONTENT_UPLOAD", "false").lower() == "true",
        "providers": [
            {"id": "openai", "name": "OpenAI / ChatGPT", "available": True, "method": "official_export", "state": latest["status"] if latest else "not_connected"},
            {"id": "claude", "name": "Claude", "available": False, "method": "future_connector", "state": "coming_soon"},
            {"id": "gemini", "name": "Gemini", "available": False, "method": "future_connector", "state": "coming_soon"},
            {"id": "demo", "name": "Demo Provider", "available": True, "method": "fixture", "state": "available"},
        ],
        "chatgpt_context": "connected_through_export" if latest and latest["status"].startswith("completed") else "not_connected",
    }


@router.post("/openai/request-export")
def request_export():
    return {
        "status": "export_requested",
        "url": "https://help.openai.com/en/articles/7260999-exporting-your-chatgpt-history-and-data",
        "message": "ChatGPT will provide a secure export download when it is ready.",
        "password_requested": False,
    }


@router.post("/openai/select-export")
def select_export(file: UploadFile = File(...)):
    return save_upload(file)


@router.post("/openai/import")
def import_export(payload: dict):
    job_id = str(payload.get("job_id") or "")
    if not job_id:
        raise HTTPException(status_code=400, detail="job_id is required")
    return retry_job(job_id)


@router.get("/jobs")
def jobs():
    return list_jobs()


@router.get("/jobs/{job_id}")
def job(job_id: str):
    return get_job(job_id)


@router.get("/jobs/{job_id}/events")
def events(job_id: str):
    return get_events(job_id)


@router.get("/jobs/{job_id}/preview")
def job_preview(job_id: str):
    return preview(job_id)


@router.get("/jobs/{job_id}/validation")
def job_validation(job_id: str):
    return validation(job_id)


@router.post("/jobs/{job_id}/retry")
def retry(job_id: str):
    return retry_job(job_id)


@router.post("/jobs/{job_id}/cancel")
def cancel(job_id: str):
    return cancel_job(job_id)


@router.post("/jobs/{job_id}/test-continuation")
async def continuation(job_id: str, payload: dict):
    source_id = str(payload.get("source_conversation_id") or "")
    question = str(payload.get("question") or "Continue from where this conversation stopped.")
    if not source_id:
        raise HTTPException(status_code=400, detail="Select an imported conversation.")
    return await test_continuation(job_id, source_id, question)


@router.post("/jobs/{job_id}/promote")
def promote_job(job_id: str, payload: dict | None = None):
    return promote(job_id, bool((payload or {}).get("include_suggested_projects", False)))


@router.post("/openai-api/test")
async def api_test(payload: dict):
    return await test_openai_api(payload)


@router.delete("/jobs/{job_id}")
def remove_job(job_id: str):
    return delete_job(job_id)


@router.delete("/data")
def remove_data():
    return delete_all_data()
