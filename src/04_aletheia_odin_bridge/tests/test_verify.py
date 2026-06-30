# tests/test_verify.py
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from aletheia_odin_bridge.verifier import verify_run  # noqa: E402
from aletheia_odin_bridge.canonical import canonical_bytes  # noqa: E402
from aletheia_odin_bridge.validation import sha256_bytes  # noqa: E402
from aletheia_odin_bridge.checksums import format_checksums  # noqa: E402
from aletheia_odin_bridge.errors import VerifyError  # noqa: E402
from aletheia_odin_bridge import versions  # noqa: E402
from tests.helpers import good_output  # noqa: E402


def _rewrite_canonical(out, name, mutate):
    p = os.path.join(out, name)
    with open(p, "rb") as f:
        obj = json.loads(f.read().decode())
    mutate(obj)
    with open(p, "wb") as f:
        f.write(canonical_bytes(obj))


def _resync_checksums(out):
    """Recompute bridge_checksums.txt to match the current JSON files (used to
    bypass the hash gate and reach later semantic checks)."""
    def sh(name):
        with open(os.path.join(out, name), "rb") as f:
            return sha256_bytes(f.read())
    data = format_checksums(
        claims_sha256=sh(versions.ODIN_CLAIMS_NAME),
        report_sha256=sh(versions.BRIDGE_REPORT_NAME),
        manifest_copy_sha256=sh(versions.MANIFEST_COPY_NAME))
    with open(os.path.join(out, versions.CHECKSUMS_NAME), "wb") as f:
        f.write(data)


class TestVerify(unittest.TestCase):
    def test_19_verify_valid_output_succeeds(self):
        out = good_output()
        r = verify_run(out)
        self.assertEqual(r.bridge_status, "CONVERTED")
        self.assertEqual(r.claim_count, 2)

    def test_20_mutated_claims_fails(self):
        out = good_output()
        with open(os.path.join(out, versions.ODIN_CLAIMS_NAME), "ab") as f:
            f.write(b" ")
        with self.assertRaises(VerifyError):
            verify_run(out)

    def test_21_mutated_report_fails(self):
        out = good_output()
        with open(os.path.join(out, versions.BRIDGE_REPORT_NAME), "ab") as f:
            f.write(b" ")
        with self.assertRaises(VerifyError):
            verify_run(out)

    def test_22_mutated_manifest_copy_fails(self):
        out = good_output()
        with open(os.path.join(out, versions.MANIFEST_COPY_NAME), "ab") as f:
            f.write(b" ")
        with self.assertRaises(VerifyError):
            verify_run(out)

    def test_23_missing_checksums_fails(self):
        out = good_output()
        os.remove(os.path.join(out, versions.CHECKSUMS_NAME))
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        self.assertEqual(cm.exception.reason, "RUN_FILE_MISSING")

    def test_24_duplicate_checksum_key_fails(self):
        out = good_output()
        p = os.path.join(out, versions.CHECKSUMS_NAME)
        with open(p, encoding="utf-8") as f:
            lines = f.read().splitlines()
        with open(p, "w", encoding="utf-8") as f:
            f.write("\n".join(lines + [lines[0]]) + "\n")
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        self.assertEqual(cm.exception.reason,
                         versions.BRIDGE_FAILED_CHECKSUMS_INVALID)

    def test_25_unknown_checksum_key_fails(self):
        out = good_output()
        p = os.path.join(out, versions.CHECKSUMS_NAME)
        with open(p, "a", encoding="utf-8") as f:
            f.write(f"{'a' * 64}  surprise.json\n")
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        self.assertEqual(cm.exception.reason,
                         versions.BRIDGE_FAILED_CHECKSUMS_INVALID)

    def test_26_unknown_extra_file_fails(self):
        out = good_output()
        with open(os.path.join(out, "rogue.json"), "w") as f:
            f.write("{}")
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        self.assertEqual(cm.exception.reason, "UNKNOWN_FILE")

    def test_27_report_claim_count_mismatch_fails(self):
        out = good_output()
        _rewrite_canonical(out, versions.BRIDGE_REPORT_NAME,
                           lambda o: o.update(odin_claim_count=99))
        _resync_checksums(out)
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        self.assertEqual(cm.exception.reason, "CLAIM_COUNT_MISMATCH")

    def test_28_report_case_id_mismatch_fails(self):
        out = good_output()
        _rewrite_canonical(out, versions.BRIDGE_REPORT_NAME,
                           lambda o: o.update(case_id="case_OTHER"))
        _resync_checksums(out)
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        self.assertEqual(cm.exception.reason, "CASE_ID_MISMATCH")

    def test_29_support_sha_mismatch_fails(self):
        out = good_output()
        def mutate(o):
            for c in o["claims"]:
                for s in c["support"]:
                    s["source_sha256"] = "b" * 64
        _rewrite_canonical(out, versions.ODIN_CLAIMS_NAME, mutate)
        _resync_checksums(out)
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        self.assertEqual(cm.exception.reason, "SUPPORT_SHA_MISMATCH")

    def test_30_truth_predicate_injected_fails(self):
        out = good_output()
        def mutate(o):
            o["claims"][0]["predicate"] = "contents.true"
        _rewrite_canonical(out, versions.ODIN_CLAIMS_NAME, mutate)
        _resync_checksums(out)
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        # Disallowed predicate is caught first; either reason is a correct refusal.
        self.assertIn(cm.exception.reason,
                      ("DISALLOWED_PREDICATE", "TRUTH_PREDICATE"))

    def test_31_non_canonical_json_fails(self):
        out = good_output()
        p = os.path.join(out, versions.BRIDGE_REPORT_NAME)
        with open(p, "rb") as f:
            obj = json.loads(f.read().decode())
        with open(p, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2)  # pretty -> non-canonical
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        self.assertEqual(cm.exception.reason, "REPORT_NON_CANONICAL")

    def test_evidence_id_mismatch_fails(self):
        out = good_output()
        _rewrite_canonical(out, versions.MANIFEST_COPY_NAME,
                           lambda o: o.update(evidence_id="evidence_OTHER"))
        _resync_checksums(out)
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        self.assertEqual(cm.exception.reason, "EVIDENCE_ID_MISMATCH")

    def test_missing_run_dir_fails(self):
        with self.assertRaises(VerifyError) as cm:
            verify_run("/no/such/bridge/run")
        self.assertEqual(cm.exception.reason, "RUN_MISSING")


if __name__ == "__main__":
    unittest.main()
