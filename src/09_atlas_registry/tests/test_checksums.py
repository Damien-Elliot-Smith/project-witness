# tests/test_checksums.py
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from atlas_registry_lib.checksums import (  # noqa: E402
    format_checksums, parse_checksums, REQUIRED_KEYS)
from atlas_registry_lib.errors import ExportError  # noqa: E402
from atlas_registry_lib import versions  # noqa: E402
from tests.helpers import good_export  # noqa: E402


def _digests():
    return {key: "%064x" % (i + 1) for i, key in enumerate(REQUIRED_KEYS)}


def _good():
    return format_checksums(_digests()).decode()


class TestChecksums(unittest.TestCase):
    def test_roundtrip_two_keys(self):
        m = parse_checksums(_good())
        self.assertEqual(set(m.keys()), set(REQUIRED_KEYS))
        self.assertEqual(len(m), 2)

    def test_33_duplicate_key_fails(self):
        first = _good().splitlines()[0]
        with self.assertRaises(ExportError):
            parse_checksums(_good() + first + "\n")

    def test_34_unknown_key_fails(self):
        with self.assertRaises(ExportError):
            parse_checksums(_good() + f"{'a' * 64}  surprise.json\n")

    def test_missing_key_fails(self):
        text = _good().splitlines()[0] + "\n"
        with self.assertRaises(ExportError):
            parse_checksums(text)

    def test_35_malformed_digest_fails(self):
        with self.assertRaises(ExportError):
            parse_checksums(_good().replace("%064x" % 1, "nothex"))

    def test_36_uppercase_digest_fails(self):
        with self.assertRaises(ExportError):
            parse_checksums(_good().replace("%064x" % 1, "A" * 64))

    def test_real_export_checksums_parse(self):
        out = good_export()
        with open(os.path.join(out, versions.EXPORT_CHECKSUMS),
                  encoding="utf-8") as f:
            m = parse_checksums(f.read())
        self.assertEqual(set(m.keys()), set(REQUIRED_KEYS))


if __name__ == "__main__":
    unittest.main()
