import json
import os
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from ..db import get_conn
from .audit import audit
from .email_codes import development_code, issue, normalize_email, verify
from .onboarding import answer as save_answer
from .onboarding import attach_hash, complete as complete_onboarding
from .onboarding import get_or_create, profile
from .providers import PROVIDERS
from .schemas import DeleteAccount, EmailStart, EmailVerify, GuestCreate, OAuthStart, OnboardingAnswer
from .security import ONBOARDING_COOKIE, Principal, decrypt_short_lived, encrypt_short_lived, opaque_token, token_hash
from .service import create_guest, finish_user_auth, public_principal, user_for_identity
from .sessions import create_session, optional_principal, require_principal, revoke_all, revoke_current, rotate_session
from .tokens import apple_client_secret


router = APIRouter(tags=["authentication"])
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:3000")


def _auth_error(message: str, status: int = 400) -> HTTPException:
    return HTTPException(status_code=status, detail=message)


def _provider_configured(name: str) -> bool:
    provider = PROVIDERS[name]
    common = bool(os.getenv(provider.client_id_env) and os.getenv(provider.redirect_uri_env))
    if name == "google":
        return common and bool(os.getenv(provider.client_secret_env or ""))
    return common and all(os.getenv(key) for key in ("APPLE_TEAM_ID", "APPLE_KEY_ID", "APPLE_PRIVATE_KEY_PATH"))


@router.get("/auth/providers")
def providers():
    email_provider = os.getenv("AUTH_EMAIL_PROVIDER", "local").lower()
    email_configured = email_provider == "local" and os.getenv("ENVIRONMENT", "development") != "production"
    return {
        name: {
            "enabled": os.getenv(f"AUTH_ALLOW_{name.upper()}", "true").lower() == "true",
            "configured": _provider_configured(name),
        }
        for name, provider in PROVIDERS.items()
    } | {
        "email": {"enabled": os.getenv("AUTH_ALLOW_EMAIL", "true").lower() == "true", "configured": email_configured},
        "guest": {"enabled": os.getenv("AUTH_ALLOW_GUEST", "true").lower() == "true", "configured": True},
    }


@router.get("/onboarding")
def onboarding_state(request: Request, response: Response, principal: Principal | None = Depends(optional_principal)):
    if principal:
        current = profile(principal)
        return {"authenticated": True, "completed": bool(current and current["completed"]), "profile": current}
    row = get_or_create(request, response)
    return {"authenticated": False, "completed": row["completed"], "current_step": row["current_step"], "answers": row["answers_json"]}


@router.post("/onboarding/answer")
def onboarding_answer(payload: OnboardingAnswer, request: Request, response: Response):
    try:
        row = save_answer(request, response, payload.key, payload.value, payload.step)
    except ValueError as exc:
        raise _auth_error(str(exc)) from exc
    return {"current_step": row["current_step"], "answers": row["answers_json"]}


@router.post("/onboarding/complete")
def onboarding_complete(request: Request, response: Response):
    try:
        row = complete_onboarding(request, response)
    except ValueError as exc:
        raise _auth_error(str(exc)) from exc
    return {"completed": True, "answers": row["answers_json"]}


@router.post("/auth/email/start")
def email_start(payload: EmailStart, request: Request):
    if os.getenv("AUTH_ALLOW_EMAIL", "true").lower() != "true":
        raise _auth_error("Email sign-in is not configured", 503)
    issue(request, str(payload.email))
    audit(request, "email_code_requested", True, "email")
    return {"ok": True, "message": "If the address can receive mail, a code is on its way"}


@router.post("/auth/email/resend")
def email_resend(payload: EmailStart, request: Request):
    if os.getenv("AUTH_ALLOW_EMAIL", "true").lower() != "true":
        raise _auth_error("Email sign-in is not configured", 503)
    issue(request, str(payload.email))
    return {"ok": True, "message": "A new code is on its way"}


@router.post("/auth/email/verify")
def email_verify(payload: EmailVerify, request: Request, response: Response):
    try:
        email = verify(request, str(payload.email), payload.code)
        user_id = user_for_identity("email", email, email, True)
        principal = finish_user_auth(request, response, user_id, optional_principal(request))
        audit(request, "sign_in", True, "email", principal=principal)
        return public_principal(principal)
    except HTTPException:
        audit(request, "sign_in", False, "email", "verification_failed")
        raise


