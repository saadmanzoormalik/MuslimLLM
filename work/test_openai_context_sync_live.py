import tempfile
import time
import unittest
from pathlib import Path
from uuid import uuid4

import httpx

from app.db import get_conn
from work.context_sync_lab_fixture import create_export


class OpenAIContextSyncLiveTests(unittest.TestCase):
    api_base = "http://127.0.0.1:8000"

    def test_live_export_upload_job_report_and_cleanup(self):
        marker = uuid4().hex
        job_id = None
        connection_id = None
        upload_token = None
        try:
            with tempfile.TemporaryDirectory() as directory:
                export_path = create_export(Path(directory) / f"chatgpt-{marker}.zip")
                with export_path.open("rb") as handle, httpx.Client(timeout=20) as client:
                    response = client.post(
                        f"{self.api_base}/context-sync/openai/select-export",
                        files={"file": (export_path.name, handle, "application/zip")},
                    )
                    self.assertEqual(200, response.status_code, response.text)
                    job_id = response.json()["job_id"]
                    deadline = time.monotonic() + 20
                    while time.monotonic() < deadline:
                        status = client.get(f"{self.api_base}/context-sync/status/{job_id}")
                        self.assertEqual(200, status.status_code, status.text)
                        if status.json()["status"] in {"completed", "completed_with_exceptions"}:
                            break
                        time.sleep(0.15)
                    else:
                        self.fail("Live import did not complete")
                    report = client.get(f"{self.api_base}/context-sync/jobs/{job_id}/report")
                    self.assertEqual(200, report.status_code, report.text)
                    self.assertEqual(1, report.json()["conversations_detected"])
                    self.assertGreaterEqual(report.json()["branches_preserved"], 1)
                    destination = client.post(f"{self.api_base}/context-sync/jobs/{job_id}/open-most-recent", json={})
                    self.assertEqual(200, destination.status_code, destination.text)
                    self.assertIn("?chat=", destination.json()["url"])
            with get_conn() as conn:
                row = conn.execute("select connection_id,inventory_json from sync_jobs where id=%s", (job_id,)).fetchone()
                connection_id = str(row["connection_id"]) if row and row["connection_id"] else None
                upload_token = str((row["inventory_json"] or {}).get("upload_token") or "") if row else None
        finally:
            if job_id:
                with get_conn() as conn:
                    conn.execute("delete from chats where import_job_id=%s", (job_id,))
                    conn.execute("delete from projects where import_job_id=%s", (job_id,))
                    conn.execute("delete from sync_jobs where id=%s", (job_id,))
                    if upload_token:
                        conn.execute("delete from context_sync_uploads where id=%s", (upload_token,))
                    if connection_id:
                        conn.execute("delete from provider_connections where id=%s", (connection_id,))


if __name__ == "__main__":
    unittest.main()
