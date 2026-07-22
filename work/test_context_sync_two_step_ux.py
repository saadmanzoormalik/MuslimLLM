import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ContextSyncTwoStepUXTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = (ROOT / "frontend/app/context-sync/page.tsx").read_text()
        cls.progress = (ROOT / "frontend/components/context-sync/SyncProgress.tsx").read_text()
        cls.complete = (ROOT / "frontend/components/context-sync/SyncComplete.tsx").read_text()
        cls.provider = (ROOT / "frontend/components/context-sync/provider-card.tsx").read_text()
        cls.consent = (ROOT / "frontend/components/context-sync/ConnectConsent.tsx").read_text()
        cls.model_connection = (ROOT / "frontend/components/context-sync/ModelConnectionDialog.tsx").read_text()
        cls.visible_flow = "\n".join([cls.page, cls.progress, cls.complete, cls.provider, cls.consent, cls.model_connection])

    def test_user_flow_has_provider_selection_and_one_combined_sync_step(self):
        self.assertIn("Your model. Muslim LLM.", self.page)
        self.assertIn("Bring existing chats", self.page)
        self.assertIn("Connect {provider.display_name}", self.consent)
        self.assertIn("Bringing your context into Muslim LLM", self.progress)
        self.assertIn("Your context is ready", self.complete)

    def test_no_third_confirmation_step(self):
        for phrase in ["Ready to sync", "Sync now", "Choose export", "View projects", "Sync details"]:
            self.assertNotIn(phrase, self.visible_flow)

    def test_no_technical_configuration_or_inventory(self):
        for phrase in ["Date range", "Timeline", "Scope", "File types", "API details", "Parser", "Cursor", "Token count"]:
            self.assertNotIn(phrase, self.visible_flow)

    def test_provider_cards_expose_only_name_mark_and_connect(self):
        self.assertNotIn("compact_status", self.provider)
        self.assertNotIn("capabilities", self.provider)
        self.assertIn("provider.display_name", self.provider)
        self.assertIn("provider.button_label", self.provider)

    def test_authentication_uses_provider_oauth_or_official_export_only(self):
        self.assertIn("Muslim LLM never sees your password", self.consent)
        self.assertIn("Official OAuth connection", self.consent)
        self.assertIn("window.location.assign(result.authorization_url)", self.page)
        self.assertIn('type="file"', self.page)
        self.assertIn("/context-sync/official-export/", self.page)
        self.assertIn("Continue secure connection", self.consent)
        for forbidden in ['name="password"', 'name="cookie"', 'name="session_token"']:
            self.assertNotIn(forbidden, self.visible_flow)

    def test_model_connection_is_explicit_and_secret_aware(self):
        self.assertIn("Connect your model", self.model_connection)
        self.assertIn("Credentials are encrypted at rest", self.model_connection)
        self.assertIn('type="password"', self.model_connection)
        self.assertIn("Test and connect", self.model_connection)
        self.assertIn("No credential. Data stays on this device.", self.model_connection)


if __name__ == "__main__":
    unittest.main()
