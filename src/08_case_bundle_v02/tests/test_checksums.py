# tests/test_checksums.py
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from case_bundle_v02_lib.checksums import (  # noqa: E402
    format_checksums, parse_checksums, REQUIRED_KEYS)
from case_bundle_v02_lib.errors import VerifyError  # noqa: E402


def _digests():
    return {key: "%064x" % (i + 1) for i, key in enumerate(REQUIRED_KEYS)}


def _good():
    return format_checksums(_digests()).decode()


class TestChecksums(unittest.TestCase):
    def test_roundtrip(self):
        m = parse_checksums(_good())
        self.assertEqual(set(m.keys()), set(REQUIRED_KEYS))
        self.assertEqual(len(m), 14)

    def test_duplicate_key_fails(self):
        first = _good().splitlines()[0]
        with self.assertRaises(VerifyError):
            parse_checksums(_good() + first + "\n")

    def test_unknown_key_fails(self):
        with self.assertRaises(VerifyError):
            parse_checksums(_good() + f"{'a' * 64}  surprise.json\n")

    def test_missing_key_fails(self):
        text = "\n".join(_good().splitlines()[:-1]) + "\n"
        with self.assertRaises(VerifyError):
            parse_checksums(text)

    def test_malformed_digest_fails(self):
        text = _good().replace("%064x" % 1, "nothex")
        with self.assertRaises(VerifyError):
            parse_checksums(text)

    def test_uppercase_digest_fails(self):
        text = _good().replace("%064x" % 1, "A" * 64)
        with self.assertRaises(VerifyError):
            parse_checksums(text)

    def test_blank_lines_tolerated(self):
        self.assertEqual(len(parse_checksums("\n" + _good() + "\n")), 14)


if __name__ == "__main__":
    unittest.main()
