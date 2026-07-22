import os
import re
from pathlib import Path


def enabled() -> bool:
    return os.getenv("ENABLE_CONTEXT_SYNC_LAB", "false").lower() in {"1", "true", "yes", "on"}


def schema_name() -> str:
    value = os.getenv("CONTEXT_SYNC_LAB_DATABASE_SCHEMA", "context_sync_lab")
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", value):
        raise ValueError("Invalid Context Sync Lab database schema name")
    return value


def storage_path() -> Path:
    value = os.getenv("CONTEXT_SYNC_LAB_STORAGE_PATH")
    path = Path(value).expanduser() if value else Path(__file__).resolve().parents[2] / ".context-sync-lab"
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path
