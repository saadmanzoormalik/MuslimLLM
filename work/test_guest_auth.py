import unittest
from auth_test_support import assert_contains


class GuestAuthTests(unittest.TestCase):
    def test_guest_is_durable_and_hashed(self):
        assert_contains(self, "backend/app/auth/models.py", "guest_accounts", "guest_token_hash", "device_id")
        assert_contains(self, "backend/app/auth/service.py", "token_hash(guest_secret)", "claim_existing")


if __name__ == "__main__": unittest.main()
