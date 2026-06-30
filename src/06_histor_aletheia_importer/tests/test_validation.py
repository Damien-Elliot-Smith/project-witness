# tests/test_validation.py
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from histor_aletheia_importer.validation import (  # noqa: E402
    validate_id, is_safe_id, is_valid_sha256)
from histor_aletheia_importer.errors import ValidationError  # noqa: E402


class TestValidation(unittest.TestCase):
    def test_valid_ids_accepted(self):
        self.assertEqual(validate_id("case_001", label="case_id"), "case_001")
        self.assertEqual(validate_id("evidence_001", label="evidence_id"),
                         "evidence_001")

    def test_7_invalid_case_id_refused(self):
        for bad in ("../evil", "a/b", "..", ".", "-rf", ".hidden", "", "a b",
                    "a\x00b", "x" * 129):
            self.assertFalse(is_safe_id(bad))
            with self.assertRaises(ValidationError):
                validate_id(bad, label="case_id")

    def test_8_invalid_evidence_id_refused(self):
        for bad in ("../x", "e/v", ".e", "-e", "e\x7f"):
            with self.assertRaises(ValidationError):
                validate_id(bad, label="evidence_id")

    def test_sha256_validator(self):
        self.assertTrue(is_valid_sha256("a" * 64))
        self.assertFalse(is_valid_sha256("A" * 64))   # uppercase rejected
        self.assertFalse(is_valid_sha256("a" * 63))
        self.assertFalse(is_valid_sha256("g" * 64))
        self.assertFalse(is_valid_sha256(123))


if __name__ == "__main__":
    unittest.main()
