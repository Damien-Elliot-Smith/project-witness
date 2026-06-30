# tests/test_checksums.py
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from aletheia_evidence.checksums import (  # noqa: E402
    parse_checksums, format_checksums, MANIFEST_KEY, BUNDLED_KEY)
from aletheia_evidence.errors import VerifyError  # noqa: E402
from aletheia_evidence import versions  # noqa: E402

H = "a" * 64
H2 = "b" * 64


class TestChecksums(unittest.TestCase):
    def test_format_roundtrip(self):
        data = format_checksums(manifest_sha256=H, bundled_sha256=H2).decode()
        m = parse_checksums(data)
        self.assertEqual(m[MANIFEST_KEY], H)
        self.assertEqual(m[BUNDLED_KEY], H2)

    def test_19_duplicate_key_fails(self):
        text = (f"{H}  {MANIFEST_KEY}\n{H}  {MANIFEST_KEY}\n"
                f"{H2}  {BUNDLED_KEY}\n")
        with self.assertRaises(VerifyError) as cm:
            parse_checksums(text)
        self.assertEqual(cm.exception.status,
                         versions.EVIDENCE_FAILED_CHECKSUMS_INVALID)

    def test_20_unknown_key_fails(self):
        text = (f"{H}  {MANIFEST_KEY}\n{H2}  {BUNDLED_KEY}\n"
                f"{H}  surprise.txt\n")
        with self.assertRaises(VerifyError):
            parse_checksums(text)

    def test_21_malformed_digest_fails(self):
        text = f"xyz  {MANIFEST_KEY}\n{H2}  {BUNDLED_KEY}\n"
        with self.assertRaises(VerifyError):
            parse_checksums(text)

    def test_missing_key_fails(self):
        text = f"{H}  {MANIFEST_KEY}\n"
        with self.assertRaises(VerifyError):
            parse_checksums(text)

    def test_malformed_line_fails(self):
        text = f"{H} only-one-space-and-missing\n{H2}  {BUNDLED_KEY}\n"
        with self.assertRaises(VerifyError):
            parse_checksums(text)

    def test_blank_lines_tolerated(self):
        text = f"\n{H}  {MANIFEST_KEY}\n\n{H2}  {BUNDLED_KEY}\n\n"
        m = parse_checksums(text)
        self.assertEqual(len(m), 2)

    def test_uppercase_digest_rejected(self):
        text = f"{'A'*64}  {MANIFEST_KEY}\n{H2}  {BUNDLED_KEY}\n"
        with self.assertRaises(VerifyError):
            parse_checksums(text)


if __name__ == "__main__":
    unittest.main()
