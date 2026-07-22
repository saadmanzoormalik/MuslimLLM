#!/usr/bin/env python3
import sys
import tempfile
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from work.context_sync_lab_fixture import create_export
from backend.app.db import get_conn

BASE = "http://127.0.0.1:8000"


def main():
    with tempfile.TemporaryDirectory() as directory:
        path = create_export(Path(directory) / f"promotion-{time.time_ns()}.zip")
        with path.open("rb") as handle:
            result = httpx.post(f"{BASE}/context-sync-lab/openai/select-export", files={"file": (path.name, handle, "application/zip")}, timeout=30).json()
        job_id = result["job_id"]
        for _ in range(80):
            job = httpx.get(f"{BASE}/context-sync-lab/jobs/{job_id}").json()
            if job["status"].startswith("completed") or job["status"] == "failed":
                break
            time.sleep(0.25)
        first = httpx.post(f"{BASE}/context-sync-lab/jobs/{job_id}/promote", json={}, timeout=30)
        first.raise_for_status()
        second = httpx.post(f"{BASE}/context-sync-lab/jobs/{job_id}/promote", json={}, timeout=30)
        second.raise_for_status()
        assert first.json()["transactional"] is True
        assert second.json()["duplicate_prevented"] is True
        assert second.json()["promoted_chats"] == first.json()["promoted_chats"]
        print({"first": first.json(), "retry": second.json()})
        with get_conn() as conn:
            source = conn.execute("select source_hash from context_sync_lab.lab_jobs where id=%s", (job_id,)).fetchone()
            conn.execute("delete from continuity_packages where local_chat_id in (select id from chats where import_job_id=%s)", (job_id,))
            if source:
                conn.execute("delete from normalized_context_items where provider_id='openai' and source_account_id_hash=%s", (source["source_hash"],))
            conn.execute("delete from chats where import_job_id=%s", (job_id,))
            conn.execute("delete from projects where import_job_id=%s", (job_id,))
            conn.execute("delete from context_sync_lab.lab_jobs where id=%s", (job_id,))


if __name__ == "__main__":
    main()
