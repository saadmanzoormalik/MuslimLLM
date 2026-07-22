import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from app.context_sync.openai_folder_watch import find_export_candidate
from app.context_sync.workers.email_detector import approved_sender, email_detection_enabled
from work.test_openai_export_parser import branched_conversation


class OpenAIExportDetectionTests(unittest.TestCase):
    def test_folder_scan_ignores_unrelated_zip_and_detects_valid_export(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with zipfile.ZipFile(folder / "unrelated.zip", "w") as archive:
                archive.writestr("notes.txt", "not an export")
            export = folder / "chatgpt-export.zip"
            with zipfile.ZipFile(export, "w") as archive:
                archive.writestr("conversations.json", json.dumps([branched_conversation()]))
            candidate = find_export_candidate(folder, set())
            self.assertIsNotNone(candidate)
            self.assertEqual(export, candidate[0])

    def test_email_sender_scope_is_narrow_and_disabled_by_default(self):
        self.assertTrue(approved_sender("noreply@tm.openai.com"))
        self.assertTrue(approved_sender("privacy@openai.com"))
        self.assertFalse(approved_sender("openai-export@example.com"))
        self.assertFalse(email_detection_enabled())


if __name__ == "__main__":
    unittest.main()
