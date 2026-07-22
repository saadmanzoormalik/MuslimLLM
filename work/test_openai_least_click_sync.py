import asyncio
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from app.context_sync.openai_sync import resolve_openai_context_sync_method

ROOT = Path(__file__).resolve().parents[1]


class OpenAILeastClickSyncTests(unittest.TestCase):
    def test_release_path_is_official_export_without_verified_api_contract(self):
        disabled = {
            "CONTEXT_SYNC_OPENAI_HISTORY_API_DOCUMENTED": "false",
            "CONTEXT_SYNC_OPENAI_HISTORY_SCOPES_DOCUMENTED": "false",
            "CONTEXT_SYNC_OPENAI_HISTORY_CONTRACT_VERIFIED": "false",
            "CONTEXT_SYNC_OPENAI_HISTORY_PROJECT_FILES_TESTED": "false",
            "CONTEXT_SYNC_OPENAI_HISTORY_API_ENABLED": "false",
            "CONTEXT_SYNC_OPENAI_APPROVED_EXPORT_PATH": "",
        }
        with patch.dict(os.environ, disabled):
            self.assertEqual("official_export", asyncio.run(resolve_openai_context_sync_method()))

    def test_initial_ui_is_consent_connect_only(self):
        page = (ROOT / "frontend/app/context-sync/openai/page.tsx").read_text()
        self.assertIn("Bring your ChatGPT context with you", page)
        self.assertIn("I authorize Muslim LLM", page)
        self.assertIn("Connect ChatGPT", page)
        self.assertIn("Your imported data remains on this device by default", page)
        for forbidden in ["date range", "file format", "project mapping", "database settings", "model settings", "Connect OpenAI"]:
            self.assertNotIn(forbidden, page)

    def test_minimal_session_api_is_present(self):
        router = (ROOT / "backend/app/context_sync/router.py").read_text()
        for route in [
            "/openai/agree-and-connect", "/openai/session/{session_id}",
            "/openai/session/{session_id}/events", "/openai/session/{session_id}/grant-email-access",
            "/openai/session/{session_id}/grant-folder-access", "/openai/session/{session_id}/select-export",
            "/openai/session/{session_id}/resume", "/openai/session/{session_id}/cancel",
            "/openai/session/{session_id}/report", "/openai/imported-context",
        ]:
            self.assertIn(route, router)


if __name__ == "__main__":
    unittest.main()
