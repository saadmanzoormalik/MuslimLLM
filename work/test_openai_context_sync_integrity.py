import tempfile
import unittest
from pathlib import Path

from app.context_sync.jobs.orchestrator import run_sync_job
from app.db import get_conn
from work.openai_context_sync_test_support import cleanup_import, make_export, prepare_import


class OpenAIContextSyncIntegrityTests(unittest.TestCase):
    def test_completion_report_reconciles_records_and_surfaces_exceptions(self):
        with tempfile.TemporaryDirectory() as directory:
            path, _ = make_export(
                Path(directory) / "chatgpt-export.zip",
                conversation_count=3,
                orphan=True,
            )
            prepared = prepare_import(path)
            try:
                result = run_sync_job(prepared.job_id)
                self.assertEqual("completed_with_exceptions", result["status"])
                with get_conn() as conn:
                    report = conn.execute("select report_json,validation_status from sync_validation_reports where job_id=%s", (prepared.job_id,)).fetchone()
                    archive = conn.execute("select archive_hash,integrity_status from openai_export_archives where job_id=%s", (prepared.job_id,)).fetchone()
                    job = conn.execute("select status,stage,ready_for_use from sync_jobs where id=%s", (prepared.job_id,)).fetchone()
                details = report["report_json"]
                self.assertEqual("passed_with_exceptions", report["validation_status"])
                self.assertEqual(details["conversations_discovered"], details["conversations_imported"])
                self.assertEqual(details["messages_discovered"], details["messages_imported"])
                self.assertEqual(details["projects_discovered"], details["projects_transferred"])
                self.assertEqual(details["files_discovered"], details["files_imported"])
                self.assertEqual(details["branches_discovered"], details["branches_preserved"])
                self.assertEqual(details["continuity_validations_run"], details["continuity_validations_passed"])
                self.assertTrue(details["exceptions"])
                self.assertEqual(64, len(archive["archive_hash"]))
                self.assertEqual("validated", archive["integrity_status"])
                self.assertEqual("context_ready", job["stage"])
                self.assertTrue(job["ready_for_use"])
            finally:
                cleanup_import(prepared)


if __name__ == "__main__":
    unittest.main()

