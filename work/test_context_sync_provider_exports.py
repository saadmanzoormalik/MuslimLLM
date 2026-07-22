import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from app.context_sync.connectors import get_connector


ROOT = Path(__file__).resolve().parents[1]


class ContextSyncProviderExportTests(unittest.TestCase):
    def test_chatgpt_fixture_is_ingested(self):
        fixture = ROOT / "work/fixtures/imports/chatgpt_export_sample.json"
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "official-export.zip"
            with ZipFile(archive_path, "w") as archive:
                archive.writestr("conversations.json", fixture.read_text(encoding="utf-8"))
            inventory = asyncio.run(get_connector("chatgpt").parse_official_export(str(archive_path)))
        self.assertGreater(inventory.conversations_found, 0)
        self.assertTrue(inventory.normalized["conversations"][0]["messages"])

    def test_zip_detects_conversations_json_and_preserves_file_metadata(self):
        payload = [{"id": "zip-chat", "title": "ZIP chat", "mapping": {}}]
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "export.zip"
            with ZipFile(archive_path, "w") as archive:
                archive.writestr("conversations.json", json.dumps(payload))
                archive.writestr("notes.md", "local attachment reference")
            inventory = asyncio.run(get_connector("chatgpt").parse_official_export(str(archive_path)))
        self.assertEqual(1, inventory.conversations_found)
        self.assertEqual(1, inventory.files_found)

    def test_malformed_json_is_visible(self):
        with tempfile.NamedTemporaryFile(suffix=".json") as handle:
            handle.write(b"{not-json")
            handle.flush()
            with self.assertRaises(json.JSONDecodeError):
                asyncio.run(get_connector("claude").parse_official_export(handle.name))


if __name__ == "__main__":
    unittest.main()
