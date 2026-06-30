import os

from atlas_release_gate_lib import checksums, canonical
from atlas_release_gate_lib.errors import VerifyError
from tests._helpers import TempCase

_PATHS = list(checksums.REQUIRED_PATHS)


def _line(digest, path):
    return "%s  %s" % (digest, path)


_VALID = "a" * 64


class TestChecksums(TempCase):
    def test_checksums_written(self):
        out_dir, _ = self.run_gate()
        text = canonical.read_bytes(
            os.path.join(out_dir, "atlas_release_gate_checksums.txt")).decode()
        self.assertIn("atlas_release_gate_report.json", text)
        self.assertIn("atlas_export/atlas_summary.json", text)

    def test_parse_round_trip(self):
        out_dir, _ = self.run_gate()
        listed = checksums.verify_checksums(out_dir, _PATHS)
        self.assertEqual(set(listed), set(_PATHS))

    def test_duplicate_key_fails(self):
        text = "\n".join([_line(_VALID, p) for p in _PATHS] +
                         [_line(_VALID, _PATHS[0])])
        with self.assertRaises(VerifyError):
            checksums.parse_checksums(text, _PATHS)

    def test_unknown_key_fails(self):
        text = "\n".join([_line(_VALID, p) for p in _PATHS] +
                         [_line(_VALID, "atlas_export/extra.json")])
        with self.assertRaises(VerifyError):
            checksums.parse_checksums(text, _PATHS)

    def test_missing_key_fails(self):
        text = "\n".join(_line(_VALID, p) for p in _PATHS[:-1])
        with self.assertRaises(VerifyError):
            checksums.parse_checksums(text, _PATHS)

    def test_malformed_digest_fails(self):
        text = "\n".join([_line("zz", p) for p in _PATHS])
        with self.assertRaises(VerifyError):
            checksums.parse_checksums(text, _PATHS)

    def test_uppercase_digest_fails(self):
        text = "\n".join([_line("A" * 64, p) for p in _PATHS])
        with self.assertRaises(VerifyError):
            checksums.parse_checksums(text, _PATHS)

    def test_single_space_separator_fails(self):
        text = "\n".join(["%s %s" % (_VALID, p) for p in _PATHS])
        with self.assertRaises(VerifyError):
            checksums.parse_checksums(text, _PATHS)
