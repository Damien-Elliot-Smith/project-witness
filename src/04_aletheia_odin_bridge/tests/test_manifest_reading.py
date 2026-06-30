# tests/test_manifest_reading.py
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from aletheia_odin_bridge.aletheia_reader import (  # noqa: E402
    read_manifest, validate_manifest, require_verified_present)
from aletheia_odin_bridge.errors import ManifestError  # noqa: E402
from tests.helpers import manifest, make_bundle_dir  # noqa: E402


class TestManifestReading(unittest.TestCase):
    def test_1_valid_manifest_accepted(self):
        m = validate_manifest(manifest())
        self.assertEqual(m["evidence_id"], "evidence_001")
        require_verified_present(m)  # must not raise

    def test_2_missing_field_refused(self):
        with self.assertRaises(ManifestError) as cm:
            validate_manifest(manifest(drop=["bundled_file_sha256"]))
        self.assertEqual(cm.exception.reason, "MANIFEST_FIELD_MISSING")

    def test_3_extra_field_tolerated_by_subset_validation(self):
        # The bridge validates the subset of fields it relies on; an unknown extra
        # field on the *source* manifest is tolerated (the copy is hashed verbatim
        # and re-checked canonically by verify). This documents the boundary.
        m = validate_manifest(manifest(extra={"surprise": 1}))
        self.assertEqual(m["surprise"], 1)

    def test_4_non_verified_present_refused(self):
        for bad in ("FAILED_HASH_MISMATCH", "FAILED_MISSING_FILE", "BUNDLED"):
            m = validate_manifest(manifest(evidence_status=bad))
            with self.assertRaises(ManifestError) as cm:
                require_verified_present(m)
            self.assertEqual(cm.exception.reason, "STATUS_NOT_VERIFIED_PRESENT")

    def test_missing_manifest_file_refused(self):
        import tempfile
        empty = tempfile.mkdtemp()
        with self.assertRaises(ManifestError) as cm:
            read_manifest(empty)
        self.assertEqual(cm.exception.reason, "MANIFEST_MISSING")

    def test_malformed_manifest_refused(self):
        import tempfile
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "evidence_manifest.json"), "w") as f:
            f.write("{not json")
        with self.assertRaises(ManifestError) as cm:
            read_manifest(d)
        self.assertEqual(cm.exception.reason, "MANIFEST_MALFORMED")

    def test_unsafe_evidence_id_refused(self):
        with self.assertRaises(ManifestError) as cm:
            validate_manifest(manifest(evidence_id="../evil"))
        self.assertEqual(cm.exception.reason, "MANIFEST_ID_UNSAFE")

    def test_bad_sha_refused(self):
        with self.assertRaises(ManifestError) as cm:
            validate_manifest(manifest(sha="nothex"))
        self.assertEqual(cm.exception.reason, "MANIFEST_SHA256_INVALID")

    def test_read_manifest_from_bundle_dir(self):
        d = make_bundle_dir(manifest())
        m = read_manifest(d)
        self.assertEqual(m["case_id"], "case_001")


if __name__ == "__main__":
    unittest.main()
