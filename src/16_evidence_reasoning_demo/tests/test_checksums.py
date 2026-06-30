# tests/test_checksums.py
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from evidence_reasoning_demo.checksums import (  # noqa: E402
    format_checksums, parse_checksums, REQUIRED_KEYS)
from evidence_reasoning_demo.errors import VerifyError  # noqa: E402

H = ["%064x" % i for i in (1, 2, 3, 4, 5)]


def _good_text():
    return format_checksums(
        demo_report_sha256=H[0], demo_steps_sha256=H[1],
        aletheia_manifest_sha256=H[2], bridge_report_sha256=H[3],
        odin_reasoning_report_sha256=H[4]).decode()


class TestChecksums(unittest.TestCase):
    def test_20_format_roundtrip(self):
        m = parse_checksums(_good_text())
        self.assertEqual(set(m.keys()), set(REQUIRED_KEYS))

    def test_duplicate_key_fails(self):
        text = _good_text()
        first = text.splitlines()[0]
        with self.assertRaises(VerifyError):
            parse_checksums(text + first + "\n")

    def test_unknown_key_fails(self):
        text = _good_text() + f"{H[0]}  surprise.json\n"
        with self.assertRaises(VerifyError):
            parse_checksums(text)

    def test_malformed_digest_fails(self):
        text = _good_text().replace(H[0], "nothex")
        with self.assertRaises(VerifyError):
            parse_checksums(text)

    def test_missing_key_fails(self):
        text = "\n".join(_good_text().splitlines()[:-1]) + "\n"
        with self.assertRaises(VerifyError):
            parse_checksums(text)

    def test_uppercase_digest_rejected(self):
        text = _good_text().replace(H[0], "A" * 64)
        with self.assertRaises(VerifyError):
            parse_checksums(text)

    def test_blank_lines_tolerated(self):
        text = "\n" + _good_text() + "\n"
        self.assertEqual(len(parse_checksums(text)), 5)


if __name__ == "__main__":
    unittest.main()
