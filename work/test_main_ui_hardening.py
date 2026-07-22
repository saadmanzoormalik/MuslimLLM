from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "frontend/app/page.tsx").read_text()
SIDEBAR = (ROOT / "frontend/components/sidebar.tsx").read_text()
DRAWER = (ROOT / "frontend/components/source-drawer.tsx").read_text()
ONBOARDING = (ROOT / "frontend/app/onboarding/page.tsx").read_text()
AUTH = (ROOT / "frontend/components/auth/AuthBoundary.tsx").read_text()


class MainUiHardeningTests(unittest.TestCase):
    def test_main_header_has_visible_labels_and_onboarding_preview(self):
        context_transfer = (ROOT / "frontend/components/quick-context-transfer.tsx").read_text()
        for label in ["Onboarding", "Theme", "Sources", "Context Sync"]:
            self.assertTrue(label in PAGE or label in context_transfer)
        self.assertIn('href="/onboarding?preview=1"', PAGE)
        self.assertIn("previewingOnboarding", AUTH)
        self.assertIn("Your current workspace and saved preferences were not changed.", ONBOARDING)

    def test_navigation_and_drawer_are_accessible_and_non_overlapping(self):
        for contract in ["Close navigation", "Search all chats", "Actions for", "Chats and projects"]:
            self.assertTrue(contract in PAGE or contract in SIDEBAR)
        self.assertIn("if (!open) return null", DRAWER)
        self.assertIn('role="dialog"', DRAWER)
        self.assertIn("max-h-44", SIDEBAR)
        self.assertIn("grid-cols-2", SIDEBAR)
        self.assertIn("Context Sync", SIDEBAR)
        self.assertIn("scrollIntoView", SIDEBAR)


if __name__ == "__main__":
    unittest.main()
