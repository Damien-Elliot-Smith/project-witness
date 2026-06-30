# tests/test_import_sentinel.py
import json
import os
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from histor_lite.errors import ImportRefused, VerifierUnavailable  # noqa: E402
from histor_lite.sentinel_import import import_sentinel_run  # noqa: E402
from histor_lite import versions  # noqa: E402
from tests.helpers import build_stub_sentinel_root, write_stub_run  # noqa: E402

FIXED = "2026-01-01T00:00:00Z"


class _Base(unittest.TestCase):
    def setUp(self):
        self.root = build_stub_sentinel_root()
        self.work = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)
        shutil.rmtree(self.work, ignore_errors=True)

    def _run(self, verdict=None, crash=False, raw=None, name="run.json"):
        return write_stub_run(os.path.join(self.work, name),
                              verdict=verdict or "PASS_STRICT", crash=crash, raw=raw)

    def _import(self, run, out="case"):
        return import_sentinel_run(sentinel_root=self.root, run_path=run,
                                   out_dir=os.path.join(self.work, out), now_utc=FIXED)

    def _summary(self, out="case"):
        with open(os.path.join(self.work, out, "case_summary.json"), encoding="utf-8") as f:
            return json.load(f)


class TestImportAccept(_Base):
    def test_1_import_pass_strict(self):
        r = self._import(self._run("PASS_STRICT"))
        self.assertEqual(r.import_status, versions.STATUS_IMPORTED)
        self.assertEqual(r.verdict, "PASS_STRICT")
        s = self._summary()
        self.assertEqual(s["sentinel_replay_verdict"], "PASS_STRICT")
        self.assertTrue(s["sentinel_replay_ok"])
        self.assertEqual(s["import_status"], "IMPORTED")
        self.assertEqual(s["source_component"], "sentinel_core")
        self.assertEqual(s["source_component_version"], "0.2.2")
        self.assertEqual(s["histor_lite_version"], "0.1.2")
        self.assertEqual(len(s["source_run_sha256"]), 64)

    def test_2_import_pass_with_environmental_exceptions(self):
        r = self._import(self._run("PASS_WITH_ENVIRONMENTAL_EXCEPTIONS"))
        self.assertEqual(r.import_status,
                         versions.STATUS_IMPORTED_WITH_ENVIRONMENTAL_EXCEPTIONS)
        s = self._summary()
        # The exact verdict must be preserved, never relabelled as strict.
        self.assertEqual(s["sentinel_replay_verdict"],
                         "PASS_WITH_ENVIRONMENTAL_EXCEPTIONS")
        self.assertEqual(s["import_status"],
                         "IMPORTED_WITH_ENVIRONMENTAL_EXCEPTIONS")
        self.assertTrue(s["sentinel_replay_ok"])
        self.assertNotIn("PASS_STRICT", s["sentinel_replay_verdict"])

    def test_7_verdict_preserved_exactly(self):
        for v in ("PASS_STRICT", "PASS_WITH_ENVIRONMENTAL_EXCEPTIONS"):
            self._import(self._run(v, name=f"{v}.json"), out=f"c_{v}")
            self.assertEqual(self._summary(f"c_{v}")["sentinel_replay_verdict"], v)

    def test_8_deterministic_canonical_json(self):
        # Same input run file (fixed clock) -> byte-identical case_summary.json.
        run = self._run("PASS_STRICT", name="same.json")
        self._import(run, out="ca")
        self._import(run, out="cb")
        with open(os.path.join(self.work, "ca", "case_summary.json"), "rb") as f:
            ba = f.read()
        with open(os.path.join(self.work, "cb", "case_summary.json"), "rb") as f:
            bb = f.read()
        self.assertEqual(ba, bb)
        # keys are sorted in the serialised form
        text = ba.decode("utf-8")
        self.assertLess(text.index('"case_id"'), text.index('"histor_lite_version"'))
        self.assertTrue(text.endswith("\n"))

    def test_9_checksums_written(self):
        self._import(self._run("PASS_STRICT"))
        cpath = os.path.join(self.work, "case", "checksums.txt")
        self.assertTrue(os.path.isfile(cpath))
        with open(cpath, encoding="utf-8") as f:
            text = f.read()
        for key in ("source_run_sha256", "case_summary_sha256",
                    "sentinel_replay_report_sha256"):
            self.assertIn(key, text)
        # the recorded case_summary hash matches the file on disk
        import hashlib
        with open(os.path.join(self.work, "case", "case_summary.json"), "rb") as f:
            actual = hashlib.sha256(f.read()).hexdigest()
        self.assertIn(actual, text)


