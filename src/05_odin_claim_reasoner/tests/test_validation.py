# tests/test_validation.py
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from odin_reasoner.validation import validate_id, is_safe_id, is_valid_sha256  # noqa: E402
from odin_reasoner.errors import ValidationError  # noqa: E402


class TestIdValidation(unittest.TestCase):
    def test_valid_ids_accepted(self):
        for good in ("case_001", "claim_001", "support_1", "a.b-c_d"):
            self.assertEqual(validate_id(good, label="id"), good)
            self.assertTrue(is_safe_id(good))

    def test_5_unsafe_claim_id_refused(self):
        for bad in ("../evil", "a/b", "a\\b", "..", ".", "-rf", ".hidden", "",
                    "a b", "a\x00b", "a\nb", "x" * 129):
            self.assertFalse(is_safe_id(bad))
            with self.assertRaises(ValidationError):
                validate_id(bad, label="claim_id")

    def test_6_unsafe_support_id_refused(self):
        for bad in ("../s", "s/x", ".s", "-s"):
            with self.assertRaises(ValidationError):
                validate_id(bad, label="support_id")

    def test_non_string_id_refused(self):
        for bad in (123, None, ["x"]):
            self.assertFalse(is_safe_id(bad))

    def test_sha256_validator(self):
        self.assertTrue(is_valid_sha256("a" * 64))
        self.assertFalse(is_valid_sha256("A" * 64))  # uppercase rejected
        self.assertFalse(is_valid_sha256("a" * 63))
        self.assertFalse(is_valid_sha256("g" * 64))
        self.assertFalse(is_valid_sha256(123))


if __name__ == "__main__":
    unittest.main()
