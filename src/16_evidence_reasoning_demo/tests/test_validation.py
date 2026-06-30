# tests/test_validation.py
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from evidence_reasoning_demo.validation import (  # noqa: E402
    validate_id, is_safe_id, validate_source_file)
from evidence_reasoning_demo.errors import ValidationError  # noqa: E402


class TestValidation(unittest.TestCase):
    def test_1_valid_ids_accepted(self):
        self.assertEqual(validate_id("case_001", label="case_id"), "case_001")
        self.assertEqual(validate_id("evidence_001", label="evidence_id"),
                         "evidence_001")

    def test_2_unsafe_case_id_refused(self):
        for bad in ("../evil", "a/b", "..", ".", "-rf", ".hidden", "", "a b",
                    "a\x00b", "x" * 129):
            self.assertFalse(is_safe_id(bad))
            with self.assertRaises(ValidationError):
                validate_id(bad, label="case_id")

    def test_3_unsafe_evidence_id_refused(self):
        for bad in ("../x", "e/v", ".e", "-e"):
            with self.assertRaises(ValidationError):
                validate_id(bad, label="evidence_id")

    def test_4_missing_evidence_file_refused(self):
        with self.assertRaises(ValidationError) as cm:
            validate_source_file("/no/such/file.txt")
        self.assertEqual(cm.exception.reason, "MISSING_FILE")

    def test_5_directory_evidence_source_refused(self):
        d = tempfile.mkdtemp()
        with self.assertRaises(ValidationError) as cm:
            validate_source_file(d)
        self.assertEqual(cm.exception.reason, "DIRECTORY_SOURCE")

    def test_6_symlink_evidence_source_refused(self):
        d = tempfile.mkdtemp()
        target = os.path.join(d, "real.txt")
        with open(target, "w") as f:
            f.write("x")
        link = os.path.join(d, "link.txt")
        os.symlink(target, link)
        with self.assertRaises(ValidationError) as cm:
            validate_source_file(link)
        self.assertEqual(cm.exception.reason, "SYMLINK_SOURCE")

    def test_valid_source_accepted(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "ok.txt")
        with open(p, "w") as f:
            f.write("hello")
        validate_source_file(p)  # must not raise


if __name__ == "__main__":
    unittest.main()
