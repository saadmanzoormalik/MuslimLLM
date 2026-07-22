import unittest
from auth_test_support import source


class AuthSecurityTests(unittest.TestCase):
    def test_secrets_do_not_reach_frontend(self):
        frontend = "\n".join(source(path) for path in ["frontend/lib/api.ts", "frontend/app/auth/page.tsx", "frontend/components/auth/AuthBoundary.tsx"])
        for forbidden in ("GOOGLE_OAUTH_CLIENT_SECRET", "APPLE_PRIVATE_KEY", "refresh_token_hash"):
            self.assertNotIn(forbidden, frontend)

    def test_tokens_not_in_local_storage(self):
        auth = source("frontend/components/auth/AuthBoundary.tsx") + source("frontend/lib/api.ts")
        self.assertNotIn("localStorage", auth)
        self.assertIn('credentials: "include"', auth)


if __name__ == "__main__": unittest.main()
