import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.auth.providers.apple import APPLE


class AppleAuthTests(unittest.TestCase):
    def test_form_post_and_oidc_controls(self):
        url = APPLE.authorization_url("service", "https://example.com/callback", "state", "nonce", "challenge")
        for value in ("response_type=code", "response_mode=form_post", "state=state", "nonce=nonce", "code_challenge="):
            self.assertIn(value, url)


if __name__ == "__main__": unittest.main()
