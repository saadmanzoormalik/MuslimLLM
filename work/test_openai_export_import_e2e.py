#!/usr/bin/env python3
import sys
import tempfile
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from work.context_sync_lab_fixture import create_export

BASE = "http://127.0.0.1:8000"


def main():
    with tempfile.TemporaryDirectory() as directory:
        path = create_export(Path(directory) / "chatgpt-export.zip", numbered=True)
        with path.open("rb") as handle:
            response = httpx.post(f"{BASE}/context-sync-lab/openai/select-export", files={"file": (path.name, handle, "application/zip")}, timeout=30)
        response.raise_for_status()
        job_id = response.json()["job_id"]
        for _ in range(80):
            job = httpx.get(f"{BASE}/context-sync-lab/jobs/{job_id}", timeout=10).json()
            if job["status"] in {"completed", "completed_with_exceptions", "failed"}:
                break
            time.sleep(0.25)
        assert job["status"] in {"completed", "completed_with_exceptions"}, job
        preview = httpx.get(f"{BASE}/context-sync-lab/jobs/{job_id}/preview").json()
        report = httpx.get(f"{BASE}/context-sync-lab/jobs/{job_id}/validation").json()
        assert len(preview["conversations"]) == 1
        assert preview["conversations"][0]["branch_count"] == 1
        assert report["report_json"]["gates"]["all_imported_system_instructions_untrusted"] is True
        print({"job_id": job_id, "status": job["status"], "validation": report["status"], "score": float(report["score"])})


if __name__ == "__main__":
    main()
