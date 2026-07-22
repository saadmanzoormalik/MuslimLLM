import unittest

from app.context_sync.jobs.queue import enqueue_job
from app.context_sync.service import create_job
from app.db import get_conn


class ContextSyncResumeTests(unittest.TestCase):
    provider = "resume-test"

    def tearDown(self):
        with get_conn() as conn:
            conn.execute("delete from continuity_packages where source_provider=%s", (self.provider,))
            conn.execute("delete from normalized_context_items where provider_id=%s", (self.provider,))
            conn.execute("delete from chats where imported_from_provider=%s", (self.provider,))
            conn.execute("delete from projects where imported_from_provider=%s", (self.provider,))
            conn.execute("delete from sync_jobs where provider_id=%s", (self.provider,))

    def test_restarted_job_is_resumable_and_idempotent(self):
        normalized = {
            "projects": [{"source_id": "resume-project", "title": "Resume project"}],
            "files": [{"source_id": "resume-file", "name": "note.md"}],
            "conversations": [
                {
                    "source_id": "resume-chat",
                    "title": "Resume chat",
                    "project_source_id": "resume-project",
                    "messages": [{"role": "user", "content": "Continue after restart"}],
                }
            ],
        }
        inventory = {"conversations_found": 1, "projects_found": 1, "files_found": 1}
        job_id = create_job(self.provider, None, inventory, normalized)
        first = enqueue_job(job_id)
        self.assertEqual("completed", first["status"])
        with get_conn() as conn:
            conn.execute("update sync_jobs set status='failed_recoverable',stage='recovery' where id=%s", (job_id,))
        resumed = enqueue_job(job_id)
        self.assertEqual("completed", resumed["status"])
        with get_conn() as conn:
            count = conn.execute("select count(*) as count from chats where imported_from_provider=%s", (self.provider,)).fetchone()["count"]
            job = conn.execute("select status,percent,ready_for_use from sync_jobs where id=%s", (job_id,)).fetchone()
        self.assertEqual(1, count)
        self.assertEqual("completed", job["status"])
        self.assertEqual(100, float(job["percent"]))
        self.assertTrue(job["ready_for_use"])


if __name__ == "__main__":
    unittest.main()
