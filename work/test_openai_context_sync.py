import asyncio
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from app.context_sync.openai_sync import OPENAI_EXPORT_URL, resolve_openai_context_sync_method


class OpenAIContextSyncContractTests(unittest.TestCase):
    root = Path(__file__).resolve().parents[1]

    def test_top_button_opens_exact_route(self):
        component = (self.root / "frontend/components/quick-context-transfer.tsx").read_text()
        self.assertIn('LLM Context Sync', component)
        self.assertIn('href="/context-sync/openai"', component)
        self.assertNotIn("ProviderCapability", component)

    def test_official_export_is_default_and_api_key_is_irrelevant(self):
        environment = {
            "CONTEXT_SYNC_OPENAI_VERIFIED_HISTORY": "false",
            "CONTEXT_SYNC_OPENAI_APPROVED_EXPORT_PATH": "",
            "OPENAI_API_KEY": "must-not-grant-history-access",
        }
        with patch.dict(os.environ, environment, clear=False):
            self.assertEqual("official_export", asyncio.run(resolve_openai_context_sync_method()))
        self.assertIn("help.openai.com", OPENAI_EXPORT_URL)

    def test_approved_local_export_is_selected_without_global_scan(self):
        with patch("app.context_sync.openai_sync.Path.is_file", return_value=True), patch.dict(os.environ, {"CONTEXT_SYNC_OPENAI_VERIFIED_HISTORY": "false", "CONTEXT_SYNC_OPENAI_APPROVED_EXPORT_PATH": "/user-approved/chatgpt.zip"}, clear=False):
            self.assertEqual("local_export_import", asyncio.run(resolve_openai_context_sync_method()))

    def test_normal_route_has_only_simple_primary_states(self):
        page = (self.root / "frontend/app/context-sync/openai/page.tsx").read_text()
        self.assertIn("Connect ChatGPT", page)
        self.assertIn("Select ChatGPT export", page)
        self.assertIn("Syncing your ChatGPT context", page)
        self.assertIn("Your ChatGPT context is ready", page)
        self.assertNotIn("API key", page)
        self.assertNotIn("OAuth scope", page)
        self.assertIn("/context-sync/openai/session/", page)

    def test_backend_recovers_approved_folder_watches(self):
        main = (self.root / "backend/app/main.py").read_text()
        watcher = (self.root / "backend/app/context_sync/openai_folder_watch.py").read_text()
        self.assertIn("recover_openai_folder_watches", main)
        self.assertIn("openai_export_folder_watches", watcher)
        self.assertNotIn("rglob", watcher)


if __name__ == "__main__":
    unittest.main()
