import asyncio
import os
import unittest
from unittest.mock import patch

from app.context_sync.openai.export_flow import begin_openai_export_flow, resolve_best_acquisition_method
from app.context_sync.service import ensure_context_sync_ready
from app.context_sync.state_machine import create_transfer_consent, get_transfer_session, session_events
from app.db import get_conn


class OpenAITransferOrchestratorTests(unittest.TestCase):
    def setUp(self):
        ensure_context_sync_ready()
        self.session_ids = []
        self.consent_ids = []

    def tearDown(self):
        with get_conn() as conn:
            for session_id in self.session_ids:
                conn.execute("delete from context_transfer_sessions where id=%s", (session_id,))
            for consent_id in self.consent_ids:
                conn.execute("delete from context_transfer_consents where id=%s", (consent_id,))

    def test_consent_opens_official_flow_and_selects_real_file_picker_fallback(self):
        consent = create_transfer_consent("test-device", accepted=True)
        self.consent_ids.append(str(consent["id"]))
        with patch.dict(os.environ, {"CONTEXT_SYNC_OPENAI_EMAIL_DETECTION_ENABLED": "false"}), patch("app.context_sync.openai.export_flow.latest_folder_watch", return_value=None):
            flow = asyncio.run(begin_openai_export_flow(str(consent["id"]), "test-device"))
            self.session_ids.append(flow.session_id)
            method = asyncio.run(resolve_best_acquisition_method(flow))
        self.assertEqual("official_export_file_picker", method.method)
        public = get_transfer_session(flow.session_id)
        self.assertEqual("awaiting_file_selection", public["state"])
        self.assertEqual("select_file", public["next_action"])
        states = [event["to_state"] for event in session_events(flow.session_id)]
        self.assertEqual(["consented", "opening_openai", "awaiting_file_selection"], states)

    def test_consent_is_required(self):
        with self.assertRaisesRegex(ValueError, "transfer_consent_required"):
            create_transfer_consent("test-device", accepted=False)


if __name__ == "__main__":
    unittest.main()
