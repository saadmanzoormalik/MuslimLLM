import hashlib
import json
import os
import secrets
import time
from dataclasses import dataclass
from urllib.parse import urlencode, urljoin, urlparse

import httpx
from joserfc import jwt
from joserfc.jwk import KeySet

from ...db import get_conn
from ...imports.normalizer import normalize_json_payload
from ..schemas import ContextInventory
from .oauth import new_state, pkce_pair
from .state_store import pop_state, put_state
from .token_vault import decrypt_token, encrypt_token


@dataclass(frozen=True)
class OAuthProviderConfig:
    provider_id: str
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    api_base: str
    history_path: str
    scopes: tuple[str, ...]
    issuer: str = ""
    jwks_url: str = ""
    userinfo_url: str = ""
    revocation_url: str = ""
    token_auth_method: str = "client_secret_post"
    cursor_param: str = "cursor"
    next_cursor_field: str = "next_cursor"
    verified_history: bool = False

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.authorize_url and self.token_url and self.api_base and self.history_path)

    @property
    def available(self) -> bool:
        return self.configured and self.verified_history


def provider_oauth_config(provider_id: str) -> OAuthProviderConfig:
    prefix = f"CONTEXT_SYNC_{provider_id.upper()}_"
    scopes = tuple(filter(None, os.getenv(prefix + "SCOPES", "openid profile email").replace(",", " ").split()))
    return OAuthProviderConfig(
        provider_id=provider_id,
        client_id=os.getenv(prefix + "CLIENT_ID", ""),
        client_secret=os.getenv(prefix + "CLIENT_SECRET", ""),
        authorize_url=os.getenv(prefix + "AUTHORIZE_URL", ""),
        token_url=os.getenv(prefix + "TOKEN_URL", ""),
        api_base=os.getenv(prefix + "API_BASE", ""),
        history_path=os.getenv(prefix + "HISTORY_PATH", ""),
        scopes=scopes,
        issuer=os.getenv(prefix + "ISSUER", ""),
        jwks_url=os.getenv(prefix + "JWKS_URL", ""),
        userinfo_url=os.getenv(prefix + "USERINFO_URL", ""),
        revocation_url=os.getenv(prefix + "REVOCATION_URL", ""),
        token_auth_method=os.getenv(prefix + "TOKEN_AUTH_METHOD", "client_secret_post"),
        cursor_param=os.getenv(prefix + "CURSOR_PARAM", "cursor"),
        next_cursor_field=os.getenv(prefix + "NEXT_CURSOR_FIELD", "next_cursor"),
        verified_history=os.getenv(prefix + "VERIFIED_HISTORY", "false").lower() == "true",
    )


def _callback_uri(provider_id: str) -> str:
    base = os.getenv("CONTEXT_SYNC_CALLBACK_BASE", "http://127.0.0.1:8000").rstrip("/")
    return f"{base}/context-sync/callback/{provider_id}"


def _safe_return_uri(return_uri: str) -> str:
    allowed = {
        origin.strip().rstrip("/")
        for origin in os.getenv(
            "CONTEXT_SYNC_ALLOWED_RETURN_ORIGINS",
            "http://127.0.0.1:3000,http://localhost:3000",
        ).split(",")
        if origin.strip()
    }
    parsed = urlparse(return_uri)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if origin not in allowed:
        raise ValueError("Return address is not allowed.")
    return return_uri


