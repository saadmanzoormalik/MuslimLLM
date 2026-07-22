import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.auth.email_codes import normalize_email
from app.auth.security import numeric_code, token_hash


class EmailAuthTests(unittest.TestCase):
    def test_code_shape_randomness_and_hashing(self):
        codes = {numeric_code() for _ in range(100)}
        self.assertGreater(len(codes), 95)
        self.assertTrue(all(len(code) == 6 and code.isdigit() for code in codes))
        code = next(iter(codes))
        self.assertNotIn(code, token_hash(f"person@example.com:{code}"))

    def test_email_normalization(self):
        self.assertEqual(normalize_email("Person@EXAMPLE.COM"), "person@example.com")


if __name__ == "__main__": unittest.main()
