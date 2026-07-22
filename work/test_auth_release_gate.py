import unittest
from auth_test_support import assert_contains, source


class AuthReleaseGate(unittest.TestCase):
    def test_no_blank_callback_or_fake_social_success(self):
        assert_contains(self, "frontend/app/auth/callback/page.tsx", "Try again", "Opening Muslim LLM")
        assert_contains(self, "backend/app/auth/router.py", "sign-in is not configured yet", "provider.verify")

    def test_accessibility_and_mobile_contract(self):
        onboarding = source("frontend/app/onboarding/page.tsx")
        self.assertIn("aria", source("frontend/components/onboarding/OnboardingQuestion.tsx"))
        self.assertIn("min-h-dvh", onboarding)


if __name__ == "__main__": unittest.main()
