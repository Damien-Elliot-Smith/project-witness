from coordinator_v03_lib import checksums
from coordinator_v03_lib.errors import VerifyError
from tests._helpers import TempCase

_PATHS = list(checksums.REQUIRED_PATHS)
_VALID = "a" * 64


def _line(d, p):
    return "%s  %s" % (d, p)


class TestChecksums(TempCase):
    def test_round_trip(self):
        out, _ = self.run_wf()
        listed = checksums.verify_checksums(out, checksums.present_paths(out))
        self.assertEqual(set(listed), set(checksums.present_paths(out)))

    def test_missing_key_fails(self):
        text = "\n".join(_line(_VALID, p) for p in _PATHS[:-1])
        with self.assertRaises(VerifyError):
            checksums.parse_checksums(text, _PATHS)

    def test_duplicate_key_fails(self):
        text = "\n".join([_line(_VALID, p) for p in _PATHS] + [_line(_VALID, _PATHS[0])])
        with self.assertRaises(VerifyError):
            checksums.parse_checksums(text, _PATHS)

    def test_unknown_key_fails(self):
        text = "\n".join([_line(_VALID, p) for p in _PATHS] + [_line(_VALID, "nope.json")])
        with self.assertRaises(VerifyError):
            checksums.parse_checksums(text, _PATHS)

    def test_malformed_digest_fails(self):
        with self.assertRaises(VerifyError):
            checksums.parse_checksums("\n".join(_line("zz", p) for p in _PATHS), _PATHS)

    def test_uppercase_digest_fails(self):
        with self.assertRaises(VerifyError):
            checksums.parse_checksums("\n".join(_line("A"*64, p) for p in _PATHS), _PATHS)
