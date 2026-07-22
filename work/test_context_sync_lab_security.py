#!/usr/bin/env python3
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.context_sync.connectors.openai_export import ExportSecurityError, parse_openai_export
from work.context_sync_lab_fixture import create_export


class ExportSecurityTests(unittest.TestCase):
    def test_branches_and_injection_are_preserved_but_untrusted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = create_export(Path(directory) / "export.zip", suspicious=True)
            parsed = parse_openai_export(path)
            self.assertEqual(parsed.conversations[0]["message_count"], 2)
            self.assertEqual(sum(not item["is_active_branch"] for item in parsed.branches), 1)
            suspect = next(item for item in parsed.nodes if item["source_node_id"] == "u1")
            self.assertTrue(suspect["is_untrusted_instruction"])
            self.assertTrue(any(item["kind"] == "prompt_injection_signal" for item in parsed.exceptions))

    def test_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("../escape.txt", "no")
                archive.writestr("conversations.json", "[]")
            with self.assertRaises(ExportSecurityError):
                parse_openai_export(path)

    def test_oversized_archive_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large.zip"
            with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
                archive.writestr("conversations.json", json.dumps([]))
                archive.writestr("large.txt", "x" * 2048)
            with self.assertRaises(ExportSecurityError):
                parse_openai_export(path, max_uncompressed_bytes=1024)


if __name__ == "__main__":
    unittest.main(verbosity=2)
