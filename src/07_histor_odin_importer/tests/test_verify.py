# tests/test_verify.py
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from histor_odin_importer.verifier import verify_case  # noqa: E402
from histor_odin_importer.canonical import canonical_bytes  # noqa: E402
from histor_odin_importer.validation import sha256_file  # noqa: E402
from histor_odin_importer.checksums import format_checksums  # noqa: E402
from histor_odin_importer.errors import VerifyError  # noqa: E402
from histor_odin_importer import versions  # noqa: E402
from tests.helpers import good_case, contradiction_run  # noqa: E402


def _rewrite_canonical(case, name, mutate):
    p = os.path.join(case, name)
    with open(p, "rb") as f:
        obj = json.loads(f.read().decode())
    mutate(obj)
    with open(p, "wb") as f:
        f.write(canonical_bytes(obj))


def _resync(case):
    """Recompute checksums to match current files (bypass hash gate to reach later
    semantic checks)."""
    def sh(name):
        return sha256_file(os.path.join(case, name))
    data = format_checksums(
        summary_sha256=sh(versions.SUMMARY_NAME),
        report_copy_sha256=sh(versions.REPORT_COPY_NAME),
        trace_copy_sha256=sh(versions.TRACE_COPY_NAME),
        claims_copy_sha256=sh(versions.CLAIMS_COPY_NAME),
        replay_report_sha256=sh(versions.REPLAY_REPORT_NAME))
    with open(os.path.join(case, versions.CHECKSUMS_NAME), "wb") as f:
        f.write(data)


