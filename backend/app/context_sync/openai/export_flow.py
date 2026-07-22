from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from typing import Any, Literal

from ...db import get_conn
from ..openai_folder_watch import latest_folder_watch
from ..state_machine import create_transfer_session, get_transfer_session, transition_session

OFFICIAL_OPENAI_EXPORT_GUIDE = "https://help.openai.com/en/articles/7260999-how-do-i-export-my-data"

TransferMethod = Literal[
    "official_history_api",
    "official_export_api",
    "official_export_email",
    "official_export_folder_watch",
    "official_export_file_picker",
    "unavailable",
]


@dataclass(frozen=True)
class OpenAIConnection:
    id: str | None = None
    status: str = "disconnected"
    auth_method: str | None = None
    granted_capabilities: tuple[str, ...] = ()


@dataclass
class ExportFlowSession:
    session_id: str
    consent_id: str
    state: str
    action_url: str = OFFICIAL_OPENAI_EXPORT_GUIDE


@dataclass
class AcquisitionMethod:
    method: str
    next_action: str
    permission_required: bool = False


def _enabled(key: str) -> bool:
    return os.getenv(key, "false").strip().lower() == "true"


def _configured_implementation(module_env: str, callable_name: str) -> bool:
    """A capability flag is insufficient: an importable implementation must exist."""
    module_name = os.getenv(module_env, "").strip()
    if not module_name:
        return False
    try:
        module = importlib.import_module(module_name)
    except (ImportError, ValueError):
        return False
    return callable(getattr(module, callable_name, None))


def _connection_value(connection: OpenAIConnection | dict[str, Any] | None, key: str, default: Any = None) -> Any:
    if connection is None:
        return default
    if isinstance(connection, dict):
        return connection.get(key, default)
    return getattr(connection, key, default)


def official_history_api_is_documented_configured_and_tested(
    connection: OpenAIConnection | dict[str, Any] | None = None,
) -> bool:
    required = (
        "CONTEXT_SYNC_OPENAI_HISTORY_API_DOCUMENTED",
        "CONTEXT_SYNC_OPENAI_HISTORY_SCOPES_DOCUMENTED",
        "CONTEXT_SYNC_OPENAI_HISTORY_CONTRACT_VERIFIED",
        "CONTEXT_SYNC_OPENAI_HISTORY_PROJECT_FILES_TESTED",
        "CONTEXT_SYNC_OPENAI_HISTORY_API_ENABLED",
    )
    capabilities = set(_connection_value(connection, "granted_capabilities", ()) or ())
    return (
        all(_enabled(key) for key in required)
        and _connection_value(connection, "status") == "connected"
        and "chat_history_access" in capabilities
        and _configured_implementation("CONTEXT_SYNC_OPENAI_HISTORY_IMPLEMENTATION_MODULE", "fetch_chat_history")
    )


def official_export_api_is_documented_configured_and_tested(
    connection: OpenAIConnection | dict[str, Any] | None = None,
) -> bool:
    required = (
        "CONTEXT_SYNC_OPENAI_EXPORT_API_DOCUMENTED",
        "CONTEXT_SYNC_OPENAI_EXPORT_API_CREDENTIALS_VALID",
        "CONTEXT_SYNC_OPENAI_EXPORT_API_CONTRACT_VERIFIED",
        "CONTEXT_SYNC_OPENAI_EXPORT_API_PROJECT_FILES_TESTED",
        "CONTEXT_SYNC_OPENAI_EXPORT_API_ENABLED",
    )
    capabilities = set(_connection_value(connection, "granted_capabilities", ()) or ())
    return (
        all(_enabled(key) for key in required)
        and _connection_value(connection, "status") == "connected"
        and "official_export_access" in capabilities
        and _configured_implementation("CONTEXT_SYNC_OPENAI_EXPORT_IMPLEMENTATION_MODULE", "acquire_official_export")
    )


