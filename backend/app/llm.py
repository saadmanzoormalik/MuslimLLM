import asyncio
import hashlib
import json
import os
import re
import time
from collections.abc import AsyncIterator
from urllib.parse import urlparse

import httpx
import numpy as np

from .context_sync.model_connections import RuntimeModelConnection, runtime_model_connection


LLM_API_BASE = os.getenv("LLM_API_BASE", "http://127.0.0.1:11434/v1").rstrip("/")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "muslim-llm-local")
EMBEDDING_API_BASE = os.getenv("EMBEDDING_API_BASE", LLM_API_BASE).rstrip("/")
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", LLM_API_KEY)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
OPEN_SOURCE_LLM_FALLBACK = os.getenv("OPEN_SOURCE_LLM_FALLBACK", "true").lower() in {"1", "true", "yes", "on"}
LLM_CONNECT_TIMEOUT = float(os.getenv("LLM_CONNECT_TIMEOUT", "2"))
LLM_READ_TIMEOUT = float(os.getenv("LLM_READ_TIMEOUT", "90"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "700"))
LLM_MAX_CONCURRENT_REQUESTS = int(os.getenv("LLM_MAX_CONCURRENT_REQUESTS", "2"))
LLM_REQUEST_QUEUE_TIMEOUT_SECONDS = float(os.getenv("LLM_REQUEST_QUEUE_TIMEOUT_SECONDS", "10"))
LLM_KEEP_ALIVE_DURATION = os.getenv("LLM_KEEP_ALIVE_DURATION", "10m")
LLM_WARMUP_ON_START = os.getenv("LLM_WARMUP_ON_START", "true").lower() in {"1", "true", "yes", "on"}
LLM_KEEP_WARM = os.getenv("LLM_KEEP_WARM", "true").lower() in {"1", "true", "yes", "on"}
_HTTP_CLIENT: httpx.AsyncClient | None = None
_MODEL_SEMAPHORE = asyncio.Semaphore(LLM_MAX_CONCURRENT_REQUESTS)
MODEL_RUNTIME_STATE = {"warm": False, "last_warmup_ms": None, "last_request_at": None, "active_requests": 0}

LOCAL_LLM_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "ollama", "host.docker.internal"}


async def embed_text(text: str) -> list[float]:
    if EMBEDDING_API_BASE and EMBEDDING_API_KEY:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{EMBEDDING_API_BASE}/embeddings",
                headers={"Authorization": f"Bearer {EMBEDDING_API_KEY}"},
                json={"model": EMBEDDING_MODEL, "input": text[:8000]},
            )
            response.raise_for_status()
            return response.json()["data"][0]["embedding"]
    return deterministic_embedding(text)


def shared_client() -> httpx.AsyncClient:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None or _HTTP_CLIENT.is_closed:
        _HTTP_CLIENT = httpx.AsyncClient(timeout=httpx.Timeout(LLM_READ_TIMEOUT, connect=LLM_CONNECT_TIMEOUT))
    return _HTTP_CLIENT


