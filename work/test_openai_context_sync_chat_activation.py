import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from app.context_sync.jobs.orchestrator import run_sync_job
from app.db import get_conn
from work.openai_context_sync_test_support import cleanup_import, make_export, prepare_import


class OpenAIContextSyncChatActivationTests(unittest.TestCase):
    def test_recent_chats_are_openable_while_older_history_is_running(self):
        with tempfile.TemporaryDirectory() as directory:
            path, _ = make_export(Path(directory) / "chatgpt-export.zip", conversation_count=12)
            prepared = prepare_import(path)
            worker_result = {}

            def work():
                worker_result.update(run_sync_job(prepared.job_id))

            try:
                with patch.dict(os.environ, {"CONTEXT_SYNC_RECENT_BATCH_SIZE": "2"}), patch(
                    "app.context_sync.jobs.progressive_import.demo_pacing",
                    side_effect=lambda _provider: time.sleep(0.025),
                ):
                    thread = threading.Thread(target=work, daemon=True)
                    thread.start()
                    progressive_snapshot = None
                    deadline = time.monotonic() + 10
                    while time.monotonic() < deadline:
                        with get_conn() as conn:
                            job = conn.execute("select status,ready_for_use,entry_chat_id from sync_jobs where id=%s", (prepared.job_id,)).fetchone()
                            chat_count = conn.execute("select count(*) as count from chats where import_job_id=%s", (prepared.job_id,)).fetchone()["count"]
                        if job["status"] == "running" and job["ready_for_use"] and 2 <= chat_count < 12:
                            progressive_snapshot = (job, chat_count)
                            break
                        time.sleep(0.01)
                    self.assertIsNotNone(progressive_snapshot, "Recent chats never became available during background import")
                    thread.join(timeout=15)
                    self.assertFalse(thread.is_alive())

                self.assertIn(worker_result["status"], {"completed", "completed_with_exceptions"})
                with get_conn() as conn:
                    latest = conn.execute(
                        "select id from chats where import_job_id=%s order by updated_at desc limit 1",
                        (prepared.job_id,),
                    ).fetchone()
                    roles = conn.execute(
                        "select role,import_order,source_message_id,imported_untrusted from messages where chat_id=%s order by import_order",
                        (latest["id"],),
                    ).fetchall()
                    package = conn.execute("select package_json from continuity_packages where local_chat_id=%s", (latest["id"],)).fetchone()
                    conn.execute("insert into messages (chat_id,role,content) values (%s,'user','Continue from the imported plan')", (latest["id"],))
                    continued = conn.execute("select count(*) as count from messages where chat_id=%s", (latest["id"],)).fetchone()["count"]
                self.assertEqual(["user", "assistant"], [row["role"] for row in roles])
                self.assertTrue(all(row["source_message_id"] for row in roles))
                self.assertTrue(all(row["imported_untrusted"] for row in roles))
                self.assertTrue(package["package_json"]["current_objective"])
                self.assertEqual(3, continued)
            finally:
                cleanup_import(prepared)


if __name__ == "__main__":
    unittest.main()

