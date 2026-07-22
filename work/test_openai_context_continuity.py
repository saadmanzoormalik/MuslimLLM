import unittest

from app.context_sync.continuity import build_continuity_package


class OpenAIContextContinuityTests(unittest.TestCase):
    def test_package_contains_release_continuity_contract(self):
        conversation = {"source_id": "continuity-test", "title": "Build a research brief", "project_source_id": "research", "attachments": [{"name": "sources.pdf"}]}
        messages = [
            {"role": "user", "content": "I prefer concise analysis. Next, build the evidence table."},
            {"role": "assistant", "content": "The outline is ready and the next step is the evidence table."},
        ]
        package = build_continuity_package("chatgpt", conversation, messages, "local-chat")
        for key in ("summary", "current_objective", "key_facts", "decisions", "open_tasks", "unresolved_questions", "user_preferences", "important_people", "organizations", "projects", "important_dates", "referenced_files", "source_message_refs", "confidence"):
            self.assertIn(key, package)
        self.assertIn("research", package["projects"])
        self.assertIn("sources.pdf", package["referenced_files"])
        self.assertNotIn("http", str(package).lower())


if __name__ == "__main__":
    unittest.main()
