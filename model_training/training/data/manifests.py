import hashlib
import json
from pathlib import Path


def immutable_manifest(path):
    path = Path(path)
    payload = json.loads(path.read_text())
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return {"path": str(path), "sha256": hashlib.sha256(canonical).hexdigest(), "dataset_version": payload.get("dataset_version"), "record_count": payload.get("record_count", 0)}