@router.get("/auth/dev/mailbox")
def dev_mailbox(email: str):
    code = development_code(email)
    if not code:
        raise HTTPException(status_code=404, detail="Development mailbox is unavailable")
    return {"email": normalize_email(email), "code": code}


@router.post("/auth/guest")
def guest(payload: GuestCreate, request: Request, response: Response):
    if os.getenv("AUTH_ALLOW_GUEST", "true").lower() != "true":
        raise _auth_error("Guest access is unavailable", 403)
    existing = optional_principal(request)
    if existing:
        return public_principal(existing)
    principal = create_guest(request, response, payload.claim_existing_workspace)
    audit(request, "guest_created", True, "guest", principal=principal)
    return public_principal(principal)


@router.post("/auth/guest/convert")
def guest_convert(payload: EmailVerify, request: Request, response: Response, principal: Principal = Depends(require_principal)):
    if principal.kind != "guest":
        raise _auth_error("This workspace is already connected to an account")
    email = verify(request, str(payload.email), payload.code)
    user_id = user_for_identity("email", email, email, True)
    converted = finish_user_auth(request, response, user_id, principal)
    return public_principal(converted)


def _safe_return(value: str) -> str:
    return value if value.startswith("/") and not value.startswith("//") else "/"


def _start_oauth(provider_name: str, payload: OAuthStart, request: Request, linking_user_id: str | None = None):
    provider = PROVIDERS.get(provider_name)
    if not provider:
        raise HTTPException(status_code=404, detail="Sign-in provider not found")
    client_id = os.getenv(provider.client_id_env, "")
    redirect_uri = os.getenv(provider.redirect_uri_env, "")
    if not _provider_configured(provider_name):
        raise HTTPException(status_code=503, detail=f"{provider_name.title()} sign-in is not configured yet")
    state, nonce, verifier = opaque_token(32), opaque_token(32), opaque_token(48)
    from .providers.base import pkce_pair
    _, challenge = pkce_pair(verifier)
    onboarding_raw = request.cookies.get(ONBOARDING_COOKIE)
    current = optional_principal(request)
    with get_conn() as conn:
        conn.execute(
            """insert into auth_transactions
               (provider,state_hash,nonce_hash,nonce_ciphertext,pkce_verifier_ciphertext,onboarding_token_hash,guest_id,linking_user_id,return_to,expires_at)
               values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (provider_name, token_hash(state), token_hash(nonce), encrypt_short_lived(nonce), encrypt_short_lived(verifier),
             token_hash(onboarding_raw) if onboarding_raw else None,
             current.subject_id if current and current.kind == "guest" else None,
             linking_user_id,
             _safe_return(payload.return_to), datetime.now(UTC) + timedelta(minutes=10)),
        )
    return {"authorization_url": provider.authorization_url(client_id, redirect_uri, state, nonce, challenge)}


@router.post("/auth/{provider_name}/start")
def oauth_start(provider_name: str, payload: OAuthStart, request: Request):
    if os.getenv(f"AUTH_ALLOW_{provider_name.upper()}", "false").lower() != "true":
        raise _auth_error(f"{provider_name.title()} sign-in is not configured", 503)
    return _start_oauth(provider_name, payload, request)


async def _finish_oauth(provider_name: str, code: str | None, state: str | None, request: Request, user_payload: str | None = None):
    if not code or not state:
        return RedirectResponse(f"{FRONTEND_URL}/auth/callback?error=cancelled", status_code=303)
    provider = PROVIDERS[provider_name]
    with get_conn() as conn:
        transaction = conn.execute(
            """update auth_transactions set consumed_at=now()
               where provider=%s and state_hash=%s and consumed_at is null and expires_at>now() returning *""",
            (provider_name, token_hash(state)),
        ).fetchone()
    if not transaction:
        return RedirectResponse(f"{FRONTEND_URL}/auth/callback?error=expired", status_code=303)
    try:
        client_id = os.getenv(provider.client_id_env, "")
        redirect_uri = os.getenv(provider.redirect_uri_env, "")
        secret = apple_client_secret() if provider_name == "apple" else os.getenv(provider.client_secret_env or "", "")
        token_response = await provider.exchange(code, decrypt_short_lived(transaction["pkce_verifier_ciphertext"]), client_id, secret, redirect_uri)
        claims = await provider.verify(token_response["id_token"], client_id, decrypt_short_lived(transaction["nonce_ciphertext"]))
        name = claims.get("name")
        if provider_name == "apple" and user_payload:
            supplied = json.loads(user_payload).get("name", {})
            name = " ".join(filter(None, [supplied.get("firstName"), supplied.get("lastName")])) or name
        email = normalize_email(claims["email"]) if claims.get("email") else None
        verified = str(claims.get("email_verified", "false")).lower() == "true"
        if transaction["linking_user_id"]:
            with get_conn() as conn:
                existing = conn.execute(
                    "select user_id from auth_identities where provider=%s and provider_subject=%s for update",
                    (provider_name, str(claims["sub"])),
                ).fetchone()
                if existing and existing["user_id"] != transaction["linking_user_id"]:
                    raise ValueError("identity_in_use")
                if not existing:
                    conn.execute(
                        """insert into auth_identities
                           (user_id,provider,provider_subject,provider_email,provider_email_verified)
                           values (%s,%s,%s,%s,%s)""",
                        (transaction["linking_user_id"], provider_name, str(claims["sub"]), email, verified),
                    )
            user_id = str(transaction["linking_user_id"])
        else:
            user_id = user_for_identity(provider_name, str(claims["sub"]), email, verified, name, claims.get("picture"))
        response = RedirectResponse(f"{FRONTEND_URL}/auth/callback?return_to={transaction['return_to']}", status_code=303)
        current = optional_principal(request)
        if not current and transaction["guest_id"]:
            current = Principal("oauth-transaction", "guest", str(transaction["guest_id"]))
        principal = finish_user_auth(request, response, user_id, current)
        if transaction["onboarding_token_hash"]:
            with get_conn() as conn:
                attach_hash(conn, transaction["onboarding_token_hash"], principal)
        audit(request, "sign_in", True, provider_name, principal=principal)
        return response
    except (httpx.HTTPError, KeyError, ValueError, json.JSONDecodeError):
        audit(request, "sign_in", False, provider_name, "provider_callback_failed")
        return RedirectResponse(f"{FRONTEND_URL}/auth/callback?error=failed", status_code=303)


@router.get("/auth/google/callback")
async def google_callback(request: Request, code: str | None = None, state: str | None = None, error: str | None = None):
    return await _finish_oauth("google", None if error else code, state, request)


@router.post("/auth/apple/callback")
async def apple_callback(request: Request, code: str | None = Form(None), state: str | None = Form(None), user: str | None = Form(None), error: str | None = Form(None)):
    return await _finish_oauth("apple", None if error else code, state, request, user)


@router.post("/auth/refresh")
def refresh(request: Request, response: Response):
    principal = rotate_session(request, response)
    return public_principal(principal)


@router.post("/auth/logout")
def logout(response: Response, principal: Principal = Depends(require_principal)):
    revoke_current(principal, response)
    return {"ok": True}


@router.post("/auth/logout-all")
def logout_all(response: Response, principal: Principal = Depends(require_principal)):
    revoke_all(principal, response)
    return {"ok": True}


@router.get("/auth/me")
def me(principal: Principal = Depends(require_principal)):
    with get_conn() as conn:
        identities = [] if principal.kind == "guest" else conn.execute(
            "select provider,provider_email,provider_email_verified from auth_identities where user_id=%s order by created_at",
            (principal.subject_id,),
        ).fetchall()
        current_profile = conn.execute(
            f"select primary_use,response_preference,privacy_preference,context_transfer_preference,completed from onboarding_profiles where {principal.owner_column}=%s",
            (principal.subject_id,),
        ).fetchone()
    return public_principal(principal) | {"identities": identities, "onboarding": current_profile}


@router.get("/account/identities")
def identities(principal: Principal = Depends(require_principal)):
    if principal.kind == "guest":
        return []
    with get_conn() as conn:
        return conn.execute(
            "select provider,provider_email,provider_email_verified,created_at,last_used_at from auth_identities where user_id=%s order by created_at",
            (principal.subject_id,),
        ).fetchall()


@router.post("/account/link/{provider_name}")
def link_identity(provider_name: str, payload: dict, request: Request, principal: Principal = Depends(require_principal)):
    if principal.kind != "user":
        raise _auth_error("Connect an account before adding another sign-in method")
    if provider_name in PROVIDERS:
        return _start_oauth(provider_name, OAuthStart(return_to="/settings"), request, principal.subject_id)
    if provider_name != "email":
        raise HTTPException(status_code=404, detail="Sign-in provider not found")
    try:
        email = normalize_email(str(payload["email"]))
    except (KeyError, ValueError) as exc:
        raise _auth_error("Enter a valid email address") from exc
    code = str(payload.get("code", ""))
    if not code:
        issue(request, email, "link_identity")
        return {"ok": True, "verification_required": True}
    verify(request, email, code, "link_identity")
    with get_conn() as conn:
        occupied = conn.execute(
            "select user_id from auth_identities where provider='email' and provider_subject=%s for update", (email,)
        ).fetchone()
        if occupied and str(occupied["user_id"]) != principal.subject_id:
            raise HTTPException(status_code=409, detail="That email is already connected to another account")
        if not occupied:
            conn.execute(
                """insert into auth_identities
                   (user_id,provider,provider_subject,provider_email,provider_email_verified)
                   values (%s,'email',%s,%s,true)""",
                (principal.subject_id, email, email),
            )
    return {"ok": True, "connected": "email"}


@router.delete("/account/unlink/{provider}")
def unlink(provider: str, principal: Principal = Depends(require_principal)):
    if principal.kind != "user":
        raise _auth_error("Connect an account first")
    with get_conn() as conn:
        count = conn.execute("select count(*) count from auth_identities where user_id=%s", (principal.subject_id,)).fetchone()["count"]
        if count <= 1:
            raise _auth_error("Keep at least one sign-in method connected")
        deleted = conn.execute("delete from auth_identities where user_id=%s and provider=%s returning id", (principal.subject_id, provider)).fetchone()
    if not deleted:
        raise HTTPException(status_code=404, detail="That sign-in method is not connected")
    return {"ok": True}


@router.delete("/account")
def delete_account(payload: DeleteAccount, response: Response, principal: Principal = Depends(require_principal)):
    with get_conn() as conn:
        session = conn.execute("select authenticated_at from auth_sessions where id=%s", (principal.session_id,)).fetchone()
        if not session or session["authenticated_at"] < datetime.now(UTC) - timedelta(minutes=15):
            raise HTTPException(status_code=403, detail="Sign in again before deleting your account")
        conn.execute(f"delete from chats where {principal.owner_column}=%s", (principal.subject_id,))
        conn.execute(f"delete from projects where {principal.owner_column}=%s", (principal.subject_id,))
        if principal.kind == "user":
            conn.execute("delete from users where id=%s", (principal.subject_id,))
        else:
            conn.execute("delete from guest_accounts where id=%s", (principal.subject_id,))
    from .sessions import clear_session_cookies
    clear_session_cookies(response)
    return {"deleted": True}


@router.get("/auth/diagnostics")
def diagnostics():
    if os.getenv("ENVIRONMENT", "development") == "production" and os.getenv("AUTH_DIAGNOSTICS", "false").lower() != "true":
        raise HTTPException(status_code=404, detail="Not found")
    with get_conn() as conn:
        conn.execute("select 1").fetchone()
    configured = providers()
    return {
        "backend": "healthy", "database": "connected", "session_signing": bool(os.getenv("AUTH_SECRET_KEY")),
        "email_provider": os.getenv("AUTH_EMAIL_PROVIDER", "local"), "providers": configured,
        "secure_cookies": os.getenv("AUTH_SECURE_COOKIES", "false").lower() == "true",
        "callbacks": {name: os.getenv(item.redirect_uri_env, "not configured") for name, item in PROVIDERS.items()},
    }
