import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from app.context_sync.security.archive_security import validate_archive_for_extraction
from app.context_sync.security.download_security import validate_export_url
from work.test_openai_export_parser import branched_conversation


class OpenAISyncSecurityTests(unittest.TestCase):
    def archive(self, members):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "export.zip"
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in members.items():
                archive.writestr(name, content)
        return path

    def test_download_url_requires_https_approved_host_and_public_dns(self):
        with patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("8.8.8.8", 443))]):
            self.assertTrue(validate_export_url("https://files.openai.com/export.zip").valid)
            self.assertFalse(validate_export_url("http://files.openai.com/export.zip").valid)
            self.assertFalse(validate_export_url("https://openai.example/export.zip").valid)
        with patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 443))]):
            result = validate_export_url("https://files.openai.com/export.zip")
            self.assertEqual("private_network_blocked", result.code)

    def test_safe_archive_passes(self):
        path = self.archive({"conversations.json": json.dumps([branched_conversation()])})
        self.assertTrue(validate_archive_for_extraction(path).valid)

    def test_zip_traversal_and_executables_are_blocked(self):
        traversal = self.archive({"conversations.json": "[]", "../escape.txt": "bad"})
        executable = self.archive({"conversations.json": "[]", "payload.exe": "bad"})
        self.assertEqual("path_traversal", validate_archive_for_extraction(traversal).code)
        self.assertEqual("executable_rejected", validate_archive_for_extraction(executable).code)


if __name__ == "__main__":
    unittest.main()
