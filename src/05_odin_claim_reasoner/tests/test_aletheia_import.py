# tests/test_aletheia_import.py
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from odin_reasoner.aletheia_import import build_claims_from_manifest  # noqa: E402
from odin_reasoner.claims import validate_claim_set  # noqa: E402
from odin_reasoner.errors import ImportError_  # noqa: E402


def _manifest(status="VERIFIED_PRESENT"):
    sha = "a" * 64
    return {
        "aletheia_evidence_bundle_version": "0.1.0",
        "case_id": "case_001",
        "evidence_id": "evidence_001",
        "source_file_name": "input.txt",
        "source_file_size_bytes": 15,
        "source_file_sha256": sha,
        "bundled_file_path": "evidence/evidence_001.bin",
        "bundled_file_sha256": sha,
        "bundle_status": "BUNDLED",
        "evidence_status": status,
        "created_at_utc": "2026-01-01T00:00:00Z",
        "known_limitations": ["..."],
    }


class TestAletheiaImport(unittest.TestCase):
    def test_29_import_creates_only_integrity_claims(self):
        cs = build_claims_from_manifest(_manifest())
        validate_claim_set(cs)  # importable result must be a valid claim set
        predicates = [c["predicate"] for c in cs["claims"]]
        self.assertEqual(predicates, ["evidence.present",
                                      "evidence.integrity_verified"])
        # No claim asserts anything about contents being true.
        for c in cs["claims"]:
            self.assertNotIn("true", c["predicate"].lower())
            self.assertNotIn("content", c["predicate"].lower())
            self.assertEqual(c["subject"], "evidence:evidence_001")
            self.assertEqual(c["polarity"], "AFFIRMED")

    def test_30_import_refuses_non_verified_present(self):
        for bad in ("FAILED_HASH_MISMATCH", "FAILED_MISSING_FILE", "BUNDLED",
                    "SOMETHING"):
            with self.assertRaises(ImportError_) as cm:
                build_claims_from_manifest(_manifest(bad))
            self.assertEqual(cm.exception.reason, "MANIFEST_NOT_VERIFIED_PRESENT")

    def test_import_support_references_preserved(self):
        cs = build_claims_from_manifest(_manifest())
        for c in cs["claims"]:
            s = c["support"][0]
            self.assertEqual(s["source_component"], "aletheia_evidence_bundle")
            self.assertEqual(s["source_id"], "evidence_001")
            self.assertEqual(s["source_sha256"], "a" * 64)

    def test_import_refuses_missing_field(self):
        m = _manifest()
        del m["bundled_file_sha256"]
        with self.assertRaises(ImportError_) as cm:
            build_claims_from_manifest(m)
        self.assertEqual(cm.exception.reason, "MANIFEST_FIELD_MISSING")

    def test_import_refuses_unsafe_evidence_id(self):
        m = _manifest()
        m["evidence_id"] = "../evil"
        with self.assertRaises(ImportError_) as cm:
            build_claims_from_manifest(m)
        self.assertEqual(cm.exception.reason, "UNSAFE_EVIDENCE_ID")

    def test_import_refuses_bad_sha(self):
        m = _manifest()
        m["bundled_file_sha256"] = "nothex"
        with self.assertRaises(ImportError_) as cm:
            build_claims_from_manifest(m)
        self.assertEqual(cm.exception.reason, "INVALID_SHA256")


if __name__ == "__main__":
    unittest.main()
