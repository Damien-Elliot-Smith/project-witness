# tests/test_validation.py
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from case_bundle_v02_lib.validation import (  # noqa: E402
    validate_id, is_safe_id, is_valid_sha256, scan_truth)
from case_bundle_v02_lib.errors import ValidationError, VerifyError  # noqa: E402


class TestValidation(unittest.TestCase):
    def test_valid_id_accepted(self):
        self.assertEqual(validate_id("case_001", label="case_id"), "case_001")
        self.assertTrue(is_safe_id("case_83cd1ba75eddfa05"))

    def test_unsafe_id_refused(self):
        for bad in ("../evil", "a/b", "..", ".", "-rf", "", "x" * 129):
            self.assertFalse(is_safe_id(bad))
            with self.assertRaises(ValidationError):
                validate_id(bad, label="case_id")

    def test_sha256_validator(self):
        self.assertTrue(is_valid_sha256("a" * 64))
        self.assertFalse(is_valid_sha256("A" * 64))
        self.assertFalse(is_valid_sha256("a" * 63))

    def test_scan_truth_allows_disclaimers(self):
        # The honest negated disclaimers must NOT trip the scan.
        scan_truth("It does not prove evidence contents are true.", "x")
        scan_truth("It does not prove ODIN claims are true.", "x")
        scan_truth("This import records ODIN structural reasoning metadata only. "
                   "It does not prove that any claim is true.", "x")

    def test_scan_truth_catches_affirmative(self):
        for bad in ("the evidence_is_true", "claims_are_true now",
                    "file.authentic confirmed", "this proves reality"):
            with self.assertRaises(VerifyError):
                scan_truth(bad, "x")


if __name__ == "__main__":
    unittest.main()
