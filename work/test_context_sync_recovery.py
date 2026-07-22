import unittest
from pathlib import Path

from app.context_sync.continuity import build_continuity_package
from app.context_sync.dedupe import conversation_fingerprint
from app.context_sync.jobs.retries import backoff_seconds


ROOT = Path(__file__).resolve().parents[1]


class ContextSyncRecoveryTests(unittest.TestCase):
    def test_conversation_fingerprint_is_stable(self):
        conversation = {"source_id": "source-1", "title": "Work", "messages": [{"role": "user", "content": "Continue"}]}
        self.assertEqual(conversation_fingerprint("chatgpt", conversation), conversation_fingerprint("chatgpt", conversation))

    def test_retry_backoff_is_bounded(self):
        self.assertLessEqual(backoff_seconds(20), 30.25)

    def test_restart_recovery_is_wired_to_startup(self):
        main = (ROOT / "backend/app/main.py").read_text()
        service = (ROOT / "backend/app/context_sync/service.py").read_text()
        self.assertIn("recover_pending_jobs", main)
        self.assertIn("status in ('authorized','running','failed_recoverable')", service)

    def test_continuity_package_supports_immediate_continuation(self):
        messages = [
            {"role": "user", "content": "Build the importer and continue tomorrow"},
            {"role": "assistant", "content": "Next: verify the durable queue"},
        ]
        package = build_continuity_package("claude", {"source_id": "c1", "title": "Importer"}, messages)
        self.assertTrue(package["current_objective"])
        self.assertTrue(package["continuation_prompt"])
        self.assertGreater(package["confidence"], 0.5)


if __name__ == "__main__":
    unittest.main()
