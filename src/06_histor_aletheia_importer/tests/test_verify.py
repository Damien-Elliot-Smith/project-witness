# tests/test_verify.py
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from histor_aletheia_importer.verifier import verify_case  # noqa: E402
from histor_aletheia_importer.canonical import canonical_bytes  # noqa: E402
from histor_aletheia_importer.validation import sha256_bytes, sha256_file  # noqa: E402
from histor_aletheia_importer.checksums import format_checksums  # noqa: E402
from histor_aletheia_importer.errors import VerifyError  # noqa: E402
from histor_aletheia_importer import versions  # noqa: E402
from tests.helpers import good_case  # noqa: E402


def _rewrite_canonical(case, name, mutate):
    p = os.path.join(case, name)
    with open(p, "rb") as f:
        obj = json.loads(f.read().decode())
    mutate(obj)
    with open(p, "wb") as f:
        f.write(canonical_bytes(obj))


def _resync(case):
    """Recompute the checksums file to match current files (bypass hash gate to
    reach later semantic checks)."""
    def sh(name):
        return sha256_file(os.path.join(case, name))
    data = format_checksums(
        summary_sha256=sh(versions.SUMMARY_NAME),
        manifest_copy_sha256=sh(versions.MANIFEST_COPY_NAME),
        replay_report_sha256=sh(versions.REPLAY_REPORT_NAME))
    with open(os.path.join(case, versions.CHECKSUMS_NAME), "wb") as f:
        f.write(data)


