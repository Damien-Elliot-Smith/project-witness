# tests/test_validation.py
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from aletheia_evidence.validation import (  # noqa: E402
    validate_id, is_safe_id, validate_source_file)
from aletheia_evidence.errors import ValidationError  # noqa: E402
from aletheia_evidence import versions  # noqa: E402


class TestIdValidation(unittest.TestCase):
    def test_1_valid_case_id_accepted(self):
        for good in ("case_001", "a", "a.b-c_d", "Case123"):
            self.assertEqual(validate_id(good, label="case_id"), good)

    def test_2_unsafe_case_id_refused(self):
        for bad in ("../evil", "a/b", "a\\b", "..", ".", "-rf", ".hidden",
                    "", "a b", "a\x00b", "a\nb", "x" * 129):
            with self.assertRaises(ValidationError):
                validate_id(bad, label="case_id")

    def test_3_valid_evidence_id_accepted(self):
        self.assertEqual(validate_id("evidence_001", label="evidence_id"),
                         "evidence_001")

    def test_4_unsafe_evidence_id_refused(self):
        for bad in ("../x", "e/v", ".e", "-e", "e\x7f"):
            self.assertFalse(is_safe_id(bad))
            with self.assertRaises(ValidationError):
                validate_id(bad, label="evidence_id")


class TestSourceFileValidation(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def test_5_missing_source_refused(self):
        with self.assertRaises(ValidationError) as cm:
            validate_source_file(os.path.join(self.d, "nope.txt"))
        self.assertEqual(cm.exception.reason, "MISSING_FILE")

    def test_6_directory_source_refused(self):
        with self.assertRaises(ValidationError) as cm:
            validate_source_file(self.d)
        self.assertEqual(cm.exception.reason, "DIRECTORY_SOURCE")

    def test_7_symlink_source_refused(self):
        target = os.path.join(self.d, "real.txt")
        with open(target, "w") as f:
            f.write("x")
        link = os.path.join(self.d, "link.txt")
        os.symlink(target, link)
        with self.assertRaises(ValidationError) as cm:
            validate_source_file(link)
        self.assertEqual(cm.exception.reason, "SYMLINK_SOURCE")

    def test_8_oversized_source_refused(self):
        big = os.path.join(self.d, "big.bin")
        with open(big, "wb") as f:
            f.write(b"\0" * (versions.MAX_EVIDENCE_BYTES + 1))
        with self.assertRaises(ValidationError) as cm:
            validate_source_file(big)
        self.assertEqual(cm.exception.reason, "FILE_TOO_LARGE")

    def test_valid_source_returns_size(self):
        p = os.path.join(self.d, "ok.txt")
        with open(p, "wb") as f:
            f.write(b"12345")
        self.assertEqual(validate_source_file(p), 5)


if __name__ == "__main__":
    unittest.main()
