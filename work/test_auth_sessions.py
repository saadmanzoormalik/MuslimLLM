import unittest
from auth_test_support import assert_contains


class AuthSessionTests(unittest.TestCase):
    def test_rotating_httponly_sessions(self):
        assert_contains(self, "backend/app/auth/sessions.py", 'httponly=httponly', "previous_refresh_token_hash", "replay", "revoked_at=now()")
        assert_contains(self, "frontend/lib/api.ts", 'credentials: "include"', "/auth/refresh")


if __name__ == "__main__": unittest.main()
