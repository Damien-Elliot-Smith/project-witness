# tests/test_verify.py
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from case_bundle_v02_lib.verifier import verify_bundle  # noqa: E402
from case_bundle_v02_lib.canonical import canonical_bytes  # noqa: E402
from case_bundle_v02_lib.validation import sha256_file  # noqa: E402
from case_bundle_v02_lib.checksums import (  # noqa: E402
    format_checksums, REQUIRED_KEYS, MANIFEST_KEY)
from case_bundle_v02_lib.errors import VerifyError  # noqa: E402
from case_bundle_v02_lib import versions  # noqa: E402
from tests.helpers import (  # noqa: E402
    good_bundle, make_odin_case, make_aletheia_case)


def _rewrite_manifest(bundle, mutate):
    p = os.path.join(bundle, versions.MANIFEST_NAME)
    with open(p, "rb") as f:
        obj = json.loads(f.read().decode())
    mutate(obj)
    with open(p, "wb") as f:
        f.write(canonical_bytes(obj))


def _resync(bundle):
    """Recompute bundle_checksums.txt to match current files."""
    digests = {}
    for key in REQUIRED_KEYS:
        digests[key] = sha256_file(os.path.join(bundle, key))
    with open(os.path.join(bundle, versions.CHECKSUMS_NAME), "wb") as f:
        f.write(format_checksums(digests))


def _resync_odin_internal(bundle):
    """Recompute the ODIN subcase's own checksums.txt (2-token format)."""
    odin_dir = os.path.join(bundle, versions.ODIN_DIR)
    names = [versions.ODIN_SUMMARY, versions.ODIN_REPORT_COPY,
             versions.ODIN_TRACE_COPY, versions.ODIN_CLAIMS_COPY,
             versions.ODIN_REPLAY]
    lines = [f"{sha256_file(os.path.join(odin_dir, n))}  {n}" for n in names]
    with open(os.path.join(odin_dir, versions.ODIN_CHECKSUMS), "wb") as f:
        f.write(("\n".join(lines) + "\n").encode("utf-8"))


SENT = versions.SENTINEL_DIR
ALE = versions.ALETHEIA_DIR
ODIN = versions.ODIN_DIR


