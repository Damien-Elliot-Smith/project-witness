from unified_manifest_lib import checksums, versions
from unified_manifest_lib.errors import VerifyError
from tests._helpers import TempCase

_PATHS = list(checksums.REQUIRED_PATHS)
_V = "a" * 64


def _line(d, p):
    return "%s  %s" % (d, p)


class TestChecksums(TempCase):
    def test_round_trip(self):
        out = self.build_output(versions.SOURCE_TYPE_COORDINATOR, self.coord_source())
        listed = checksums.verify_checksums(out)
        self.assertEqual(set(listed), set(_PATHS))

    def test_missing_key_fails(self):
        with self.assertRaises(VerifyError):
            checksums.parse_checksums(_line(_V, _PATHS[0]))

    def test_duplicate_key_fails(self):
        text = "\n".join([_line(_V, p) for p in _PATHS] + [_line(_V, _PATHS[0])])
        with self.assertRaises(VerifyError):
            checksums.parse_checksums(text)

    def test_unknown_key_fails(self):
        text = "\n".join([_line(_V, p) for p in _PATHS] + [_line(_V, "extra.json")])
        with self.assertRaises(VerifyError):
            checksums.parse_checksums(text)

    def test_malformed_digest_fails(self):
        with self.assertRaises(VerifyError):
            checksums.parse_checksums("\n".join(_line("zz", p) for p in _PATHS))

    def test_uppercase_digest_fails(self):
        with self.assertRaises(VerifyError):
            checksums.parse_checksums("\n".join(_line("A" * 64, p) for p in _PATHS))
