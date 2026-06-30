# tests/test_verify_bundle.py
import json
import os
import shutil
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from aletheia_evidence.verifier import verify_bundle  # noqa: E402
from aletheia_evidence.canonical import canonical_bytes  # noqa: E402
from aletheia_evidence.errors import VerifyError  # noqa: E402
from aletheia_evidence import versions  # noqa: E402
from tests.helpers import make_bundle  # noqa: E402


def _rewrite_manifest(bundle, mutate):
    p = os.path.join(bundle, "evidence_manifest.json")
    with open(p, "rb") as f:
        obj = json.loads(f.read().decode())
    mutate(obj)
    with open(p, "wb") as f:
        f.write(canonical_bytes(obj))


class TestVerifyBundle(unittest.TestCase):
    def test_13_verify_valid_bundle_succeeds(self):
        bundle, _ = make_bundle()
        r = verify_bundle(bundle)
        self.assertEqual(r.evidence_status, versions.EVIDENCE_VERIFIED_PRESENT)

    def test_14_mutated_evidence_file_fails(self):
        bundle, _ = make_bundle()
        with open(os.path.join(bundle, "evidence", "evidence_001.bin"), "wb") as f:
            f.write(b"TAMPERED")
        with self.assertRaises(VerifyError) as cm:
            verify_bundle(bundle)
        self.assertEqual(cm.exception.status,
                         versions.EVIDENCE_FAILED_HASH_MISMATCH)

    def test_15_mutated_manifest_fails(self):
        bundle, _ = make_bundle()
        # Change a field but keep it canonical -> manifest hash no longer matches
        # the checksums file -> hash mismatch.
        _rewrite_manifest(bundle, lambda o: o.update(case_id="case_XXX"))
        with self.assertRaises(VerifyError):
            verify_bundle(bundle)

    def test_16_missing_evidence_file_fails(self):
        bundle, _ = make_bundle()
        os.remove(os.path.join(bundle, "evidence", "evidence_001.bin"))
        with self.assertRaises(VerifyError) as cm:
            verify_bundle(bundle)
        self.assertEqual(cm.exception.status,
                         versions.EVIDENCE_FAILED_MISSING_FILE)

    def test_17_missing_manifest_fails(self):
        bundle, _ = make_bundle()
        os.remove(os.path.join(bundle, "evidence_manifest.json"))
        with self.assertRaises(VerifyError) as cm:
            verify_bundle(bundle)
        self.assertEqual(cm.exception.status,
                         versions.EVIDENCE_FAILED_MISSING_FILE)

    def test_18_missing_checksums_fails(self):
        bundle, _ = make_bundle()
        os.remove(os.path.join(bundle, "evidence_checksums.txt"))
        with self.assertRaises(VerifyError) as cm:
            verify_bundle(bundle)
        self.assertEqual(cm.exception.status,
                         versions.EVIDENCE_FAILED_MISSING_FILE)

    def test_22_unknown_extra_file_fails(self):
        bundle, _ = make_bundle()
        with open(os.path.join(bundle, "rogue.txt"), "w") as f:
            f.write("x")
        with self.assertRaises(VerifyError) as cm:
            verify_bundle(bundle)
        self.assertEqual(cm.exception.status,
                         versions.EVIDENCE_FAILED_CHECKSUMS_INVALID)

    def test_unknown_extra_file_inside_evidence_dir_fails(self):
        bundle, _ = make_bundle()
        with open(os.path.join(bundle, "evidence", "extra.bin"), "w") as f:
            f.write("x")
        with self.assertRaises(VerifyError):
            verify_bundle(bundle)

    def test_23_manifest_source_hash_mismatch_fails(self):
        bundle, _ = make_bundle()
        # Make source != bundled (both valid sha256 shape) but keep checksums/
        # bundled-file consistent so we reach check 13.
        def mutate(o):
            o["source_file_sha256"] = "0" * 64
        _rewrite_manifest(bundle, mutate)
        # Recompute the manifest hash into checksums so we get past check 11/12
        # and specifically hit the source==bundled check (13).
        _resync_manifest_checksum(bundle)
        with self.assertRaises(VerifyError) as cm:
            verify_bundle(bundle)
        self.assertEqual(cm.exception.status,
                         versions.EVIDENCE_FAILED_HASH_MISMATCH)

    def test_24_manifest_bundled_hash_mismatch_fails(self):
        bundle, _ = make_bundle()
        def mutate(o):
            o["bundled_file_sha256"] = "0" * 64
            o["source_file_sha256"] = "0" * 64  # keep 13 happy; fail at 12
        _rewrite_manifest(bundle, mutate)
        _resync_manifest_checksum(bundle)
        with self.assertRaises(VerifyError) as cm:
            verify_bundle(bundle)
        self.assertEqual(cm.exception.status,
                         versions.EVIDENCE_FAILED_HASH_MISMATCH)

    def test_25_non_canonical_manifest_fails(self):
        bundle, _ = make_bundle()
        p = os.path.join(bundle, "evidence_manifest.json")
        with open(p, "rb") as f:
            obj = json.loads(f.read().decode())
        with open(p, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2)  # pretty -> non-canonical
        with self.assertRaises(VerifyError) as cm:
            verify_bundle(bundle)
        self.assertEqual(cm.exception.status,
                         versions.EVIDENCE_FAILED_NON_CANONICAL_MANIFEST)

    def test_missing_bundle_dir_fails(self):
        with self.assertRaises(VerifyError) as cm:
            verify_bundle("/no/such/bundle/dir")
        self.assertEqual(cm.exception.status,
                         versions.EVIDENCE_FAILED_MISSING_FILE)

    def test_26_verified_present_is_not_a_truth_claim(self):
        # The honest status set must not contain a "TRUE"/"AUTHENTIC" style value,
        # and the manifest's known_limitations must disclaim truth.
        bundle, _ = make_bundle()
        r = verify_bundle(bundle)
        self.assertEqual(r.evidence_status, "VERIFIED_PRESENT")
        self.assertNotIn("TRUE", r.evidence_status.upper().replace("VERIFIED", ""))
        with open(os.path.join(bundle, "evidence_manifest.json")) as f:
            manifest = json.load(f)
        self.assertTrue(any("does not prove the file contents are true" in k
                            for k in manifest["known_limitations"]))


def _resync_manifest_checksum(bundle):
    """Recompute the manifest hash line in the checksums file so verification
    proceeds past the checksum-vs-file checks to the manifest's internal hash
    checks. (Used only to target specific later checks in tests.)"""
    from aletheia_evidence.hashing import sha256_file
    from aletheia_evidence.checksums import MANIFEST_KEY, BUNDLED_KEY
    mp = os.path.join(bundle, "evidence_manifest.json")
    bp = os.path.join(bundle, "evidence", "evidence_001.bin")
    msha = sha256_file(mp)
    bsha = sha256_file(bp)
    with open(os.path.join(bundle, "evidence_checksums.txt"), "w",
              encoding="utf-8") as f:
        f.write(f"{msha}  {MANIFEST_KEY}\n{bsha}  {BUNDLED_KEY}\n")


if __name__ == "__main__":
    unittest.main()