class TestVerify(unittest.TestCase):
    def test_16_verify_valid_case_succeeds(self):
        case = good_case()
        r = verify_case(case)
        self.assertEqual(r.import_status, "IMPORTED_VERIFIED_ALETHEIA")
        self.assertEqual(r.source_evidence_status, "VERIFIED_PRESENT")

    def test_17_mutated_summary_fails(self):
        case = good_case()
        with open(os.path.join(case, versions.SUMMARY_NAME), "ab") as f:
            f.write(b" ")
        with self.assertRaises(VerifyError):
            verify_case(case)

    def test_18_mutated_manifest_copy_fails(self):
        case = good_case()
        with open(os.path.join(case, versions.MANIFEST_COPY_NAME), "ab") as f:
            f.write(b" ")
        with self.assertRaises(VerifyError):
            verify_case(case)

    def test_19_mutated_replay_report_fails(self):
        case = good_case()
        with open(os.path.join(case, versions.REPLAY_REPORT_NAME), "ab") as f:
            f.write(b"x")
        with self.assertRaises(VerifyError) as cm:
            verify_case(case)
        self.assertEqual(cm.exception.reason, "HASH_MISMATCH")

    def test_20_missing_checksums_fails(self):
        case = good_case()
        os.remove(os.path.join(case, versions.CHECKSUMS_NAME))
        with self.assertRaises(VerifyError) as cm:
            verify_case(case)
        self.assertEqual(cm.exception.reason, "CASE_FILE_MISSING")

    def test_21_duplicate_checksum_key_fails(self):
        case = good_case()
        p = os.path.join(case, versions.CHECKSUMS_NAME)
        with open(p, encoding="utf-8") as f:
            lines = f.read().splitlines()
        with open(p, "w", encoding="utf-8") as f:
            f.write("\n".join(lines + [lines[0]]) + "\n")
        with self.assertRaises(VerifyError) as cm:
            verify_case(case)
        self.assertEqual(cm.exception.reason, versions.FAILED_CHECKSUMS_INVALID)

    def test_22_unknown_checksum_key_fails(self):
        case = good_case()
        with open(os.path.join(case, versions.CHECKSUMS_NAME), "a",
                  encoding="utf-8") as f:
            f.write(f"{'a' * 64}  surprise.json\n")
        with self.assertRaises(VerifyError) as cm:
            verify_case(case)
        self.assertEqual(cm.exception.reason, versions.FAILED_CHECKSUMS_INVALID)

    def test_23_malformed_digest_fails(self):
        case = good_case()
        p = os.path.join(case, versions.CHECKSUMS_NAME)
        with open(p, encoding="utf-8") as f:
            text = f.read()
        # Replace the first digest with a non-hex string.
        first = text.splitlines()[0]
        text = text.replace(first.split("  ")[0], "nothex", 1)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        with self.assertRaises(VerifyError) as cm:
            verify_case(case)
        self.assertEqual(cm.exception.reason, versions.FAILED_CHECKSUMS_INVALID)

    def test_24_uppercase_digest_fails(self):
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

    def test_25_unknown_extra_file_fails(self):
        case = good_case()
        with open(os.path.join(case, "rogue.txt"), "w") as f:
            f.write("x")
        with self.assertRaises(VerifyError) as cm:
            verify_case(case)
        self.assertEqual(cm.exception.reason, "UNKNOWN_FILE")

    def test_26_case_id_mismatch_fails(self):
        case = good_case()
        _rewrite_canonical(case, versions.SUMMARY_NAME,
                           lambda o: o.update(case_id="case_OTHER"))
        _resync(case)
        with self.assertRaises(VerifyError) as cm:
            verify_case(case)
        self.assertEqual(cm.exception.reason, "CASE_ID_MISMATCH")

    def test_27_evidence_id_mismatch_fails(self):
        case = good_case()
        _rewrite_canonical(case, versions.SUMMARY_NAME,
                           lambda o: o.update(evidence_id="evidence_OTHER"))
        _resync(case)
        with self.assertRaises(VerifyError) as cm:
            verify_case(case)
        self.assertEqual(cm.exception.reason, "EVIDENCE_ID_MISMATCH")

    def test_28_source_status_mismatch_fails(self):
        case = good_case()
        _rewrite_canonical(
            case, versions.SUMMARY_NAME,
            lambda o: o.update(source_evidence_status="FAILED_HASH_MISMATCH"))
        _resync(case)
        with self.assertRaises(VerifyError) as cm:
            verify_case(case)
        self.assertEqual(cm.exception.reason, "SOURCE_STATUS_MISMATCH")

    def test_29_source_file_sha_mismatch_fails(self):
        case = good_case()
        _rewrite_canonical(case, versions.SUMMARY_NAME,
                           lambda o: o.update(source_file_sha256="b" * 64))
        _resync(case)
        with self.assertRaises(VerifyError) as cm:
            verify_case(case)
        self.assertEqual(cm.exception.reason, "SOURCE_FILE_SHA_MISMATCH")

    def test_30_bundled_file_sha_mismatch_fails(self):
        case = good_case()
        _rewrite_canonical(case, versions.SUMMARY_NAME,
                           lambda o: o.update(bundled_file_sha256="b" * 64))
        _resync(case)
        with self.assertRaises(VerifyError) as cm:
            verify_case(case)
        self.assertEqual(cm.exception.reason, "BUNDLED_FILE_SHA_MISMATCH")

    def test_31_truth_like_claim_in_summary_fails(self):
        case = good_case()
        _rewrite_canonical(
            case, versions.SUMMARY_NAME,
            lambda o: o.update(known_limitations=o["known_limitations"]
                               + ["file.authentic confirmed"]))
        _resync(case)
        with self.assertRaises(VerifyError) as cm:
            verify_case(case)
        self.assertEqual(cm.exception.reason, "TRUTH_CLAIM")

    def test_32_truth_like_claim_in_replay_report_fails(self):
        case = good_case()
        p = os.path.join(case, versions.REPLAY_REPORT_NAME)
        with open(p, "a", encoding="utf-8") as f:
            f.write("source.trusted: yes\n")
        _resync(case)
        with self.assertRaises(VerifyError) as cm:
            verify_case(case)
        self.assertEqual(cm.exception.reason, "TRUTH_CLAIM")

    def test_import_status_mismatch_fails(self):
        case = good_case()
        _rewrite_canonical(case, versions.SUMMARY_NAME,
                           lambda o: o.update(import_status="SOMETHING_ELSE"))
        _resync(case)
        with self.assertRaises(VerifyError) as cm:
            verify_case(case)
        self.assertEqual(cm.exception.reason, "IMPORT_STATUS_MISMATCH")

    def test_missing_case_dir_fails(self):
        with self.assertRaises(VerifyError) as cm:
            verify_case("/no/such/case")
        self.assertEqual(cm.exception.reason, "CASE_MISSING")


if __name__ == "__main__":
    unittest.main()
