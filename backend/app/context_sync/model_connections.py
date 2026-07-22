import asyncio
import ipaddress
import json
import os
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field

from ..db import get_conn
from .security.token_vault import decrypt_token, encrypt_token


LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "host.docker.internal", "ollama"}
DEFAULT_LOCAL_API_BASE = os.getenv("LLM_API_BASE", "http://127.0.0.1:11434/v1").rstrip("/")
DEFAULT_LOCAL_MODEL = os.getenv("LLM_MODEL", "muslim-llm-local")


class ModelConnectionIn(BaseModel):
    mode: str = Field(pattern="^(local|remote)$")
    api_base: str | None = Field(default=None, max_length=500)
    model: str | None = Field(default=None, max_length=200)
    api_key: str | None = Field(default=None, max_length=2000)


@dataclass(frozen=True)
class RuntimeModelConnection:
    api_base: str
    model: str
    api_key: str
    mode: str
    connection_id: str | None = None


def _normalized_api_base(payload: ModelConnectionIn) -> str:
    value = (payload.api_base or DEFAULT_LOCAL_API_BASE).strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Enter a valid model API URL.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("The model API URL cannot contain credentials, query parameters, or fragments.")
    if payload.mode == "remote" and parsed.scheme != "https":
        raise ValueError("Remote model connections must use HTTPS.")
    if payload.mode == "local" and parsed.hostname not in LOCAL_HOSTS:
        raise ValueError("Local connections are limited to this device or the local Docker network.")
    return value


async def _validate_remote_host(api_base: str, mode: str) -> None:
    if mode == "local":
        return
    host = urlparse(api_base).hostname or ""
    try:
        addresses = await asyncio.to_thread(socket.getaddrinfo, host, None)
    except socket.gaierror as exc:
        raise ValueError("The model API host could not be resolved.") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
            raise ValueError("Remote model connections cannot target private or reserved networks.")


def _headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"} if api_key else {}


async def test_model_connection(payload: ModelConnectionIn) -> dict:
    api_base = _normalized_api_base(payload)
    await _validate_remote_host(api_base, payload.mode)
    model = (payload.model or (DEFAULT_LOCAL_MODEL if payload.mode == "local" else "")).strip()
    api_key = (payload.api_key or "").strip()

    timeout = httpx.Timeout(30, connect=5)
    models: list[str] = []
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        try:
            response = await client.get(f"{api_base}/models", headers=_headers(api_key))
            response.raise_for_status()
            for item in response.json().get("data", []):
                name = item.get("id") or item.get("name")
                if name:
                    models.append(str(name))
        except (httpx.HTTPError, ValueError, KeyError):
            if not model:
                raise ValueError("The endpoint did not expose a compatible model list.")

        if not model and models:
            model = models[0]
        if not model:
            raise ValueError("Enter a model ID.")

        try:
            response = await client.post(
                f"{api_base}/chat/completions",
                headers=_headers(api_key),
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "Return only the word ready."},
                        {"role": "user", "content": "Connection test."},
                    ],
                    "temperature": 0,
                    "max_tokens": 16,
                    "stream": False,
                },
            )
            response.raise_for_status()
            message = response.json().get("choices", [{}])[0].get("message", {})
            content = message.get("content") or message.get("reasoning_content") or ""
            if not str(content).strip():
                raise ValueError("The model returned an empty test response.")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {401, 403}:
                raise ValueError("The API credential was not accepted.") from exc
            raise ValueError("The model endpoint rejected the connection test.") from exc
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            if isinstance(exc, ValueError):
                raise
            raise ValueError("The model endpoint could not complete a test response.") from exc

    return {
        "ok": True,
        "api_base": api_base,
        "model": model,
        "mode": payload.mode,
        "models_found": len(models),
        "api_key": api_key,
    }


async def connect_model(payload: ModelConnectionIn) -> dict:
    tested = await test_model_connection(payload)
    encrypted = encrypt_token({"api_key": tested.pop("api_key")})
    with get_conn() as conn:
        conn.execute(
            """
            update provider_connections
            set status='connected',updated_at=now()
            where auth_method in ('api_key','local_no_auth') and status='active'
            """
        )
        row = conn.execute(
            """
            insert into provider_connections
              (provider_id,display_name,auth_method,status,api_base,api_model,encrypted_token_json,
               connection_metadata_json,last_checked_at)
            values ('model_endpoint','Muslim LLM model',%s,'active',%s,%s,%s::jsonb,%s::jsonb,now())
            returning id,api_base,api_model,status,last_checked_at
            """,
            (
                "local_no_auth" if tested["mode"] == "local" and not payload.api_key else "api_key",
                tested["api_base"],
                tested["model"],
                json.dumps(encrypted),
                json.dumps({"mode": tested["mode"], "models_found": tested["models_found"]}),
            ),
        ).fetchone()
    return _public_connection(row, tested["mode"])


def _public_connection(row: dict, mode: str | None = None) -> dict:
    parsed = urlparse(row["api_base"])
    return {
        "id": str(row["id"]),
        "status": row["status"],
        "mode": mode or ("local" if parsed.hostname in LOCAL_HOSTS else "remote"),
        "endpoint": parsed.hostname or "configured endpoint",
        "model": "Muslim LLM",
        "last_checked_at": str(row["last_checked_at"]) if row.get("last_checked_at") else None,
    }


def active_model_connection() -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            """
            select id,api_base,api_model,status,last_checked_at
            from provider_connections
            where auth_method in ('api_key','local_no_auth') and status='active'
            order by updated_at desc limit 1
            """
        ).fetchone()
    return _public_connection(row) if row else None


def runtime_model_connection() -> RuntimeModelConnection:
    try:
        with get_conn() as conn:
            row = conn.execute(
                """
                select id,api_base,api_model,auth_method,encrypted_token_json
                from provider_connections
                where auth_method in ('api_key','local_no_auth') and status='active'
                order by updated_at desc limit 1
                """
            ).fetchone()
        if row:
            secret = decrypt_token(row["encrypted_token_json"] or {})
            return RuntimeModelConnection(
                api_base=row["api_base"].rstrip("/"),
                model=row["api_model"],
                api_key=secret.get("api_key", ""),
                mode="local" if urlparse(row["api_base"]).hostname in LOCAL_HOSTS else "remote",
                connection_id=str(row["id"]),
            )
    except Exception:
        pass
    return RuntimeModelConnection(
        api_base=DEFAULT_LOCAL_API_BASE,
        model=DEFAULT_LOCAL_MODEL,
        api_key=os.getenv("LLM_API_KEY", ""),
        mode="local" if urlparse(DEFAULT_LOCAL_API_BASE).hostname in LOCAL_HOSTS else "remote",
    )


def disconnect_model(connection_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            """
            update provider_connections
            set status='disconnected',encrypted_token_json='{}'::jsonb,disconnected_at=now(),updated_at=now()
            where id=%s and auth_method in ('api_key','local_no_auth')
            returning id
            """,
            (connection_id,),
        ).fetchone()
    return {"id": str(row["id"]), "status": "disconnected"} if row else None
