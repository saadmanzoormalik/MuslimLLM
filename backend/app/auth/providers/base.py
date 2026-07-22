import base64
import hashlib
import json
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from joserfc import jwk, jwt


def pkce_pair(verifier: str) -> tuple[str, str]:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


@dataclass(frozen=True)
class OIDCProvider:
    name: str
    issuer: str
    authorize_url: str
    token_url: str
    jwks_url: str
    client_id_env: str
    client_secret_env: str | None
    redirect_uri_env: str

    def authorization_url(self, client_id: str, redirect_uri: str, state: str, nonce: str, challenge: str) -> str:
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile" if self.name == "google" else "name email",
            "state": state,
            "nonce": nonce,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        if self.name == "apple":
            params["response_mode"] = "form_post"
        return f"{self.authorize_url}?{urlencode(params)}"

    async def exchange(self, code: str, verifier: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(self.token_url, data={
                "grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri,
                "client_id": client_id, "client_secret": client_secret, "code_verifier": verifier,
            })
            response.raise_for_status()
            return response.json()

    async def verify(self, raw_token: str, client_id: str, expected_nonce: str) -> dict:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(self.jwks_url)
            response.raise_for_status()
        keys = jwk.KeySet.import_key_set(response.json())
        decoded = jwt.decode(raw_token, keys, algorithms=["RS256"])
        claims = dict(decoded.claims)
        issuer = claims.get("iss")
        if issuer != self.issuer and not (self.name == "google" and issuer == "accounts.google.com"):
            raise ValueError("issuer")
        audience = claims.get("aud")
        if client_id not in ([audience] if isinstance(audience, str) else audience or []):
            raise ValueError("audience")
        if claims.get("nonce") != expected_nonce:
            raise ValueError("nonce")
        if int(claims.get("exp", 0)) <= int(time.time()):
            raise ValueError("expired")
        return claims
