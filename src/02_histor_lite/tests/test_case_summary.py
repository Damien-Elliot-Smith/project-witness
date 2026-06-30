# tests/test_case_summary.py
import json
import os
import shutil
import tempfile
import unittest
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from histor_lite.canonical import canonical_bytes  # noqa: E402
from histor_lite.case_summary import (  # noqa: E402
    build_case_summary, case_id_for, verify_case, CASE_SUMMARY_NAME,
    REPLAY_REPORT_NAME, CHECKSUMS_NAME,
)
from histor_lite.errors import CaseError  # noqa: E402
from histor_lite.sentinel_import import import_sentinel_run  # noqa: E402
from histor_lite import versions  # noqa: E402
from tests.helpers import build_stub_sentinel_root, write_stub_run  # noqa: E402

FIXED = "2026-01-01T00:00:00Z"


class TestBuildSummary(unittest.TestCase):
    def test_summary_is_pure_and_deterministic(self):
        kw = dict(source_run_path="/x/run.json", source_run_sha256="a" * 64,
                  verdict="PASS_STRICT", ok=True,
                  import_status=versions.STATUS_IMPORTED, verified_at_utc=FIXED)
        s1 = build_case_summary(**kw)
        s2 = build_case_summary(**kw)
        self.assertEqual(canonical_bytes(s1), canonical_bytes(s2))
        self.assertEqual(s1["case_id"], case_id_for("a" * 64))
        self.assertEqual(s1["known_limitations"], list(versions.KNOWN_LIMITATIONS))

    def test_env_exceptions_verdict_not_relabelled(self):
        s = build_case_summary(
            source_run_path="/x", source_run_sha256="b" * 64,
            verdict="PASS_WITH_ENVIRONMENTAL_EXCEPTIONS", ok=True,
            import_status=versions.STATUS_IMPORTED_WITH_ENVIRONMENTAL_EXCEPTIONS,
            verified_at_utc=FIXED)
        self.assertEqual(s["sentinel_replay_verdict"],
                         "PASS_WITH_ENVIRONMENTAL_EXCEPTIONS")
        self.assertEqual(s["import_status"], "IMPORTED_WITH_ENVIRONMENTAL_EXCEPTIONS")


