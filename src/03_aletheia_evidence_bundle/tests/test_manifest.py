# tests/test_manifest.py
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from aletheia_evidence.manifest import (  # noqa: E402
    build_manifest, validate_manifest_shape, MANIFEST_FIELDS)
from aletheia_evidence.errors import VerifyError  # noqa: E402
from aletheia_evidence import versions  # noqa: E402

H = "a" * 64


def _good_manifest():
    return build_manifest(
        case_id="case_001", evidence_id="evidence_001",
        source_file_name="input.txt", source_file_size_bytes=15,
        source_file_sha256=H, bundled_file_sha256=H,
        created_at_utc="2026-01-01T00:00:00Z")


class TestManifest(unittest.TestCase):
    def test_build_manifest_fields(self):
        m = _good_manifest()
        self.assertEqual(set(m.keys()), set(MANIFEST_FIELDS))
        self.assertEqual(m["aletheia_evidence_bundle_version"], "0.1.0")
        self.assertEqual(m["evidence_status"], "VERIFIED_PRESENT")
        self.assertEqual(m["bundled_file_path"], "evidence/evidence_001.bin")

    def test_valid_manifest_passes_shape(self):
        validate_manifest_shape(_good_manifest())  # must not raise

    def test_missing_field_fails(self):
        m = _good_manifest()
        del m["case_id"]
        with self.assertRaises(VerifyError) as cm:
            validate_manifest_shape(m)
        self.assertEqual(cm.exception.status,
                         versions.EVIDENCE_FAILED_MANIFEST_INVALID)

    def test_unknown_field_fails(self):
        m = _good_manifest()
        m["surprise"] = 1
        with self.assertRaises(VerifyError):
            validate_manifest_shape(m)

    def test_bad_sha_field_fails(self):
        m = _good_manifest()
        m["source_file_sha256"] = "nothex"
        with self.assertRaises(VerifyError):
            validate_manifest_shape(m)

    def test_bad_size_fails(self):
        m = _good_manifest()
        m["source_file_size_bytes"] = -1
        with self.assertRaises(VerifyError):
            validate_manifest_shape(m)

    def test_non_present_status_fails(self):
        m = _good_manifest()
        m["evidence_status"] = "FAILED_HASH_MISMATCH"
        with self.assertRaises(VerifyError):
            validate_manifest_shape(m)

    def test_known_limitations_disclaims_truth(self):
        m = _good_manifest()
        self.assertTrue(any("not prove the file contents are true" in k
                            for k in m["known_limitations"]))


if __name__ == "__main__":
    unittest.main()
