from __future__ import annotations

import hashlib
import json
import os
import random
from pathlib import Path

import torch


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save_checkpoint(path, model, optimizer, *, step: int, metadata: dict, data_cursor: int = 0):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    payload = {"model": model.state_dict(), "optimizer": optimizer.state_dict(), "step": step, "metadata": metadata, "data_cursor": data_cursor, "torch_rng": torch.get_rng_state(), "python_rng": random.getstate()}
    torch.save(payload, temporary)
    os.replace(temporary, path)
    signature = {"sha256": _sha256(path), "step": step, "metadata": metadata}
    path.with_suffix(path.suffix + ".sha256.json").write_text(json.dumps(signature, indent=2) + "\n")
    return signature


def load_checkpoint(path, model, optimizer, *, expected_metadata: dict):
    path = Path(path)
    signature = json.loads(path.with_suffix(path.suffix + ".sha256.json").read_text())
    if signature["sha256"] != _sha256(path):
        raise ValueError("Checkpoint hash mismatch")
    payload = torch.load(path, map_location="cpu")
    for key, expected in expected_metadata.items():
        if payload["metadata"].get(key) != expected:
            raise ValueError(f"Checkpoint metadata mismatch: {key}")
    model.load_state_dict(payload["model"])
    optimizer.load_state_dict(payload["optimizer"])
    torch.set_rng_state(payload["torch_rng"])
    random.setstate(payload["python_rng"])
    return payload

