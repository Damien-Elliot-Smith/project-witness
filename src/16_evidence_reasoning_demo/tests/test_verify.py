# tests/test_verify.py
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from evidence_reasoning_demo.verifier import verify_run  # noqa: E402
from evidence_reasoning_demo.canonical import canonical_bytes  # noqa: E402
from evidence_reasoning_demo.validation import sha256_bytes, sha256_file  # noqa: E402
from evidence_reasoning_demo.checksums import format_checksums  # noqa: E402
from evidence_reasoning_demo.errors import VerifyError  # noqa: E402
from evidence_reasoning_demo import versions  # noqa: E402
from tests.helpers import good_output, FakeComponentRunner, run_with_fake  # noqa: E402


def _rewrite_canonical(out, name, mutate):
    p = os.path.join(out, name)
    with open(p, "rb") as f:
        obj = json.loads(f.read().decode())
    mutate(obj)
    with open(p, "wb") as f:
        f.write(canonical_bytes(obj))


def _resync_checksums(out):
    """Recompute demo_checksums.txt to match current files (bypass hash gate to
    reach later semantic checks)."""
    def shb(name):
        with open(os.path.join(out, name), "rb") as f:
            return sha256_bytes(f.read())
    data = format_checksums(
        demo_report_sha256=shb(versions.DEMO_REPORT_NAME),
        demo_steps_sha256=shb(versions.DEMO_STEPS_NAME),
        aletheia_manifest_sha256=sha256_file(
            os.path.join(out, versions.ALETHEIA_MANIFEST_REL)),
        bridge_report_sha256=sha256_file(
            os.path.join(out, versions.BRIDGE_REPORT_REL)),
        odin_reasoning_report_sha256=sha256_file(
            os.path.join(out, versions.ODIN_REASONING_REPORT_REL)))
    with open(os.path.join(out, versions.CHECKSUMS_NAME), "wb") as f:
        f.write(data)


class TestVerify(unittest.TestCase):
    def test_21_verify_valid_output_succeeds(self):
        out = good_output()
        r = verify_run(out)
        self.assertEqual(r.demo_status, "DEMO_COMPLETED")
        self.assertEqual(r.odin_reasoning_status, "CONSISTENT")

    def test_22_mutated_demo_report_fails(self):
        out = good_output()
        with open(os.path.join(out, versions.DEMO_REPORT_NAME), "ab") as f:
            f.write(b" ")
        with self.assertRaises(VerifyError):
            verify_run(out)

    def test_23_mutated_demo_steps_fails(self):
        out = good_output()
        with open(os.path.join(out, versions.DEMO_STEPS_NAME), "ab") as f:
            f.write(b" ")
        with self.assertRaises(VerifyError):
            verify_run(out)

    def test_24_mutated_aletheia_manifest_hash_fails(self):
        out = good_output()
        p = os.path.join(out, versions.ALETHEIA_MANIFEST_REL)
        with open(p, "ab") as f:
            f.write(b" ")
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        self.assertEqual(cm.exception.reason, "HASH_MISMATCH")

    def test_25_mutated_bridge_report_hash_fails(self):
        out = good_output()
        with open(os.path.join(out, versions.BRIDGE_REPORT_REL), "ab") as f:
            f.write(b" ")
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        self.assertEqual(cm.exception.reason, "HASH_MISMATCH")

    def test_26_mutated_odin_report_hash_fails(self):
        out = good_output()
        with open(os.path.join(out, versions.ODIN_REASONING_REPORT_REL), "ab") as f:
            f.write(b" ")
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        self.assertEqual(cm.exception.reason, "HASH_MISMATCH")

    def test_27_missing_checksums_fails(self):
        out = good_output()
        os.remove(os.path.join(out, versions.CHECKSUMS_NAME))
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        self.assertEqual(cm.exception.reason, "RUN_FILE_MISSING")

    def test_28_duplicate_checksum_key_fails(self):
        out = good_output()
        p = os.path.join(out, versions.CHECKSUMS_NAME)
        with open(p, encoding="utf-8") as f:
            lines = f.read().splitlines()
        with open(p, "w", encoding="utf-8") as f:
            f.write("\n".join(lines + [lines[0]]) + "\n")
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        self.assertEqual(cm.exception.reason, versions.FAILED_CHECKSUMS_INVALID)

    def test_29_unknown_checksum_key_fails(self):
        out = good_output()
        with open(os.path.join(out, versions.CHECKSUMS_NAME), "a",
                  encoding="utf-8") as f:
            f.write(f"{'a' * 64}  surprise.json\n")
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        self.assertEqual(cm.exception.reason, versions.FAILED_CHECKSUMS_INVALID)

    def test_30_unknown_extra_top_level_file_fails(self):
        out = good_output()
        with open(os.path.join(out, "rogue.json"), "w") as f:
            f.write("{}")
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        self.assertEqual(cm.exception.reason, "UNKNOWN_FILE")

    def test_31_case_id_mismatch_fails(self):
        out = good_output()
        _rewrite_canonical(out, versions.DEMO_REPORT_NAME,
                           lambda o: o.update(case_id="case_OTHER"))
        _resync_checksums(out)
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        self.assertEqual(cm.exception.reason, "CASE_ID_MISMATCH")

    def test_32_evidence_id_mismatch_fails(self):
        out = good_output()
        _rewrite_canonical(out, versions.DEMO_REPORT_NAME,
                           lambda o: o.update(evidence_id="evidence_OTHER"))
        _resync_checksums(out)
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        self.assertEqual(cm.exception.reason, "EVIDENCE_ID_MISMATCH")

    def test_33_truth_like_generated_claim_fails(self):
        out = good_output()
        _rewrite_canonical(
            out, versions.DEMO_REPORT_NAME,
            lambda o: o.update(generated_claims=["evidence.present",
                                                 "contents.true"]))
        _resync_checksums(out)
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        self.assertIn(cm.exception.reason,
                      ("DISALLOWED_PREDICATE", "TRUTH_PREDICATE"))

    def test_34_non_consistent_odin_status_fails(self):
        out = good_output()
        _rewrite_canonical(
            out, versions.DEMO_REPORT_NAME,
            lambda o: o.update(odin_reasoning_status="CONTRADICTION_DETECTED"))
        _resync_checksums(out)
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        self.assertEqual(cm.exception.reason, "ODIN_STATUS_NOT_CONSISTENT")

    def test_35_non_completed_demo_status_fails(self):
        out = good_output()
        _rewrite_canonical(out, versions.DEMO_REPORT_NAME,
                           lambda o: o.update(demo_status="FAILED_ODIN_VERIFY"))
        _resync_checksums(out)
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        self.assertEqual(cm.exception.reason, "DEMO_STATUS_NOT_COMPLETED")

    def test_missing_subfolder_fails(self):
        import shutil
        out = good_output()
        shutil.rmtree(os.path.join(out, versions.ODIN_OUTPUT_DIR))
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        self.assertIn(cm.exception.reason,
                      ("SUBFOLDER_MISSING", "COMPONENT_FILE_MISSING"))

    def test_missing_run_dir_fails(self):
        with self.assertRaises(VerifyError) as cm:
            verify_run("/no/such/demo/run")
        self.assertEqual(cm.exception.reason, "RUN_MISSING")


if __name__ == "__main__":
    unittest.main()
