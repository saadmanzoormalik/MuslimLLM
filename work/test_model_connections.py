import unittest

from app.context_sync.model_connections import ModelConnectionIn, _normalized_api_base, _public_connection


class ModelConnectionSecurityTests(unittest.TestCase):
    def test_local_connection_defaults_to_configured_loopback_model(self):
        base = _normalized_api_base(ModelConnectionIn(mode="local"))
        self.assertTrue(base.startswith("http://127.0.0.1:") or "ollama" in base)

    def test_local_mode_rejects_external_hosts(self):
        with self.assertRaisesRegex(ValueError, "limited to this device"):
            _normalized_api_base(ModelConnectionIn(mode="local", api_base="https://example.com/v1"))

    def test_remote_mode_requires_https(self):
        with self.assertRaisesRegex(ValueError, "must use HTTPS"):
            _normalized_api_base(ModelConnectionIn(mode="remote", api_base="http://example.com/v1", model="example"))

    def test_url_cannot_embed_credentials(self):
        with self.assertRaisesRegex(ValueError, "cannot contain credentials"):
            _normalized_api_base(ModelConnectionIn(mode="remote", api_base="https://key@example.com/v1", model="example"))

    def test_public_connection_hides_internal_model_id(self):
        public = _public_connection(
            {
                "id": "connection-id",
                "api_base": "https://api.example.com/v1",
                "api_model": "private-provider-model-id",
                "status": "active",
                "last_checked_at": None,
            }
        )
        self.assertEqual("Muslim LLM", public["model"])
        self.assertNotIn("private-provider-model-id", str(public))


if __name__ == "__main__":
    unittest.main()
