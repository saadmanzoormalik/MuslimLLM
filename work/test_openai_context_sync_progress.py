import tempfile
import unittest
from pathlib import Path

from app.context_sync.jobs.orchestrator import run_sync_job
from app.db import get_conn
from work.openai_context_sync_test_support import cleanup_import, make_export, prepare_import


class OpenAIContextSyncProgressTests(unittest.TestCase):
    def test_progress_events_are_persisted_from_real_import_stages(self):
        with tempfile.TemporaryDirectory() as directory:
            path, _ = make_export(Path(directory) / "chatgpt-export.zip", conversation_count=4)
            prepared = prepare_import(path)
            try:
                result = run_sync_job(prepared.job_id)
                self.assertIn(result["status"], {"completed", "completed_with_exceptions"})
                with get_conn() as conn:
                    events = conn.execute(
                        "select stage,status,processed,total,percent,estimated_seconds_remaining from sync_job_events where job_id=%s order by created_at,id",
                        (prepared.job_id,),
                    ).fetchall()
                    job = conn.execute("select * from sync_jobs where id=%s", (prepared.job_id,)).fetchone()
                stages = [row["stage"] for row in events]
                for required in (
                    "reading_conversations",
                    "restoring_recent_chats",
                    "recent_context_ready",
                    "restoring_projects",
                    "processing_files",
                    "building_working_context",
                    "validating_transfer",
                    "context_ready",
                ):
                    self.assertIn(required, stages)
                self.assertTrue(all(float(row["percent"]) >= 0 for row in events))
                self.assertEqual(100, float(job["percent"]))
                self.assertEqual(job["processed"], job["items_processed"])
                self.assertEqual(job["total"], job["items_discovered"])
            finally:
                cleanup_import(prepared)


if __name__ == "__main__":
    unittest.main()

