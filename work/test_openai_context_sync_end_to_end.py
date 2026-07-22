import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.context_sync.jobs.orchestrator import run_sync_job
from app.context_sync.openai.export_flow import (
    OFFICIAL_OPENAI_EXPORT_GUIDE,
    begin_openai_export_flow,
    resolve_best_acquisition_method,
    resolve_real_openai_transfer_method,
)
from app.context_sync.state_machine import create_transfer_consent, get_transfer_session, transition_session
from app.db import get_conn
from work.openai_context_sync_test_support import cleanup_import, make_export, prepare_import


class OpenAIContextSyncEndToEndTests(unittest.TestCase):
    def test_official_export_file_picker_runs_to_usable_validated_context(self):
        consent = create_transfer_consent("end-to-end-device", accepted=True)
        session_id = None
        prepared = None
        try:
            with patch("app.context_sync.openai.export_flow.valid_user_authorized_folder_permission_exists", return_value=False):
                flow = asyncio.run(begin_openai_export_flow(str(consent["id"]), "end-to-end-device"))
                session_id = flow.session_id
                method = asyncio.run(resolve_best_acquisition_method(flow))
            self.assertEqual("official_export_file_picker", method.method)
            self.assertTrue(OFFICIAL_OPENAI_EXPORT_GUIDE.startswith("https://help.openai.com/"))

            with tempfile.TemporaryDirectory() as directory:
                path, _ = make_export(Path(directory) / "chatgpt-export.zip", conversation_count=3)
                prepared = prepare_import(path)
            transition_session(
                session_id,
                "importing_recent_context",
                event_type="test_official_export_selected",
                sync_job_id=prepared.job_id,
                background_sync_continues=True,
            )
            result = run_sync_job(prepared.job_id)
            self.assertIn(result["status"], {"completed", "completed_with_exceptions"})
            session = get_transfer_session(session_id)
            self.assertTrue(session["ready_for_use"])
            self.assertEqual(3, session["available_chat_count"])
            self.assertIsNotNone(session["latest_imported_chat_id"])
            with get_conn() as conn:
                report = conn.execute("select report_json from sync_validation_reports where job_id=%s", (prepared.job_id,)).fetchone()["report_json"]
            self.assertIn(report["validation_status"], {"passed", "passed_with_exceptions"})
            self.assertEqual(report["conversations_discovered"], report["conversations_imported"])
            self.assertEqual(report["messages_discovered"], report["messages_imported"])
        finally:
            if prepared:
                cleanup_import(prepared)
            if session_id:
                with get_conn() as conn:
                    conn.execute("delete from context_transfer_sessions where id=%s", (session_id,))
            with get_conn() as conn:
                conn.execute("delete from context_transfer_consents where id=%s", (consent["id"],))

    def test_flags_alone_cannot_enable_an_unimplemented_history_adapter(self):
        enabled = {
            "CONTEXT_SYNC_OPENAI_HISTORY_API_DOCUMENTED": "true",
            "CONTEXT_SYNC_OPENAI_HISTORY_SCOPES_DOCUMENTED": "true",
            "CONTEXT_SYNC_OPENAI_HISTORY_CONTRACT_VERIFIED": "true",
            "CONTEXT_SYNC_OPENAI_HISTORY_PROJECT_FILES_TESTED": "true",
            "CONTEXT_SYNC_OPENAI_HISTORY_API_ENABLED": "true",
        }
        connection = {"status": "connected", "granted_capabilities": ["chat_history_access"]}
        with patch.dict(os.environ, enabled, clear=False), patch("app.context_sync.openai.export_flow.valid_user_authorized_folder_permission_exists", return_value=False):
            method = asyncio.run(resolve_real_openai_transfer_method(connection, "darwin"))
        self.assertEqual("official_export_file_picker", method)

    def test_frontend_never_collects_openai_credentials(self):
        page = (Path(__file__).parents[1] / "frontend/app/context-sync/openai/page.tsx").read_text()
        lowered = page.lower()
        self.assertNotIn('type="password"', lowered)
        self.assertNotIn("chatgpt session token", lowered)
        self.assertNotIn("browser cookie", lowered)
        self.assertIn("help.openai.com", (Path(__file__).parents[1] / "backend/app/context_sync/openai/export_flow.py").read_text())


if __name__ == "__main__":
    unittest.main()

