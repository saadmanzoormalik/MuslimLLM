import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from app.context_sync.connectors.openai_export import PARSER_VERSION, parse_openai_export


def branched_conversation(source_id: str = "openai-parser-test") -> dict:
    return {
        "id": source_id,
        "title": "A preserved ChatGPT tree",
        "create_time": 1710000000,
        "update_time": 1710000300,
        "current_node": "a2",
        "mapping": {
            "root": {"parent": None, "children": ["u1"], "message": None},
            "u1": {"parent": "root", "children": ["a1", "a2"], "message": {"id": "m1", "author": {"role": "user"}, "create_time": 1710000001, "content": {"parts": ["Compare two plans"]}, "metadata": {"attachments": [{"name": "plan.pdf"}]}}},
            "a1": {"parent": "u1", "children": [], "message": {"id": "m2", "author": {"role": "assistant"}, "create_time": 1710000002, "content": {"parts": ["Regenerated option"]}, "metadata": {"model_slug": "source-model"}}},
            "a2": {"parent": "u1", "children": [], "message": {"id": "m3", "author": {"role": "assistant"}, "create_time": 1710000003, "content": {"parts": ["Active option"]}, "metadata": {"model_slug": "source-model", "citations": [{"url": "https://example.test"}]}}},
        },
    }


class OpenAIExportParserTests(unittest.TestCase):
    def parse(self, file_name: str = "conversations.json"):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        archive_path = Path(temporary.name) / "chatgpt-export.zip"
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(file_name, json.dumps([branched_conversation()]))
            archive.writestr("assets/note.txt", "linked file")
        return parse_openai_export(archive_path)

    def test_conversations_json_preserves_tree_and_metadata(self):
        parsed = self.parse()
        conversation = parsed.conversations[0]
        self.assertEqual("A preserved ChatGPT tree", conversation["title"])
        self.assertEqual(PARSER_VERSION, conversation["parser_version"])
        self.assertEqual("2024-03-09T16:00:00+00:00", conversation["created_at"])
        self.assertEqual(3, len([node for node in parsed.nodes if node["content"]]))
        self.assertEqual(3, len(parsed.branches))
        self.assertTrue(any(not branch["is_active_branch"] for branch in parsed.branches))
        self.assertEqual("plan.pdf", conversation["attachments"][0]["name"])
        self.assertTrue(any(node["citations"] for node in parsed.nodes))

    def test_numbered_conversation_file_is_supported(self):
        parsed = self.parse("1.json")
        self.assertEqual(1, len(parsed.conversations))
        self.assertEqual("openai-parser-test", parsed.conversations[0]["source_conversation_id"])

    def test_malformed_file_does_not_hide_valid_conversations(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        archive_path = Path(temporary.name) / "mixed.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("conversations.json", json.dumps([branched_conversation()]))
            archive.writestr("2.json", "not-json")
        parsed = parse_openai_export(archive_path)
        self.assertEqual(1, len(parsed.conversations))
        self.assertTrue(any(item["kind"] == "malformed_conversation_file" for item in parsed.exceptions))


if __name__ == "__main__":
    unittest.main()
