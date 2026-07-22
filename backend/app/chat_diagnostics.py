import os
from datetime import datetime, timezone
from typing import Any

import httpx

from .db import get_conn
from .llm import current_model_connection, llm_headers, should_call_llm

LAST_CHAT_ERROR: dict[str, Any] | None = None


def record_chat_error(request_id: str, stage: str, message: str, recoverable: bool = True) -> None:
    global LAST_CHAT_ERROR
    LAST_CHAT_ERROR = {
        "request_id": request_id,
        "stage": stage,
        "message": message,
        "recoverable": recoverable,
        "at": datetime.now(timezone.utc).isoformat(),
    }


async def run_chat_diagnostics() -> dict[str, Any]:
    runtime = current_model_connection()
    database = check_database()
    local_model_api = await check_model_api(runtime)
    model_response_test = await check_model_response(runtime) if local_model_api["ok"] else {"ok": False, "detail": "Model API unavailable."}
    loaded_models = local_model_api.get("models", [])
    local_model_loaded = any(runtime.model in model for model in loaded_models) if loaded_models else local_model_api["ok"]
    streaming = {"ok": model_response_test["ok"], "detail": "Streaming path uses the same local chat endpoint."}
    recommendations: list[str] = []

    if not database["ok"]:
        recommendations.append("Restart PostgreSQL or check DATABASE_URL.")
    if not local_model_api["ok"]:
        recommendations.append("Start Ollama or the configured OpenAI-compatible local model server.")
    if local_model_api["ok"] and not local_model_loaded:
        recommendations.append(f"Load or pull the configured local model for Muslim LLM.")
    if local_model_api["ok"] and not model_response_test["ok"]:
        recommendations.append("The model server is reachable but did not return a valid chat response.")
    if not recommendations:
        recommendations.append("Chat pipeline is reachable.")

    return {
        "backend": {"ok": True, "app": os.getenv("APP_NAME", "Muslim LLM")},
        "database": database,
        "local_model_api": local_model_api,
        "local_model_loaded": {"ok": bool(local_model_loaded), "display_name": "Muslim LLM Local"},
        "model_response_test": model_response_test,
        "streaming": streaming,
        "last_error": LAST_CHAT_ERROR,
        "recommendations": recommendations,
    }


def check_database() -> dict[str, Any]:
    try:
        with get_conn() as conn:
            conn.execute("select 1").fetchone()
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "detail": type(exc).__name__}


async def check_model_api(runtime=None) -> dict[str, Any]:
    runtime = runtime or current_model_connection()
    if not should_call_llm():
        return {"ok": False, "detail": "No local model endpoint configured.", "models": []}
    models: list[str] = []
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{runtime.api_base}/models", headers=llm_headers(runtime.api_key))
            response.raise_for_status()
            payload = response.json()
            for item in payload.get("data", []):
                model_name = item.get("id") or item.get("name")
                if model_name:
                    models.append(str(model_name))
        return {"ok": True, "display_name": "Muslim LLM Local", "models": models}
    except Exception as exc:
        return {"ok": False, "detail": type(exc).__name__, "models": models}


async def check_model_response(runtime=None) -> dict[str, Any]:
    runtime = runtime or current_model_connection()
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{runtime.api_base}/chat/completions",
                headers=llm_headers(runtime.api_key),
                json={
                    "model": runtime.model,
                    "messages": [
                        {"role": "system", "content": "Reply with one short sentence."},
                        {"role": "user", "content": "Say ready."},
                    ],
                    "temperature": 0,
                    "max_tokens": 24,
                    "stream": False,
                },
            )
            response.raise_for_status()
            payload = response.json()
            content = payload.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {"ok": bool(content.strip()), "display_name": "Muslim LLM Local"}
    except Exception as exc:
        return {"ok": False, "detail": type(exc).__name__}
