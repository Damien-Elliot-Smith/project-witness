# tests/test_checksums.py
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from histor_aletheia_importer.checksums import (  # noqa: E402
    format_checksums, parse_checksums, REQUIRED_KEYS, SUMMARY_KEY)
from histor_aletheia_importer.errors import VerifyError  # noqa: E402

H = ["%064x" % i for i in (1, 2, 3)]


def _good():
    return format_checksums(summary_sha256=H[0], manifest_copy_sha256=H[1],
                            replay_report_sha256=H[2]).decode()


class TestChecksums(unittest.TestCase):
    def test_roundtrip(self):
        m = parse_checksums(_good())
        self.assertEqual(set(m.keys()), set(REQUIRED_KEYS))

    def test_duplicate_key_fails(self):
        first = _good().splitlines()[0]
        with self.assertRaises(VerifyError):
            parse_checksums(_good() + first + "\n")

    def test_unknown_key_fails(self):
        with self.assertRaises(VerifyError):
            parse_checksums(_good() + f"{H[0]}  surprise.json\n")

    def test_missing_key_fails(self):
        text = "\n".join(_good().splitlines()[:-1]) + "\n"
        with self.assertRaises(VerifyError):
            parse_checksums(text)

    def test_malformed_digest_fails(self):
        with self.assertRaises(VerifyError):
            parse_checksums(_good().replace(H[0], "nothex"))

    def test_uppercase_digest_fails(self):
        with self.assertRaises(VerifyError):
            parse_checksums(_good().replace(H[0], "A" * 64))

    def test_blank_lines_tolerated(self):
        self.assertEqual(len(parse_checksums("\n" + _good() + "\n")), 3)


if __name__ == "__main__":
    unittest.main()
