import json
import os
import platform
import secrets
from urllib.parse import urlparse

import httpx

from ..db import get_conn
from .device_auth import claim_device_transaction, complete_device_transaction, fail_device_transaction, save_device_transaction
from .device_identity import load_device_identity
from .provider_inventory import fetch_provider_inventory
from .security.token_vault import encrypt_token


AUTH_BROKER_URL = os.getenv("AUTH_BROKER_URL", "http://127.0.0.1:8100").rstrip("/")
DEVICE_CALLBACK_BASE = os.getenv("CONTEXT_SYNC_DEVICE_CALLBACK_BASE", "http://127.0.0.1:8000/context-sync/device-callback").rstrip("/")
ALLOWED_RETURN_ORIGINS = set(filter(None, os.getenv("CONTEXT_SYNC_ALLOWED_RETURN_ORIGINS", "http://127.0.0.1:3000,http://localhost:3000").split(",")))


def _validate_return_uri(uri: str) -> str:
    parsed = urlparse(uri)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if origin not in ALLOWED_RETURN_ORIGINS or parsed.path != "/context-sync":
        raise ValueError("Return URI is not allowed")
    return uri


async def start_broker_connection(provider: str, return_uri: str) -> dict:
    if provider != "demo":
        raise ValueError("Broker connector is not enabled for this provider")
    return_uri = _validate_return_uri(return_uri)
    identity = load_device_identity()
    public = identity.public_bundle()
    device_state = secrets.token_urlsafe(40)
    with get_conn() as conn:
        local = conn.execute(
            """
            insert into provider_connections (provider_id,display_name,auth_method,status,connection_metadata_json)
            values ('demo','Demo AI Account','broker_oauth','connecting','{"development_only":true}'::jsonb)
            returning id
            """
        ).fetchone()
    local_connection_id = str(local["id"])
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
            response = await client.post(
                f"{AUTH_BROKER_URL}/v1/connections/{provider}/start",
                json={
                    "device_callback_uri": f"{DEVICE_CALLBACK_BASE}/{provider}",
                    "device_signing_public_key": public["signing_public_key"],
                    "device_encryption_public_key": public["encryption_public_key"],
                    "device_state": device_state,
                    "platform": platform.system().lower(),
                    "app_version": os.getenv("APP_VERSION", "development"),
                    "requested_capability": "context_sync",
                },
            )
            response.raise_for_status()
            broker = response.json()
        if broker.get("method") != "oauth" or not broker.get("authorization_url") or not broker.get("connection_id"):
            raise ValueError("Authorization broker did not offer an OAuth connection")
        save_device_transaction(provider, local_connection_id, broker["connection_id"], device_state, return_uri)
        with get_conn() as conn:
            conn.execute("update provider_connections set broker_connection_id=%s,updated_at=now() where id=%s", (broker["connection_id"], local_connection_id))
        return {
            "provider_id": provider,
            "connection_id": local_connection_id,
            "next_action": "redirect",
            "authorization_url": broker["authorization_url"],
            "user_message": None,
        }
    except Exception:
        with get_conn() as conn:
            conn.execute("delete from provider_connections where id=%s", (local_connection_id,))
        raise


async def exchange_broker_grant(provider: str, grant_id: str, state: str) -> dict:
    transaction = claim_device_transaction(provider, state)
    identity = load_device_identity()
    public = identity.public_bundle()
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            response = await client.post(
                f"{AUTH_BROKER_URL}/v1/grants/{grant_id}/exchange",
                json={"device_signing_public_key": public["signing_public_key"], "signature": identity.sign_grant(grant_id)},
            )
            response.raise_for_status()
            grant = response.json()
        if grant.get("provider") != provider or grant.get("connection_id") != str(transaction["broker_connection_id"]):
            raise ValueError("Broker grant binding does not match the device transaction")
        token_package = identity.decrypt_grant(grant["token_envelope"], grant_id)
        inventory, account_hash = await fetch_provider_inventory(token_package)
        encrypted = encrypt_token(token_package)
        with get_conn() as conn:
            conn.execute(
                """
                update provider_connections
                set status='connected',source_account_hash=%s,scopes_json=%s::jsonb,encrypted_token_json=%s::jsonb,
                    automatic_sync_enabled=true,incremental_sync_enabled=false,updated_at=now()
                where id=%s
                """,
                (
                    account_hash,
                    json.dumps(str(token_package.get("scope", "")).split()),
                    json.dumps(encrypted),
                    transaction["local_connection_id"],
                ),
            )
        complete_device_transaction(str(transaction["id"]))
        return {
            "connection_id": str(transaction["local_connection_id"]),
            "return_uri": transaction["return_uri"],
            "inventory": inventory,
        }
    except Exception:
        fail_device_transaction(str(transaction["id"]))
        raise


async def revoke_broker_connection(broker_connection_id: str) -> None:
    async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
        response = await client.post(f"{AUTH_BROKER_URL}/v1/connections/{broker_connection_id}/revoke")
        if response.status_code not in {200, 404}:
            response.raise_for_status()
