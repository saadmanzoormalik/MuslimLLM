import hashlib
import json
from typing import Any


def content_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, default=str) if not isinstance(value, str) else value
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def source_identity(provider_id: str, source_account_hash: str | None, object_type: str, object_id: str | None, fallback: Any) -> str:
    stable = object_id or content_hash(fallback)
    return f"{provider_id}:{source_account_hash or 'local'}:{object_type}:{stable}"