class TestVerify(unittest.TestCase):
    def test_16_verify_valid_bundle_succeeds(self):
        r = verify_bundle(good_bundle())
        self.assertEqual(r.bundle_status, "BUNDLED_VERIFIED_CASE")

    def test_17_mutated_manifest_fails(self):
        b = good_bundle()
        with open(os.path.join(b, versions.MANIFEST_NAME), "ab") as f:
            f.write(b" ")
        with self.assertRaises(VerifyError):
            verify_bundle(b)

    def _mut_file(self, rel):
        b = good_bundle()
        with open(os.path.join(b, rel), "ab") as f:
            f.write(b" ")
        with self.assertRaises(VerifyError) as cm:
            verify_bundle(b)
        return cm.exception

    def test_18_mutated_sentinel_summary_fails(self):
        self._mut_file(f"{SENT}/{versions.SENTINEL_SUMMARY}")

    def test_19_mutated_sentinel_replay_fails(self):
        self._mut_file(f"{SENT}/{versions.SENTINEL_REPLAY}")

    def test_20_mutated_aletheia_summary_fails(self):
        self._mut_file(f"{ALE}/{versions.ALETHEIA_SUMMARY}")

    def test_21_mutated_aletheia_manifest_copy_fails(self):
        self._mut_file(f"{ALE}/{versions.ALETHEIA_MANIFEST_COPY}")

    def test_22_mutated_aletheia_replay_fails(self):
        self._mut_file(f"{ALE}/{versions.ALETHEIA_REPLAY}")

    def test_23_mutated_odin_summary_fails(self):
        self._mut_file(f"{ODIN}/{versions.ODIN_SUMMARY}")

    def test_24_mutated_odin_report_copy_fails(self):
        self._mut_file(f"{ODIN}/{versions.ODIN_REPORT_COPY}")

    def test_25_mutated_odin_trace_copy_fails(self):
        self._mut_file(f"{ODIN}/{versions.ODIN_TRACE_COPY}")

    def test_26_mutated_odin_claims_copy_fails(self):
        self._mut_file(f"{ODIN}/{versions.ODIN_CLAIMS_COPY}")

    def test_27_mutated_odin_replay_fails(self):
        self._mut_file(f"{ODIN}/{versions.ODIN_REPLAY}")

    def test_28_missing_bundle_checksums_fails(self):
        b = good_bundle()
        os.remove(os.path.join(b, versions.CHECKSUMS_NAME))
        with self.assertRaises(VerifyError) as cm:
            verify_bundle(b)
        self.assertEqual(cm.exception.reason, "BUNDLE_FILE_MISSING")

    def test_29_duplicate_checksum_key_fails(self):
        b = good_bundle()
        p = os.path.join(b, versions.CHECKSUMS_NAME)
        with open(p, encoding="utf-8") as f:
            lines = f.read().splitlines()
        with open(p, "w", encoding="utf-8") as f:
            f.write("\n".join(lines + [lines[0]]) + "\n")
        with self.assertRaises(VerifyError) as cm:
            verify_bundle(b)
        self.assertEqual(cm.exception.reason, versions.FAILED_CHECKSUMS_INVALID)

    def test_30_unknown_checksum_key_fails(self):
        b = good_bundle()
        with open(os.path.join(b, versions.CHECKSUMS_NAME), "a",
                  encoding="utf-8") as f:
            f.write(f"{'a' * 64}  surprise.json\n")
        with self.assertRaises(VerifyError) as cm:
            verify_bundle(b)
        self.assertEqual(cm.exception.reason, versions.FAILED_CHECKSUMS_INVALID)

    def test_31_malformed_digest_fails(self):
        b = good_bundle()
        p = os.path.join(b, versions.CHECKSUMS_NAME)
        with open(p, encoding="utf-8") as f:
            text = f.read()
        d0 = text.splitlines()[0].split("  ")[0]
        with open(p, "w", encoding="utf-8") as f:
            f.write(text.replace(d0, "nothex", 1))
        with self.assertRaises(VerifyError) as cm:
            verify_bundle(b)
        self.assertEqual(cm.exception.reason, versions.FAILED_CHECKSUMS_INVALID)

    def test_32_uppercase_digest_fails(self):
        b = good_bundle()
        p = os.path.join(b, versions.CHECKSUMS_NAME)
        with open(p, encoding="utf-8") as f:
            text = f.read()
        d0 = text.splitlines()[0].split("  ")[0]
        with open(p, "w", encoding="utf-8") as f:
            f.write(text.replace(d0, d0.upper(), 1))
        with self.assertRaises(VerifyError) as cm:
            verify_bundle(b)
        self.assertEqual(cm.exception.reason, versions.FAILED_CHECKSUMS_INVALID)

    def test_33_unknown_top_level_file_fails(self):
        b = good_bundle()
        with open(os.path.join(b, "rogue.txt"), "w") as f:
            f.write("x")
        with self.assertRaises(VerifyError) as cm:
            verify_bundle(b)
        self.assertEqual(cm.exception.reason, "UNKNOWN_FILE")

    def test_34_unknown_subfolder_file_fails(self):
        b = good_bundle()
        with open(os.path.join(b, ODIN, "rogue.txt"), "w") as f:
            f.write("x")
        with self.assertRaises(VerifyError) as cm:
            verify_bundle(b)
        self.assertEqual(cm.exception.reason, "UNKNOWN_SUBCASE_FILE")

    def test_35_internal_sentinel_checksum_mismatch_fails(self):
        # Tamper a sentinel file but resync the BUNDLE checksums so the bundle-level
        # hash passes; the internal sentinel checksums must still catch it.
        b = good_bundle()
        with open(os.path.join(b, SENT, versions.SENTINEL_SUMMARY), "ab") as f:
            f.write(b" ")
        _resync(b)
        with self.assertRaises(VerifyError) as cm:
            verify_bundle(b)
        self.assertEqual(cm.exception.reason,
                         "INTERNAL_SENTINEL_CHECKSUM_MISMATCH")

    def test_36_internal_aletheia_checksum_mismatch_fails(self):
        b = good_bundle()
        with open(os.path.join(b, ALE, versions.ALETHEIA_SUMMARY), "ab") as f:
            f.write(b" ")
        _resync(b)
        with self.assertRaises(VerifyError) as cm:
            verify_bundle(b)
        self.assertEqual(cm.exception.reason,
                         "INTERNAL_ALETHEIA_CHECKSUM_MISMATCH")

    def test_37_internal_odin_checksum_mismatch_fails(self):
        b = good_bundle()
        with open(os.path.join(b, ODIN, versions.ODIN_CLAIMS_COPY), "ab") as f:
            f.write(b" ")
        _resync(b)
        with self.assertRaises(VerifyError) as cm:
            verify_bundle(b)
        self.assertEqual(cm.exception.reason, "INTERNAL_ODIN_CHECKSUM_MISMATCH")

    def test_38_bundle_case_id_mismatch_fails(self):
        b = good_bundle()
        _rewrite_manifest(b, lambda o: o.update(case_id="case_OTHER"))
        _resync(b)
        with self.assertRaises(VerifyError) as cm:
            verify_bundle(b)
        self.assertEqual(cm.exception.reason, "CASE_ID_MISMATCH")

    def test_39_aletheia_status_mutated_fails(self):
        b = good_bundle()
        _rewrite_manifest(
            b, lambda o: o["aletheia"].update(
                source_evidence_status="FAILED_HASH_MISMATCH"))
        _resync(b)
        with self.assertRaises(VerifyError) as cm:
            verify_bundle(b)
        self.assertEqual(cm.exception.reason, "ALETHEIA_STATUS_INVALID")

    def test_40_odin_consistent_accepted(self):
        r = verify_bundle(good_bundle(odin=make_odin_case(
            reasoning_status="CONSISTENT")))
        self.assertEqual(r.odin_reasoning_status, "CONSISTENT")

    def test_41_odin_contradiction_accepted(self):
        r = verify_bundle(good_bundle(odin=make_odin_case(
            reasoning_status="CONTRADICTION_DETECTED", claim_count=2,
            contradiction_count=1)))
        self.assertEqual(r.odin_reasoning_status, "CONTRADICTION_DETECTED")

    def test_42_odin_invalid_input_fails(self):
        b = good_bundle()
        _rewrite_manifest(
            b, lambda o: o["odin"].update(source_reasoning_status="INVALID_INPUT"))
        _resync(b)
        with self.assertRaises(VerifyError) as cm:
            verify_bundle(b)
        self.assertEqual(cm.exception.reason, "ODIN_INVALID_INPUT")

    def test_43_truth_like_claim_in_manifest_fails(self):
        b = good_bundle()
        _rewrite_manifest(
            b, lambda o: o.update(known_limitations=o["known_limitations"]
                                  + ["the evidence_is_true and proven"]))
        _resync(b)
        with self.assertRaises(VerifyError) as cm:
            verify_bundle(b)
        self.assertEqual(cm.exception.reason, "TRUTH_CLAIM")

    def test_44_truth_like_claim_in_replay_fails(self):
        b = good_bundle()
        # Inject a forbidden token into the ODIN replay, then resync BOTH the ODIN
        # subcase's internal checksums and the bundle checksums, so verify reaches
        # the truth scan (rule 24) rather than tripping a hash check first.
        with open(os.path.join(b, ODIN, versions.ODIN_REPLAY), "a",
                  encoding="utf-8") as f:
            f.write("source.trusted: yes\n")
        _resync_odin_internal(b)
        _resync(b)
        with self.assertRaises(VerifyError) as cm:
            verify_bundle(b)
        self.assertEqual(cm.exception.reason, "TRUTH_CLAIM")

    def test_missing_bundle_dir_fails(self):
        with self.assertRaises(VerifyError) as cm:
            verify_bundle("/no/such/bundle")
        self.assertEqual(cm.exception.reason, "BUNDLE_MISSING")

    def test_missing_subfolder_fails(self):
        import shutil
        b = good_bundle()
        shutil.rmtree(os.path.join(b, ODIN))
        with self.assertRaises(VerifyError) as cm:
            verify_bundle(b)
        self.assertEqual(cm.exception.reason, "SUBFOLDER_MISSING")


if __name__ == "__main__":
    unittest.main()
