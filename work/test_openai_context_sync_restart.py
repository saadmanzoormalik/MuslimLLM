import tempfile
import unittest
from pathlib import Path

from app.context_sync.jobs.checkpoints import save_checkpoint
from app.context_sync.jobs.orchestrator import run_sync_job
from app.context_sync.jobs.progressive_import import _import_conversation
from app.db import get_conn
from work.openai_context_sync_test_support import cleanup_import, make_export, prepare_import


class OpenAIContextSyncRestartTests(unittest.TestCase):
    def test_idempotent_recovery_resumes_without_duplicate_chats(self):
        with tempfile.TemporaryDirectory() as directory:
            path, _ = make_export(Path(directory) / "chatgpt-export.zip", conversation_count=5, include_project=False)
            prepared = prepare_import(path)
            try:
                with get_conn() as conn:
                    job = conn.execute("select upload_payload_json from sync_jobs where id=%s", (prepared.job_id,)).fetchone()
                    first = job["upload_payload_json"]["conversations"][0]
                    imported = _import_conversation(conn, prepared.job_id, "chatgpt", first, {})
                    conn.execute(
                        "update sync_jobs set status='running',stage='restoring_recent_chats',processed=1,items_processed=1,ready_for_use=true,entry_chat_id=%s where id=%s",
                        (imported["chat_id"], prepared.job_id),
                    )
                    save_checkpoint(
                        conn,
                        prepared.job_id,
                        "restoring_recent_chats",
                        1,
                        {"last_source_id": first["source_id"]},
                        cursor=first["source_id"],
                    )

                result = run_sync_job(prepared.job_id)
                self.assertIn(result["status"], {"completed", "completed_with_exceptions"})
                with get_conn() as conn:
                    chat_count = conn.execute("select count(*) as count from chats where import_job_id=%s", (prepared.job_id,)).fetchone()["count"]
                    report = conn.execute("select report_json from sync_validation_reports where job_id=%s", (prepared.job_id,)).fetchone()["report_json"]
                    job = conn.execute("select checkpoint_json,provider_cursor,retry_count from sync_jobs where id=%s", (prepared.job_id,)).fetchone()
                self.assertEqual(5, chat_count)
                self.assertGreaterEqual(report["duplicates_prevented"], 1)
                self.assertTrue(job["checkpoint_json"])
                self.assertIsNotNone(job["provider_cursor"])
            finally:
                cleanup_import(prepared)


if __name__ == "__main__":
    unittest.main()