class TestVerifyCase(unittest.TestCase):
    def setUp(self):
        self.root = build_stub_sentinel_root()
        self.work = tempfile.mkdtemp()
        run = write_stub_run(os.path.join(self.work, "run.json"), "PASS_STRICT")
        self.case = os.path.join(self.work, "case")
        import_sentinel_run(sentinel_root=self.root, run_path=run,
                            out_dir=self.case, now_utc=FIXED)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)
        shutil.rmtree(self.work, ignore_errors=True)

    def test_10_verify_clean_case(self):
        res = verify_case(self.case)
        self.assertEqual(res["integrity"], "OK")
        self.assertEqual(res["sentinel_replay_verdict"], "PASS_STRICT")
        self.assertEqual(res["import_status"], "IMPORTED")

    def test_11_detect_mutated_case_summary(self):
        sp = os.path.join(self.case, CASE_SUMMARY_NAME)
        with open(sp, "r+", encoding="utf-8") as f:
            data = f.read().replace("IMPORTED", "FORGED")
            f.seek(0)
            f.write(data)
            f.truncate()
        with self.assertRaises(CaseError):
            verify_case(self.case)

    def test_detect_mutated_replay_report(self):
        rp = os.path.join(self.case, REPLAY_REPORT_NAME)
        with open(rp, "a", encoding="utf-8") as f:
            f.write("tampered line\n")
        with self.assertRaises(CaseError):
            verify_case(self.case)

    def test_detect_noncanonical_summary_same_hash_line(self):
        # Re-pretty-print the summary (valid JSON, different bytes) and also fix
        # the checksum to match: the canonical-form check still catches it.
        import hashlib
        sp = os.path.join(self.case, CASE_SUMMARY_NAME)
        with open(sp, encoding="utf-8") as f:
            obj = json.load(f)
        pretty = (json.dumps(obj, indent=2) + "\n").encode("utf-8")
        with open(sp, "wb") as f:
            f.write(pretty)
        # update checksums.txt so the byte-hash matches the pretty file
        cp = os.path.join(self.case, CHECKSUMS_NAME)
        with open(cp, encoding="utf-8") as f:
            lines = f.read().splitlines()
        new = []
        for ln in lines:
            if ln.startswith("case_summary_sha256"):
                new.append(f"case_summary_sha256  {hashlib.sha256(pretty).hexdigest()}  "
                           f"{CASE_SUMMARY_NAME}")
            else:
                new.append(ln)
        with open(cp, "w", encoding="utf-8") as f:
            f.write("\n".join(new) + "\n")
        # byte-hash now matches, but the file is not canonical -> still detected
        with self.assertRaises(CaseError):
            verify_case(self.case)

    def test_missing_case_folder(self):
        with self.assertRaises(CaseError):
            verify_case(os.path.join(self.work, "no_case"))

    # ── Issue 2: source_run_sha256 metadata consistency ────────────────────
    def _edit_checksums(self, transform):
        cp = os.path.join(self.case, CHECKSUMS_NAME)
        with open(cp, encoding="utf-8") as f:
            lines = f.read().splitlines()
        out = [transform(ln) for ln in lines]
        with open(cp, "w", encoding="utf-8") as f:
            f.write("\n".join(x for x in out if x is not None) + "\n")

    def test_source_run_sha256_value_tamper_detected(self):
        # Modify ONLY the source_run_sha256 line -> must fail (the original bug).
        self._edit_checksums(
            lambda ln: ("source_run_sha256  " + "d" * 64 + "  run.json")
            if ln.startswith("source_run_sha256") else ln)
        with self.assertRaises(CaseError) as cm:
            verify_case(self.case)
        self.assertIn("source_run_sha256", str(cm.exception))

    def test_source_run_sha256_missing_line_detected(self):
        self._edit_checksums(
            lambda ln: None if ln.startswith("source_run_sha256") else ln)
        with self.assertRaises(CaseError) as cm:
            verify_case(self.case)
        self.assertIn("missing source_run_sha256", str(cm.exception))

    def test_source_run_sha256_malformed_digest_detected(self):
        self._edit_checksums(
            lambda ln: ("source_run_sha256  NOT_A_HEX_DIGEST  run.json")
            if ln.startswith("source_run_sha256") else ln)
        with self.assertRaises(CaseError) as cm:
            verify_case(self.case)
        self.assertIn("valid SHA-256", str(cm.exception))

    def test_summary_and_report_hash_checks_still_work(self):
        # Regression guard: the two original hash checks remain effective.
        import shutil as _sh
        # mutate report
        with open(os.path.join(self.case, REPLAY_REPORT_NAME), "a",
                  encoding="utf-8") as f:
            f.write("tamper\n")
        with self.assertRaises(CaseError):
            verify_case(self.case)

    # ── Issue 1 (v0.1.2): duplicate checksum keys must be rejected ──────────
    def _prepend_duplicate(self, key):
        cp = os.path.join(self.case, CHECKSUMS_NAME)
        with open(cp, encoding="utf-8") as f:
            lines = f.read().splitlines()
        target = next(l for l in lines if l.startswith(key))
        with open(cp, "w", encoding="utf-8") as f:
            f.write("\n".join([target] + lines) + "\n")

    def test_duplicate_source_run_sha256_fails(self):
        self._prepend_duplicate("source_run_sha256")
        with self.assertRaises(CaseError) as cm:
            verify_case(self.case)
        self.assertIn("Duplicate checksum key", str(cm.exception))

    def test_duplicate_case_summary_sha256_fails(self):
        self._prepend_duplicate("case_summary_sha256")
        with self.assertRaises(CaseError) as cm:
            verify_case(self.case)
        self.assertIn("Duplicate checksum key", str(cm.exception))

    def test_duplicate_replay_report_sha256_fails(self):
        self._prepend_duplicate("sentinel_replay_report_sha256")
        with self.assertRaises(CaseError) as cm:
            verify_case(self.case)
        self.assertIn("Duplicate checksum key", str(cm.exception))

    def test_duplicate_bogus_then_correct_source_hash_fails(self):
        # The exact reported attack: a bogus source_run_sha256 line followed by
        # the correct one. "Last line wins" would have passed; we must reject.
        cp = os.path.join(self.case, CHECKSUMS_NAME)
        with open(cp, encoding="utf-8") as f:
            lines = f.read().splitlines()
        bogus = "source_run_sha256  " + "d" * 64 + "  run.json"
        with open(cp, "w", encoding="utf-8") as f:
            f.write("\n".join([bogus] + lines) + "\n")
        with self.assertRaises(CaseError) as cm:
            verify_case(self.case)
        self.assertIn("Duplicate checksum key", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
