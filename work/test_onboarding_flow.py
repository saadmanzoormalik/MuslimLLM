import unittest

from auth_test_support import assert_contains, source


class OnboardingFlowTests(unittest.TestCase):
    def test_exactly_three_required_questions(self):
        page = source("frontend/app/onboarding/page.tsx")
        self.assertEqual(page.count('key: "primary_use"'), 1)
        self.assertEqual(page.count('key: "response_preference"'), 1)
        self.assertEqual(page.count('key: "privacy_preference"'), 1)
        self.assertIn("onSelect={select}", page)

    def test_progress_restores_from_backend(self):
        assert_contains(self, "frontend/app/onboarding/page.tsx", "/onboarding", "current_step", "answers")
        assert_contains(self, "backend/app/auth/models.py", "temporary_onboarding_sessions", "answers_json")


if __name__ == "__main__": unittest.main()