class TestImportRefuse(_Base):
    def test_3_refuse_fail_verdict(self):
        with self.assertRaises(ImportRefused) as cm:
            self._import(self._run("FAIL"))
        self.assertEqual(cm.exception.reason, "SENTINEL_REPLAY_FAIL")
        self.assertFalse(os.path.isfile(
            os.path.join(self.work, "case", "case_summary.json")))

    def test_4_refuse_replay_incompatible(self):
        with self.assertRaises(ImportRefused) as cm:
            self._import(self._run("REPLAY_INCOMPATIBLE"))
        self.assertEqual(cm.exception.reason, "SENTINEL_REPLAY_INCOMPATIBLE")

    def test_5_refuse_missing_run_file(self):
        with self.assertRaises(ImportRefused) as cm:
            import_sentinel_run(sentinel_root=self.root,
                                run_path=os.path.join(self.work, "nope.json"),
                                out_dir=os.path.join(self.work, "case"))
        self.assertEqual(cm.exception.reason, "RUN_FILE_MISSING")

    def test_6_refuse_malformed_json(self):
        # A malformed run file makes the verifier return FAIL -> refused.
        run = self._run(raw="{ this is not valid json ", name="bad.json")
        with self.assertRaises(ImportRefused) as cm:
            self._import(run)
        self.assertEqual(cm.exception.reason, "SENTINEL_REPLAY_FAIL")

    def test_inconsistent_pass_strict_ok_false_refused(self):
        # Issue 1: verdict says PASS_STRICT but the verifier's ok flag is False.
        # An accepted verdict must have ok=True; this contradiction is refused.
        run = self._run("PASS_STRICT", name="incon_strict.json")
        # rewrite with ok override
        from tests.helpers import write_stub_run
        write_stub_run(run, "PASS_STRICT", ok=False)
        with self.assertRaises(ImportRefused) as cm:
            self._import(run)
        self.assertEqual(cm.exception.reason, "SENTINEL_VERDICT_INCONSISTENT")
        self.assertFalse(os.path.isfile(
            os.path.join(self.work, "case", "case_summary.json")))

    def test_inconsistent_pass_env_ok_false_refused(self):
        from tests.helpers import write_stub_run
        run = os.path.join(self.work, "incon_env.json")
        write_stub_run(run, "PASS_WITH_ENVIRONMENTAL_EXCEPTIONS", ok=False)
        with self.assertRaises(ImportRefused) as cm:
            self._import(run)
        self.assertEqual(cm.exception.reason, "SENTINEL_VERDICT_INCONSISTENT")

    def test_fail_with_ok_true_still_refused(self):
        # A FAIL verdict is refused regardless of an (incorrect) ok=True.
        from tests.helpers import write_stub_run
        run = os.path.join(self.work, "fail_oktrue.json")
        write_stub_run(run, "FAIL", ok=True)
        with self.assertRaises(ImportRefused) as cm:
            self._import(run)
        self.assertEqual(cm.exception.reason, "SENTINEL_REPLAY_FAIL")

    def test_incompatible_with_ok_true_still_refused(self):
        from tests.helpers import write_stub_run
        run = os.path.join(self.work, "incompat_oktrue.json")
        write_stub_run(run, "REPLAY_INCOMPATIBLE", ok=True)
        with self.assertRaises(ImportRefused) as cm:
            self._import(run)
        self.assertEqual(cm.exception.reason, "SENTINEL_REPLAY_INCOMPATIBLE")

    def test_pass_strict_ok_true_still_imports(self):
        r = self._import(self._run("PASS_STRICT", name="ok_strict.json"), out="ok_s")
        self.assertEqual(r.import_status, versions.STATUS_IMPORTED)

    def test_pass_env_ok_true_still_imports(self):
        r = self._import(self._run("PASS_WITH_ENVIRONMENTAL_EXCEPTIONS",
                                   name="ok_env.json"), out="ok_e")
        self.assertEqual(r.import_status,
                         versions.STATUS_IMPORTED_WITH_ENVIRONMENTAL_EXCEPTIONS)

    def test_verifier_crash_is_refused(self):
        run = self._run("PASS_STRICT", crash=True, name="crash.json")
        with self.assertRaises(VerifierUnavailable):
            self._import(run)

    def test_missing_sentinel_root_is_unavailable(self):
        run = self._run("PASS_STRICT")
        with self.assertRaises(VerifierUnavailable):
            import_sentinel_run(sentinel_root=os.path.join(self.work, "no_such_root"),
                                run_path=run,
                                out_dir=os.path.join(self.work, "case"))

    def test_sentinel_root_without_verifier_is_unavailable(self):
        empty = tempfile.mkdtemp()
        try:
            run = self._run("PASS_STRICT")
            with self.assertRaises(VerifierUnavailable):
                import_sentinel_run(sentinel_root=empty, run_path=run,
                                    out_dir=os.path.join(self.work, "case"))
        finally:
            shutil.rmtree(empty, ignore_errors=True)


@unittest.skipUnless(os.environ.get("SENTINEL_V022_ROOT"),
                     "set SENTINEL_V022_ROOT to an extracted sentinel_core_v022 "
                     "to run the real-Sentinel integration test")
class TestRealSentinelIntegration(unittest.TestCase):
    """Optional: drives the REAL frozen Sentinel verifier if available."""

    def test_real_pass_strict_round_trip(self):
        sroot = os.environ["SENTINEL_V022_ROOT"]
        import subprocess
        allowed = tempfile.mkdtemp()
        run = os.path.join(tempfile.mkdtemp(), "run.json")
        case = os.path.join(tempfile.mkdtemp(), "case")
        try:
            subprocess.run([sys.executable, "sentinel.py", "create", "--run", run,
                            "--run-id", "it", "--request-id", "R1",
                            "--target-path", "made", "--allowed-root", allowed],
                           cwd=sroot, check=True, capture_output=True, timeout=60)
            subprocess.run([sys.executable, "sentinel.py", "close", "--run", run],
                           cwd=sroot, check=True, capture_output=True, timeout=60)
            r = import_sentinel_run(sentinel_root=sroot, run_path=run, out_dir=case)
            self.assertEqual(r.verdict, "PASS_STRICT")
            self.assertEqual(r.import_status, versions.STATUS_IMPORTED)
        finally:
            for d in (allowed, os.path.dirname(run), os.path.dirname(case)):
                shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