class TestVerify(unittest.TestCase):
    def test_21_verify_valid_case_succeeds(self):
        r = verify_case(good_case())
        self.assertEqual(r.import_status, "IMPORTED_VERIFIED_ODIN")
        self.assertEqual(r.source_reasoning_status, "CONSISTENT")

    def test_21b_verify_contradiction_case_succeeds(self):
        r = verify_case(good_case(run_dir=contradiction_run()))
        self.assertEqual(r.source_reasoning_status, "CONTRADICTION_DETECTED")
        self.assertEqual(r.contradiction_count, 1)

    def test_22_mutated_summary_fails(self):
        case = good_case()
        with open(os.path.join(case, versions.SUMMARY_NAME), "ab") as f:
            f.write(b" ")
        with self.assertRaises(VerifyError):
            verify_case(case)

    def test_23_mutated_report_copy_fails(self):
        case = good_case()
        with open(os.path.join(case, versions.REPORT_COPY_NAME), "ab") as f:
            f.write(b" ")
        with self.assertRaises(VerifyError):
            verify_case(case)

    def test_24_mutated_trace_copy_fails(self):
        case = good_case()
        with open(os.path.join(case, versions.TRACE_COPY_NAME), "ab") as f:
            f.write(b" ")
        with self.assertRaises(VerifyError):
            verify_case(case)

    def test_25_mutated_claims_copy_fails(self):
        case = good_case()
        with open(os.path.join(case, versions.CLAIMS_COPY_NAME), "ab") as f:
            f.write(b" ")
        with self.assertRaises(VerifyError):
            verify_case(case)

    def test_26_mutated_replay_report_fails(self):
        case = good_case()
        with open(os.path.join(case, versions.REPLAY_REPORT_NAME), "ab") as f:
            f.write(b"x")
        with self.assertRaises(VerifyError) as cm:
            verify_case(case)
        self.assertEqual(cm.exception.reason, "HASH_MISMATCH")

    def test_27_missing_checksums_fails(self):
        case = good_case()
        os.remove(os.path.join(case, versions.CHECKSUMS_NAME))
        with self.assertRaises(VerifyError) as cm:
            verify_case(case)
        self.assertEqual(cm.exception.reason, "CASE_FILE_MISSING")

    def test_28_duplicate_checksum_key_fails(self):
        case = good_case()
        p = os.path.join(case, versions.CHECKSUMS_NAME)
        with open(p, encoding="utf-8") as f:
            lines = f.read().splitlines()
        with open(p, "w", encoding="utf-8") as f:
            f.write("\n".join(lines + [lines[0]]) + "\n")
        with self.assertRaises(VerifyError) as cm:
            verify_case(case)
        self.assertEqual(cm.exception.reason, versions.FAILED_CHECKSUMS_INVALID)

    def test_29_unknown_checksum_key_fails(self):
        case = good_case()
        with open(os.path.join(case, versions.CHECKSUMS_NAME), "a",
                  encoding="utf-8") as f:
            f.write(f"{'a' * 64}  surprise.json\n")
        with self.assertRaises(VerifyError) as cm:
            verify_case(case)
        self.assertEqual(cm.exception.reason, versions.FAILED_CHECKSUMS_INVALID)

    def test_30_malformed_digest_fails(self):
        case = good_case()
        p = os.path.join(case, versions.CHECKSUMS_NAME)
        with open(p, encoding="utf-8") as f:
            text = f.read()
        first_digest = text.splitlines()[0].split("  ")[0]
        text = text.replace(first_digest, "nothex", 1)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        with self.assertRaises(VerifyError) as cm:
            verify_case(case)
        self.assertEqual(cm.exception.reason, versions.FAILED_CHECKSUMS_INVALID)

    def test_31_uppercase_digest_fails(self):
        case = good_case()
        p = os.path.join(case, versions.CHECKSUMS_NAME)
        with open(p, encoding="utf-8") as f:
            text = f.read()
        first_digest = text.splitlines()[0].split("  ")[0]
        text = text.replace(first_digest, first_digest.upper(), 1)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        with self.assertRaises(VerifyError) as cm:
            verify_case(case)
        self.assertEqual(cm.exception.reason, versions.FAILED_CHECKSUMS_INVALID)

    def test_32_unknown_extra_file_fails(self):
        case = good_case()
        with open(os.path.join(case, "rogue.txt"), "w") as f:
            f.write("x")
        with self.assertRaises(VerifyError) as cm:
            verify_case(case)
        self.assertEqual(cm.exception.reason, "UNKNOWN_FILE")

    def test_33_case_id_mismatch_fails(self):
        case = good_case()
        _rewrite_canonical(case, versions.SUMMARY_NAME,
                           lambda o: o.update(case_id="case_OTHER"))
        _resync(case)
        with self.assertRaises(VerifyError) as cm:
            verify_case(case)
        self.assertEqual(cm.exception.reason, "CASE_ID_MISMATCH")

    def test_34_reasoning_status_mismatch_fails(self):
        case = good_case()
        # change summary status to a different importable value than report copy
        _rewrite_canonical(
            case, versions.SUMMARY_NAME,
            lambda o: o.update(source_reasoning_status="CONTRADICTION_DETECTED"))
        _resync(case)
        with self.assertRaises(VerifyError) as cm:
            verify_case(case)
        self.assertEqual(cm.exception.reason, "SOURCE_STATUS_MISMATCH")

    def test_35_claim_count_mismatch_fails(self):
        case = good_case()
        _rewrite_canonical(case, versions.SUMMARY_NAME,
                           lambda o: o.update(claim_count=99))
        _resync(case)
        with self.assertRaises(VerifyError) as cm:
            verify_case(case)
        self.assertEqual(cm.exception.reason, "CLAIM_COUNT_MISMATCH")

    def test_36_contradiction_count_mismatch_fails(self):
        case = good_case()
        _rewrite_canonical(case, versions.SUMMARY_NAME,
                           lambda o: o.update(contradiction_count=99))
        _resync(case)
        with self.assertRaises(VerifyError) as cm:
            verify_case(case)
        self.assertEqual(cm.exception.reason, "CONTRADICTION_COUNT_MISMATCH")

    def test_37_proof_step_count_mismatch_fails(self):
        case = good_case()
        _rewrite_canonical(case, versions.SUMMARY_NAME,
                           lambda o: o.update(proof_step_count=99))
        _resync(case)
        with self.assertRaises(VerifyError) as cm:
            verify_case(case)
        self.assertEqual(cm.exception.reason, "PROOF_STEP_COUNT_MISMATCH")

    def test_38_import_status_mismatch_fails(self):
        case = good_case()
        _rewrite_canonical(case, versions.SUMMARY_NAME,
                           lambda o: o.update(import_status="SOMETHING_ELSE"))
        _resync(case)
        with self.assertRaises(VerifyError) as cm:
            verify_case(case)
        self.assertEqual(cm.exception.reason, "IMPORT_STATUS_MISMATCH")

    def test_39_invalid_input_injected_fails(self):
        # Inject INVALID_INPUT into BOTH summary and report copy (so the status
        # cross-check passes) and resync; verify must still refuse INVALID_INPUT.
        case = good_case()
        _rewrite_canonical(
            case, versions.SUMMARY_NAME,
            lambda o: o.update(source_reasoning_status="INVALID_INPUT"))
        _rewrite_canonical(
            case, versions.REPORT_COPY_NAME,
            lambda o: o.update(reasoning_status="INVALID_INPUT"))
        _resync(case)
        with self.assertRaises(VerifyError) as cm:
            verify_case(case)
        self.assertEqual(cm.exception.reason, "REASONING_STATUS_INVALID")

    def test_40_truth_like_claim_in_summary_fails(self):
        case = good_case()
        _rewrite_canonical(
            case, versions.SUMMARY_NAME,
            lambda o: o.update(known_limitations=o["known_limitations"]
                               + ["claim.true asserted"]))
        _resync(case)
        with self.assertRaises(VerifyError) as cm:
            verify_case(case)
        self.assertEqual(cm.exception.reason, "TRUTH_CLAIM")

    def test_41_truth_like_claim_in_replay_report_fails(self):
        case = good_case()
        with open(os.path.join(case, versions.REPLAY_REPORT_NAME), "a",
                  encoding="utf-8") as f:
            f.write("source.trusted: yes\n")
        _resync(case)
        with self.assertRaises(VerifyError) as cm:
            verify_case(case)
        self.assertEqual(cm.exception.reason, "TRUTH_CLAIM")

    def test_missing_case_dir_fails(self):
        with self.assertRaises(VerifyError) as cm:
            verify_case("/no/such/case")
        self.assertEqual(cm.exception.reason, "CASE_MISSING")


if __name__ == "__main__":
    unittest.main()
