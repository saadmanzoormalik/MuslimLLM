import asyncio
import os
import unittest
from unittest.mock import patch

from app.context_sync.connectors import CONNECTORS, get_connector
from app.context_sync.providers.registry import provider_list
from app.context_sync.security.oauth import pkce_pair
from app.context_sync.security.oauth_service import begin_oauth_connection, provider_oauth_config


class ContextSyncBackendTests(unittest.TestCase):
    def test_all_expected_providers_are_registered(self):
        expected = {"demo", "chatgpt", "claude", "gemini", "copilot", "perplexity", "deepseek", "grok", "qwen", "glm", "other"}
        self.assertEqual(expected, set(CONNECTORS))
        self.assertEqual(expected, {provider["provider_id"] for provider in provider_list()})

    def test_connectors_share_the_provider_neutral_contract(self):
        required = {
            "begin_connection",
            "complete_connection",
            "discover_context",
            "fetch_context_batch",
            "parse_official_export",
            "revoke_connection",
        }
        for provider_id in CONNECTORS:
            connector = get_connector(provider_id)
            self.assertTrue(required.issubset(set(dir(connector))), provider_id)

    def test_unconfigured_provider_cannot_claim_oauth_history_access(self):
        keys = [key for key in os.environ if key.startswith("CONTEXT_SYNC_TESTPROVIDER_")]
        with patch.dict(os.environ, {key: "" for key in keys}, clear=False):
            config = provider_oauth_config("testprovider")
        self.assertFalse(config.configured)
        self.assertFalse(config.available)

    def test_pkce_uses_distinct_verifier_and_s256_challenge(self):
        verifier, challenge = pkce_pair()
        self.assertGreater(len(verifier), 42)
        self.assertNotEqual(verifier, challenge)
        self.assertNotIn("=", challenge)

    @patch("app.context_sync.security.oauth_service.put_state")
    def test_verified_oauth_connection_returns_provider_redirect(self, put_state_mock):
        configured = {
            "CONTEXT_SYNC_TESTPROVIDER_CLIENT_ID": "client-id",
            "CONTEXT_SYNC_TESTPROVIDER_CLIENT_SECRET": "client-secret",
            "CONTEXT_SYNC_TESTPROVIDER_AUTHORIZE_URL": "https://provider.example/authorize",
            "CONTEXT_SYNC_TESTPROVIDER_TOKEN_URL": "https://provider.example/token",
            "CONTEXT_SYNC_TESTPROVIDER_API_BASE": "https://provider.example/api/",
            "CONTEXT_SYNC_TESTPROVIDER_HISTORY_PATH": "history",
            "CONTEXT_SYNC_TESTPROVIDER_VERIFIED_HISTORY": "true",
        }
        with patch.dict(os.environ, configured, clear=False):
            result = begin_oauth_connection("testprovider", "connection-id", "http://127.0.0.1:3000/context-sync")
        self.assertEqual("redirect", result["next_action"])
        self.assertIn("code_challenge_method=S256", result["authorization_url"])
        self.assertIn("state=", result["authorization_url"])
        self.assertNotIn("client-secret", result["authorization_url"])
        put_state_mock.assert_called_once()

    def test_no_provider_claims_unverified_direct_history_access(self):
        for provider in provider_list():
            if provider["integration_status"] == "direct":
                self.assertTrue(provider["test_backed_direct_sync"])


if __name__ == "__main__":
    unittest.main()