def valid_user_authorized_export_email_connection_exists() -> bool:
    if not (
        _enabled("CONTEXT_SYNC_OPENAI_EMAIL_DETECTION_ENABLED")
        and _enabled("CONTEXT_SYNC_OPENAI_EMAIL_CONTRACT_VERIFIED")
        and _configured_implementation("CONTEXT_SYNC_OPENAI_EMAIL_IMPLEMENTATION_MODULE", "watch_for_openai_export")
    ):
        return False
    with get_conn() as conn:
        row = conn.execute(
            """
            select 1 from context_transfer_permissions
            where provider='chatgpt' and permission_type='export_email' and status='active'
              and revoked_at is null and (expires_at is null or expires_at > now())
            limit 1
            """
        ).fetchone()
    return bool(row)


def valid_user_authorized_folder_permission_exists(platform: str) -> bool:
    if platform not in {"darwin", "macos", "mac"}:
        return False
    watch = latest_folder_watch()
    if not watch or watch.get("status") not in {"watching", "validating", "syncing"}:
        return False
    with get_conn() as conn:
        permission = conn.execute(
            """
            select 1 from context_transfer_permissions
            where provider='chatgpt' and permission_type='selected_folder' and status='active'
              and grant_reference_id=%s and revoked_at is null
              and (expires_at is null or expires_at > now())
            limit 1
            """,
            (watch["id"],),
        ).fetchone()
    return bool(permission)


async def resolve_real_openai_transfer_method(
    connection: OpenAIConnection | dict[str, Any] | None,
    platform: str,
) -> TransferMethod:
    """Select only a real, configured, contract-tested ChatGPT transfer path."""
    if official_history_api_is_documented_configured_and_tested(connection):
        return "official_history_api"
    if official_export_api_is_documented_configured_and_tested(connection):
        return "official_export_api"
    if valid_user_authorized_export_email_connection_exists():
        return "official_export_email"
    if valid_user_authorized_folder_permission_exists(platform):
        return "official_export_folder_watch"
    return "official_export_file_picker"


async def begin_openai_export_flow(consent_id: str, device_id: str) -> ExportFlowSession:
    session = create_transfer_session(consent_id, device_id)
    session_id = str(session["id"])
    transition_session(session_id, "opening_openai", event_type="official_export_opened", acquisition_method="official_user_export")
    return ExportFlowSession(session_id=session_id, consent_id=consent_id, state="opening_openai")


async def resolve_best_acquisition_method(session: ExportFlowSession, connection: OpenAIConnection | dict[str, Any] | None = None) -> AcquisitionMethod:
    method = await resolve_real_openai_transfer_method(connection, os.sys.platform)
    if method == "official_history_api":
        transition_session(session.session_id, "waiting_for_export", acquisition_method=method)
        return AcquisitionMethod(method, "sync")

    if method == "official_export_api":
        transition_session(session.session_id, "waiting_for_export", acquisition_method="official_export_api")
        return AcquisitionMethod("official_export_api", "sync")

    if method == "official_export_email":
        transition_session(session.session_id, "watching_email", acquisition_method=method)
        return AcquisitionMethod(method, "sync")

    if method == "official_export_folder_watch":
        watch = latest_folder_watch()
        if watch:
            transition_session(session.session_id, "watching_folder", acquisition_method=method, folder_watch_id=watch["id"])
            return AcquisitionMethod(method, "sync")

    if method == "official_export_file_picker":
        transition_session(session.session_id, "awaiting_file_selection", acquisition_method=method)
        return AcquisitionMethod(method, "open_official_export")

    transition_session(session.session_id, "failed_recoverable", acquisition_method="unavailable", last_error_code="no_real_transfer_method")
    return AcquisitionMethod("unavailable", "unavailable")


async def resume_export_flow(session_id: str) -> ExportFlowSession:
    session = get_transfer_session(session_id)
    return ExportFlowSession(session_id=session_id, consent_id="", state=session["state"])
