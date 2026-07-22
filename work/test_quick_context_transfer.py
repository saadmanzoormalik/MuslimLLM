#!/usr/bin/env python3
import os
import sys
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.db import get_conn
from work.context_sync_lab_fixture import create_export


BASE = os.getenv("MUSLIM_LLM_API", "http://127.0.0.1:8000")


def cleanup(job_id: str) -> None:
    with get_conn() as conn:
        job = conn.execute("select connection_id from sync_jobs where id=%s", (job_id,)).fetchone()
        connection_id = job["connection_id"] if job else None
        conn.execute("delete from continuity_packages where job_id=%s", (job_id,))
        conn.execute("delete from normalized_context_items where job_id=%s", (job_id,))
        conn.execute("delete from chats where import_job_id=%s", (job_id,))
        conn.execute("delete from projects where import_job_id=%s", (job_id,))
        conn.execute("delete from sync_jobs where id=%s", (job_id,))
        if connection_id:
            conn.execute("delete from context_sync_uploads where connection_id=%s", (connection_id,))
            conn.execute("delete from provider_connections where id=%s", (connection_id,))


def main() -> None:
    job_id = ""
    with tempfile.TemporaryDirectory() as directory:
        export = create_export(Path(directory) / f"quick-transfer-{time.time_ns()}.zip", numbered=False)
        try:
            with export.open("rb") as handle:
                response = httpx.post(
                    f"{BASE}/context-sync/official-export/chatgpt",
                    files={"file": (export.name, handle, "application/zip")},
                    timeout=30,
                )
            response.raise_for_status()
            job_id = response.json()["job_id"]
            for _ in range(120):
                status = httpx.get(f"{BASE}/context-sync/status/{job_id}", timeout=10)
                status.raise_for_status()
                job = status.json()
                if job["status"] in {"completed", "completed_with_exceptions", "failed_recoverable"}:
                    break
                time.sleep(0.25)
            assert job["status"] in {"completed", "completed_with_exceptions"}, job
            with get_conn() as conn:
                counts = conn.execute(
                    """
                    select
                      (select count(*) from chats where import_job_id=%s) as chats,
                      (select count(*) from messages where chat_id in (select id from chats where import_job_id=%s)) as messages,
                      (select count(*) from sync_validation_reports where job_id=%s) as validations,
                      (select count(*) from continuity_packages where job_id=%s) as continuity_packages
                    """,
                    (job_id, job_id, job_id, job_id),
                ).fetchone()
            assert counts["chats"] == 1, counts
            assert counts["messages"] >= 2, counts
            assert counts["validations"] == 1, counts
            assert counts["continuity_packages"] == 1, counts
            print({"job_id": job_id, "status": job["status"], **counts})
        finally:
            if job_id:
                cleanup(job_id)


if __name__ == "__main__":
    main()
