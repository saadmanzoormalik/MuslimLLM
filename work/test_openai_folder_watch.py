import asyncio
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from app.context_sync.jobs.queue import enqueue_job
from app.context_sync.openai_folder_watch import (
    _public_watch,
    _watch_folder_loop,
    find_export_candidate,
    recover_openai_folder_watches,
    revoke_folder_watch,
)
from app.context_sync.service import ensure_context_sync_ready
from app.db import get_conn
from work.context_sync_lab_fixture import conversation


class OpenAIFolderWatchTests(unittest.TestCase):
    def setUp(self):
        ensure_context_sync_ready()
        self.watch_ids: list[str] = []
        self.job_ids: list[str] = []

    def tearDown(self):
        with get_conn() as conn:
            for job_id in self.job_ids:
                conn.execute("delete from chats where import_job_id=%s", (job_id,))
                conn.execute("delete from projects where import_job_id=%s", (job_id,))
                row = conn.execute("select connection_id,inventory_json from sync_jobs where id=%s", (job_id,)).fetchone()
                connection_id = row["connection_id"] if row else None
                upload_token = (row["inventory_json"] or {}).get("upload_token") if row else None
                conn.execute("delete from sync_jobs where id=%s", (job_id,))
                if upload_token:
                    conn.execute("delete from context_sync_uploads where id=%s", (upload_token,))
                if connection_id:
                    conn.execute("delete from provider_connections where id=%s", (connection_id,))
            for watch_id in self.watch_ids:
                conn.execute("delete from openai_export_folder_watches where id=%s", (watch_id,))
                conn.execute("delete from sync_audit_log where details_json->>'watch_id'=%s", (watch_id,))

    def create_archive(self, folder: Path, source_id: str) -> Path:
        path = folder / f"chatgpt-export-{source_id}.zip"
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("conversations.json", json.dumps([conversation(source_id, "Backend watched export")]))
        return path

    def test_candidate_scan_is_non_recursive_and_deduplicated(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            nested = folder / "nested"
            nested.mkdir()
            self.create_archive(nested, "nested")
            expected = self.create_archive(folder, "direct")
            candidate = find_export_candidate(folder, set())
            self.assertIsNotNone(candidate)
            self.assertEqual(expected, candidate[0])
            self.assertIsNone(find_export_candidate(folder, {candidate[1]}))

    def test_public_status_hides_path_and_access_can_be_revoked(self):
        watch_id = str(uuid4())
        public = _public_watch({"id": watch_id, "folder_path": "/private/secret/Downloads", "folder_name": "Downloads", "status": "watching", "matched_file_name": None, "job_id": None})
        self.assertEqual("Downloads", public["folder_name"])
        self.assertNotIn("/private/secret", str(public))
        with get_conn() as conn:
            conn.execute(
                "insert into openai_export_folder_watches (id,folder_path,folder_name,status) values (%s,%s,%s,'watching')",
                (watch_id, "/private/secret/Downloads", "Downloads"),
            )
        self.watch_ids.append(watch_id)
        revoked = revoke_folder_watch(watch_id)
        self.assertEqual("revoked", revoked["status"])

    def test_backend_detects_export_and_creates_durable_job(self):
        marker = f"folder-watch-{uuid4().hex}"
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            self.create_archive(folder, marker)
            with get_conn() as conn:
                row = conn.execute(
                    "insert into openai_export_folder_watches (folder_path,folder_name,status) values (%s,%s,'watching') returning id",
                    (str(folder), folder.name),
                ).fetchone()
            watch_id = str(row["id"])
            self.watch_ids.append(watch_id)

            async def detect():
                with patch("app.context_sync.openai_folder_watch.enqueue_job"):
                    await _watch_folder_loop(watch_id)
                    await asyncio.sleep(0.05)

            asyncio.run(detect())
            with get_conn() as conn:
                watch = conn.execute("select status,job_id from openai_export_folder_watches where id=%s", (watch_id,)).fetchone()
            self.assertEqual("syncing", watch["status"])
            self.assertIsNotNone(watch["job_id"])
            job_id = str(watch["job_id"])
            self.job_ids.append(job_id)
            result = enqueue_job(job_id)
            self.assertIn(result["status"], {"completed", "completed_with_exceptions"})
            with get_conn() as conn:
                ready = conn.execute("select ready_for_use from sync_jobs where id=%s", (job_id,)).fetchone()["ready_for_use"]
            self.assertTrue(ready)

    def test_interrupted_validation_is_recovered_after_restart(self):
        watch_id = str(uuid4())
        with get_conn() as conn:
            conn.execute(
                """
                insert into openai_export_folder_watches
                  (id,folder_path,folder_name,status,last_archive_hash,seen_archive_hashes_json)
                values (%s,%s,%s,'validating','archive-a','[\"archive-a\"]'::jsonb)
                """,
                (watch_id, "/temporarily/unavailable", "Downloads"),
            )
        self.watch_ids.append(watch_id)
        with patch("app.context_sync.openai_folder_watch.start_folder_watch") as start:
            asyncio.run(recover_openai_folder_watches())
        with get_conn() as conn:
            row = conn.execute("select status,seen_archive_hashes_json from openai_export_folder_watches where id=%s", (watch_id,)).fetchone()
        self.assertEqual("watching", row["status"])
        self.assertEqual([], row["seen_archive_hashes_json"])
        start.assert_called_once_with(watch_id)


if __name__ == "__main__":
    unittest.main()