def deterministic_embedding(text: str, dimensions: int = 1536) -> list[float]:
    vector = np.zeros(dimensions, dtype=np.float32)
    words = text.lower().split()
    for word in words:
        digest = hashlib.sha256(word.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1 if digest[4] % 2 == 0 else -1
        vector[idx] += sign
    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm
    return vector.tolist()


def resolve_model(model: str | None = None, runtime_model: str | None = None) -> str:
    if not model or model == "muslim-llm-core":
        return runtime_model or runtime_model_connection().model
    return model


def is_local_open_source_endpoint(api_base: str) -> bool:
    host = urlparse(api_base).hostname or ""
    return host in LOCAL_LLM_HOSTS


def llm_headers(api_key: str | None = None) -> dict[str, str]:
    key = LLM_API_KEY if api_key is None else api_key
    if not key:
        return {}
    return {"Authorization": f"Bearer {key}"}


def should_call_llm() -> bool:
    runtime = runtime_model_connection()
    return bool(runtime.api_base and (runtime.api_key or is_local_open_source_endpoint(runtime.api_base)))


def current_model_connection() -> RuntimeModelConnection:
    return runtime_model_connection()


def offline_completion(messages: list[dict]) -> str:
    user_messages = [message["content"] for message in messages if message.get("role") == "user"]
    question = user_messages[-1] if user_messages else ""
    lower = question.lower()

    if "zakat" in lower:
        return (
            "Zakat is the obligatory annual giving due on certain forms of wealth when they reach the required threshold, meant to purify wealth, support the vulnerable, and keep economic life tied to worship and social responsibility."
        )

    if "salah" in lower or "prayer" in lower:
        return (
            "Salah is the five daily prayer obligation that anchors a Muslim's day in worship, discipline, remembrance of Allah, and moral accountability."
        )

    if "ramadan" in lower or "fasting" in lower:
        return (
            "Ramadan is the month of obligatory fasting from dawn to sunset, centered on taqwa, Quran, self-restraint, charity, and renewal of one's relationship with Allah."
        )

    if any(word in lower for word in ["caliphate", "caliph", "khilafah", "khalifah"]):
        return (
            "Some recurring issues in caliphate history were succession disputes, tribal and regional rivalries, tension between religious legitimacy and political power, uneven treatment of non-Arab or frontier populations, fiscal pressure, court factionalism, and the difficulty of governing vast, diverse territories. From a Muslim-civilizational lens, the strongest periods usually combined justice, consultation, legal scholarship, administrative competence, public welfare, and secure trade; decline often came when power became dynastic, coercive, corrupt, or detached from accountability."
        )

    if any(word in lower for word in ["fiqh", "madhab", "fatwa", "halal", "haram", "ruling", "sharia", "zakat", "salah", "hajj", "ramadan", "wudu"]):
        return (
            "In Islamic law, the right answer depends on the act, evidence, context, and sometimes madhab. A sound approach is to separate what is agreed from what is disputed, explain the reasoning clearly, and avoid presenting one school as the only valid Muslim position."
        )

    if any(word in lower for word in ["abbasid", "ottoman", "umayyad", "mamluk", "andalus", "trade", "civilization", "history", "governance", "science", "empire", "dynasty"]):
        if "trade" in lower:
            return (
                "Muslim trade networks connected the Indian Ocean, Mediterranean, Sahara, Silk Roads, and East African coast, moving not only goods but also law, language, trust, scholarship, and technologies across regions."
            )
        return (
            "A Muslim civilizational lens looks at institutions, scholarship, markets, law, endowments, diplomacy, and moral ideals while still separating Islamic principles from the political realities of each dynasty and region."
        )

    if any(word in lower for word in ["code", "python", "javascript", "api", "bug", "write", "draft", "plan", "strategy", "summarize"]):
        return (
            "Send the goal, constraints, and desired format. I will make it practical and concise."
        )

    return (
        "Tell me the specific question or task, and I will answer directly."
    )


async def stream_completion(messages: list[dict], model: str | None = None, temperature: float = 0.3, max_tokens: int | None = None, runtime_metrics: dict | None = None) -> AsyncIterator[str]:
    runtime = current_model_connection()
    if runtime.api_base and (runtime.api_key or is_local_open_source_endpoint(runtime.api_base)):
        queue_started = time.monotonic()
        acquired = False
        try:
            await asyncio.wait_for(_MODEL_SEMAPHORE.acquire(), timeout=LLM_REQUEST_QUEUE_TIMEOUT_SECONDS)
            acquired = True
            MODEL_RUNTIME_STATE["active_requests"] += 1
            if runtime_metrics is not None:
                runtime_metrics["queue_wait_ms"] = round((time.monotonic() - queue_started) * 1000, 2)
            client = shared_client()
            async with client.stream(
                    "POST",
                    f"{runtime.api_base}/chat/completions",
                    headers=llm_headers(runtime.api_key),
                    json={
                        "model": resolve_model(model, runtime.model),
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens or LLM_MAX_TOKENS,
                        "stream": True,
                        "keep_alive": LLM_KEEP_ALIVE_DURATION,
                    },
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        payload = line.removeprefix("data: ")
                        if payload == "[DONE]":
                            break
                        data = json.loads(payload)
                        delta = data["choices"][0].get("delta", {}).get("content", "")
                        if delta:
                            MODEL_RUNTIME_STATE["warm"] = True
                            MODEL_RUNTIME_STATE["last_request_at"] = time.time()
                            yield delta
            return
        except (httpx.HTTPError, json.JSONDecodeError, KeyError, TimeoutError, ValueError):
            if not OPEN_SOURCE_LLM_FALLBACK:
                raise
        finally:
            if acquired:
                MODEL_RUNTIME_STATE["active_requests"] -= 1
                _MODEL_SEMAPHORE.release()

    fallback = offline_completion(messages)
    for token in re.split(r"(\s+)", fallback):
        if token:
            yield token


async def warmup_model() -> dict:
    if not LLM_WARMUP_ON_START or not should_call_llm():
        return MODEL_RUNTIME_STATE
    runtime = current_model_connection()
    started = time.monotonic()
    try:
        response = await shared_client().post(
            f"{runtime.api_base}/chat/completions",
            headers=llm_headers(runtime.api_key),
            json={"model": runtime.model, "messages": [{"role": "user", "content": "Reply: ready"}], "temperature": 0, "max_tokens": 2, "stream": False, "keep_alive": LLM_KEEP_ALIVE_DURATION},
            timeout=30,
        )
        response.raise_for_status()
        MODEL_RUNTIME_STATE["warm"] = True
    except Exception:
        MODEL_RUNTIME_STATE["warm"] = False
    MODEL_RUNTIME_STATE["last_warmup_ms"] = round((time.monotonic() - started) * 1000, 2)
    return MODEL_RUNTIME_STATE


async def keep_warm_loop():
    while LLM_KEEP_WARM:
        await asyncio.sleep(240)
        if time.time() - float(MODEL_RUNTIME_STATE.get("last_request_at") or 0) > 180:
            await warmup_model()
