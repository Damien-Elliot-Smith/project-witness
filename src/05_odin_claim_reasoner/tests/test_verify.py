# tests/test_verify.py
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from odin_reasoner.reasoner import reason_to_dir  # noqa: E402
from odin_reasoner.verifier import verify_run  # noqa: E402
from odin_reasoner.canonical import canonical_bytes  # noqa: E402
from odin_reasoner.validation import sha256_bytes  # noqa: E402
from odin_reasoner.errors import VerifyError  # noqa: E402
from odin_reasoner import versions  # noqa: E402
from tests.helpers import consistent_set, contradiction_set_object  # noqa: E402


def _mk(claim_set=None):
    out = os.path.join(tempfile.mkdtemp(), "odin")
    reason_to_dir(claim_set or consistent_set(), out)
    return out


def _resync_checksums(out):
    """Recompute the checksums file to match whatever the three JSON files now
    contain (used to bypass the hash gate and target a later check)."""
    from odin_reasoner.checksums import format_checksums
    def sha(name):
        with open(os.path.join(out, name), "rb") as f:
            return sha256_bytes(f.read())
    data = format_checksums(
        claims_sha256=sha(versions.CLAIMS_CANONICAL_NAME),
        report_sha256=sha(versions.REASONING_REPORT_NAME),
        trace_sha256=sha(versions.PROOF_TRACE_NAME))
    with open(os.path.join(out, versions.CHECKSUMS_NAME), "wb") as f:
        f.write(data)


def _rewrite_canonical(out, name, mutate):
    p = os.path.join(out, name)
    with open(p, "rb") as f:
        obj = json.loads(f.read().decode())
    mutate(obj)
    with open(p, "wb") as f:
        f.write(canonical_bytes(obj))


class TestVerify(unittest.TestCase):
    def test_18_verify_valid_output_succeeds(self):
        out = _mk()
        r = verify_run(out)
        self.assertEqual(r.reasoning_status, versions.REASONING_CONSISTENT)

    def test_verify_valid_contradiction_output(self):
        out = _mk(contradiction_set_object())
        r = verify_run(out)
        self.assertEqual(r.reasoning_status,
                         versions.REASONING_CONTRADICTION_DETECTED)
        self.assertEqual(r.contradiction_count, 1)

    def test_19_mutated_claims_fails(self):
        out = _mk()
        with open(os.path.join(out, versions.CLAIMS_CANONICAL_NAME), "ab") as f:
            f.write(b" ")  # break canonical form / hash
        with self.assertRaises(VerifyError):
            verify_run(out)

    def test_20_mutated_report_fails(self):
        out = _mk()
        with open(os.path.join(out, versions.REASONING_REPORT_NAME), "ab") as f:
            f.write(b" ")
        with self.assertRaises(VerifyError):
            verify_run(out)

    def test_21_mutated_proof_trace_fails(self):
        out = _mk()
        with open(os.path.join(out, versions.PROOF_TRACE_NAME), "ab") as f:
            f.write(b" ")
        with self.assertRaises(VerifyError):
            verify_run(out)

    def test_22_missing_checksums_fails(self):
        out = _mk()
        os.remove(os.path.join(out, versions.CHECKSUMS_NAME))
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        self.assertEqual(cm.exception.reason, "RUN_FILE_MISSING")

    def test_23_duplicate_checksum_key_fails(self):
        out = _mk()
        p = os.path.join(out, versions.CHECKSUMS_NAME)
        with open(p, encoding="utf-8") as f:
            lines = f.read().splitlines()
        with open(p, "w", encoding="utf-8") as f:
            f.write("\n".join(lines + [lines[0]]) + "\n")  # duplicate first key
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        self.assertEqual(cm.exception.reason, "CHECKSUMS_INVALID")

    def test_24_unknown_checksum_key_fails(self):
        out = _mk()
        p = os.path.join(out, versions.CHECKSUMS_NAME)
        with open(p, "a", encoding="utf-8") as f:
            f.write(f"{'a' * 64}  surprise.json\n")
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        self.assertEqual(cm.exception.reason, "CHECKSUMS_INVALID")

    def test_25_unknown_extra_file_fails(self):
        out = _mk()
        with open(os.path.join(out, "rogue.json"), "w") as f:
            f.write("{}")
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        self.assertEqual(cm.exception.reason, "UNKNOWN_FILE")

    def test_26_report_contradiction_count_mismatch_fails(self):
        out = _mk()
        # Lie about the contradiction count, keep it canonical, resync hashes so we
        # reach the recompute check (11).
        _rewrite_canonical(out, versions.REASONING_REPORT_NAME,
                           lambda o: o.update(contradiction_count=5))
        _resync_checksums(out)
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        self.assertEqual(cm.exception.reason, "CONTRADICTION_COUNT_MISMATCH")

    def test_status_mismatch_fails(self):
        out = _mk()
        _rewrite_canonical(
            out, versions.REASONING_REPORT_NAME,
            lambda o: o.update(reasoning_status="CONTRADICTION_DETECTED"))
        _resync_checksums(out)
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        self.assertEqual(cm.exception.reason, "STATUS_MISMATCH")

    def test_27_proof_trace_unknown_claim_id_fails(self):
        out = _mk()
        def mutate(o):
            o["steps"].append({
                "step_id": "step_999", "step_type": "CLAIM_ACCEPTED",
                "claim_id": "ghost_claim",
                "reason": "CLAIM_SCHEMA_VALID_AND_SUPPORT_PRESENT"})
        _rewrite_canonical(out, versions.PROOF_TRACE_NAME, mutate)
        _resync_checksums(out)
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        self.assertEqual(cm.exception.reason, "TRACE_UNKNOWN_CLAIM_ID")

    def test_missing_run_dir_fails(self):
        with self.assertRaises(VerifyError) as cm:
            verify_run("/no/such/odin/run")
        self.assertEqual(cm.exception.reason, "RUN_MISSING")


if __name__ == "__main__":
    unittest.main()
