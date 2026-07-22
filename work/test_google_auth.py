import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.auth.providers.base import pkce_pair
from app.auth.providers.google import GOOGLE
from app.auth.security import opaque_token


class GoogleAuthTests(unittest.TestCase):
    def test_authorization_code_pkce_state_nonce(self):
        verifier = opaque_token(48)
        _, challenge = pkce_pair(verifier)
        url = GOOGLE.authorization_url("client", "http://localhost/callback", "state-value", "nonce-value", challenge)
        for value in ("response_type=code", "code_challenge=", "state=state-value", "nonce=nonce-value", "openid"):
            self.assertIn(value, url)
        self.assertNotIn(verifier, url)


if __name__ == "__main__": unittest.main()
