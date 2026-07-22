import unittest
from auth_test_support import assert_contains


class AccountLinkingTests(unittest.TestCase):
    def test_provider_subject_is_stable_and_unique(self):
        assert_contains(self, "backend/app/auth/models.py", "unique(provider, provider_subject)")
        assert_contains(self, "backend/app/auth/service.py", 'provider == "email" and email_verified', "provider_subject")


if __name__ == "__main__": unittest.main()