def begin_oauth_connection(provider_id: str, connection_id: str, return_uri: str) -> dict:
    config = provider_oauth_config(provider_id)
    if not config.available:
        return {
            "provider_id": provider_id,
            "connection_id": "",
            "next_action": "unavailable",
            "user_message": f"Secure sign-in for {provider_id} is not available yet.",
        }

    verifier, challenge = pkce_pair()
    state = new_state()
    nonce = secrets.token_urlsafe(32)
    redirect_uri = _callback_uri(provider_id)
    put_state(connection_id, state, verifier, nonce, redirect_uri, _safe_return_uri(return_uri))
    query = urlencode(
        {
            "response_type": "code",
            "client_id": config.client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(config.scopes),
            "state": state,
            "nonce": nonce,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )
    return {
        "provider_id": provider_id,
        "connection_id": connection_id,
        "next_action": "redirect",
        "authorization_url": f"{config.authorize_url}{'&' if '?' in config.authorize_url else '?'}{query}",
    }


async def _validate_id_token(config: OAuthProviderConfig, id_token: str, nonce: str) -> dict:
    if not id_token:
        return {}
    if not config.issuer or not config.jwks_url:
        raise ValueError("OIDC issuer verification is not configured.")
    async with httpx.AsyncClient(timeout=15) as client:
        jwks_response = await client.get(config.jwks_url)
        jwks_response.raise_for_status()
    token = jwt.decode(id_token, KeySet.import_key_set(jwks_response.json()), algorithms=["RS256", "ES256"])
    claims = dict(token.claims)
    audience = claims.get("aud")
    audiences = audience if isinstance(audience, list) else [audience]
    now = int(time.time())
    if claims.get("iss") != config.issuer:
        raise ValueError("OIDC issuer did not match.")
    if config.client_id not in audiences:
        raise ValueError("OIDC audience did not match.")
    if not secrets.compare_digest(str(claims.get("nonce") or ""), nonce):
        raise ValueError("OIDC nonce did not match.")
    if int(claims.get("exp") or 0) < now - 60:
        raise ValueError("OIDC token expired.")
    if int(claims.get("nbf") or 0) > now + 60:
        raise ValueError("OIDC token is not active.")
    return claims


async def complete_oauth_connection(provider_id: str, code: str, state: str) -> dict:
    stored = pop_state(state)
    if stored["provider_id"] != provider_id:
        raise ValueError("Provider authorization did not match the request.")
    config = provider_oauth_config(provider_id)
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": stored["redirect_uri"],
        "client_id": config.client_id,
        "code_verifier": stored["code_verifier"],
    }
    auth = None
    if config.token_auth_method == "client_secret_basic" and config.client_secret:
        auth = httpx.BasicAuth(config.client_id, config.client_secret)
    elif config.client_secret:
        data["client_secret"] = config.client_secret

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(config.token_url, data=data, auth=auth, headers={"Accept": "application/json"})
        response.raise_for_status()
        token = response.json()
    if not token.get("access_token"):
        raise ValueError("Provider did not return an access token.")

    claims = await _validate_id_token(config, token.get("id_token", ""), stored["nonce"])
    account_id = str(claims.get("sub") or claims.get("email") or "")
    account_hash = hashlib.sha256(account_id.encode()).hexdigest() if account_id else None
    with get_conn() as conn:
        conn.execute(
            """
            update provider_connections
            set status='connected',auth_method='oauth_pkce',source_account_hash=%s,
                scopes_json=%s::jsonb,encrypted_token_json=%s::jsonb,
                encrypted_oauth_state_json='{}'::jsonb,updated_at=now()
            where id=%s
            """,
            (
                account_hash,
                json.dumps(token.get("scope", " ".join(config.scopes)).split()),
                json.dumps(encrypt_token(token)),
                stored["connection_id"],
            ),
        )
    return {**stored, "account_hash": account_hash}


async def fetch_oauth_context(provider_id: str, connection_id: str) -> ContextInventory:
    config = provider_oauth_config(provider_id)
    with get_conn() as conn:
        row = conn.execute("select encrypted_token_json from provider_connections where id=%s and status='connected'", (connection_id,)).fetchone()
    token = decrypt_token((row or {}).get("encrypted_token_json") or {})
    if not token.get("access_token"):
        raise ValueError("Reconnect required.")

    merged = {"provider": provider_id, "conversations": [], "projects": [], "files": [], "preferences": []}
    cursor = None
    max_pages = max(1, min(int(os.getenv("CONTEXT_SYNC_MAX_OAUTH_PAGES", "100")), 500))
    headers = {"Authorization": f"Bearer {token['access_token']}", "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=30) as client:
        for _ in range(max_pages):
            params = {config.cursor_param: cursor} if cursor else {}
            response = await client.get(urljoin(config.api_base.rstrip("/") + "/", config.history_path.lstrip("/")), headers=headers, params=params)
            response.raise_for_status()
            payload = response.json()
            normalized = normalize_json_payload(payload, provider_id, source_name="official_oauth_history")
            for key in ["conversations", "projects", "files", "preferences"]:
                merged[key].extend(normalized.get(key, []))
            cursor = payload.get(config.next_cursor_field) if isinstance(payload, dict) else None
            if not cursor:
                break

    return ContextInventory(
        provider_id=provider_id,
        conversations_found=len(merged["conversations"]),
        projects_found=len(merged["projects"]),
        files_found=len(merged["files"]),
        estimated_seconds=max(5, len(merged["conversations"])),
        normalized=merged,
    )


async def revoke_oauth_connection(connection_id: str) -> None:
    with get_conn() as conn:
        row = conn.execute("select provider_id,encrypted_token_json from provider_connections where id=%s", (connection_id,)).fetchone()
    if not row:
        return
    config = provider_oauth_config(row["provider_id"])
    token = decrypt_token(row["encrypted_token_json"] or {})
    if config.revocation_url and token.get("access_token"):
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                await client.post(config.revocation_url, data={"token": token["access_token"], "client_id": config.client_id})
            except httpx.HTTPError:
                pass
