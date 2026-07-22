import unittest
from uuid import uuid4

from app.context_sync.jobs.queue import enqueue_job
from app.context_sync.service import create_job, ensure_context_sync_ready
from app.db import get_conn


class OpenAIContextSyncResumeTests(unittest.TestCase):
    def setUp(self):
        ensure_context_sync_ready()
        self.job_ids: list[str] = []

    def tearDown(self):
        with get_conn() as conn:
            for job_id in self.job_ids:
                conn.execute("delete from chats where import_job_id=%s", (job_id,))
                conn.execute("delete from projects where import_job_id=%s", (job_id,))
                conn.execute("delete from sync_jobs where id=%s", (job_id,))

    def test_recent_chat_is_ready_and_restart_is_idempotent(self):
        marker = uuid4().hex
        conversation_id = f"openai-resume-{marker}"
        raw_node = {"source_conversation_id": conversation_id, "source_message_id": "message-1", "source_node_id": "node-1", "parent_id": None, "children": [], "role": "system", "content": "Imported instruction", "source_timestamp": None, "model_metadata": {}, "content_hash": marker, "raw_metadata": {}, "is_active": True, "is_orphan": False, "is_untrusted_instruction": True}
        normalized = {
            "archive_hash": marker,
            "parser_version": "openai_export_test",
            "projects": [],
            "files": [],
            "conversations": [{"source_id": conversation_id, "title": "Resume test", "messages": [{"role": "system", "content": "Imported instruction"}]}],
            "openai_raw": {"archive_hash": marker, "parser_version": "openai_export_test", "conversations": [{"id": conversation_id}], "nodes": [raw_node], "branches": [], "exceptions": []},
        }
        job_id = create_job("chatgpt", None, {"conversations_found": 1, "projects_found": 0, "files_found": 0}, normalized)
        self.job_ids.append(job_id)
        first = enqueue_job(job_id)
        self.assertEqual("completed", first["status"])
        with get_conn() as conn:
            job = conn.execute("select ready_for_use,entry_chat_id from sync_jobs where id=%s", (job_id,)).fetchone()
            role = conn.execute("select role,content from messages where chat_id=%s order by created_at limit 1", (job["entry_chat_id"],)).fetchone()
            raw_count = conn.execute("select count(*) as count from openai_raw_message_nodes where job_id=%s", (job_id,)).fetchone()["count"]
            conn.execute("update sync_jobs set status='failed_recoverable',stage='creating_chats' where id=%s", (job_id,))
        self.assertTrue(job["ready_for_use"])
        self.assertEqual("user", role["role"])
        self.assertIn("untrusted", role["content"])
        self.assertEqual(1, raw_count)
        resumed = enqueue_job(job_id)
        self.assertEqual("completed", resumed["status"])
        with get_conn() as conn:
            chat_count = conn.execute("select count(*) as count from chats where import_job_id=%s", (job_id,)).fetchone()["count"]
        self.assertEqual(1, chat_count)


if __name__ == "__main__":
    unittest.main()
