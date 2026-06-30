# tests/test_runner.py
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import demo  # noqa: E402
from evidence_reasoning_demo.errors import (  # noqa: E402
    ComponentPathError, StepError, ValidationError)
from evidence_reasoning_demo import versions  # noqa: E402
from tests.helpers import (  # noqa: E402
    FakeComponentRunner, run_with_fake, make_evidence_file)


def _out():
    return os.path.join(tempfile.mkdtemp(prefix="erd_out_"), "out")


class TestRunnerPaths(unittest.TestCase):
    def test_7_missing_aletheia_root_refused(self):
        # With no injected runner, real path checks apply.
        with self.assertRaises(ComponentPathError) as cm:
            demo.run_demo(evidence_file=make_evidence_file(), case_id="case_001",
                          evidence_id="evidence_001",
                          aletheia_root="/no/such/aletheia", bridge_root=HERE,
                          odin_root=HERE, out_dir=_out())
        self.assertEqual(cm.exception.reason, "ALETHEIA_ROOT_MISSING")

    def test_8_missing_bridge_root_refused(self):
        with self.assertRaises(ComponentPathError) as cm:
            demo.run_demo(evidence_file=make_evidence_file(), case_id="case_001",
                          evidence_id="evidence_001", aletheia_root=HERE,
                          bridge_root="/no/such/bridge", odin_root=HERE,
                          out_dir=_out())
        self.assertEqual(cm.exception.reason, "BRIDGE_ROOT_MISSING")

    def test_9_missing_odin_root_refused(self):
        with self.assertRaises(ComponentPathError) as cm:
            demo.run_demo(evidence_file=make_evidence_file(), case_id="case_001",
                          evidence_id="evidence_001", aletheia_root=HERE,
                          bridge_root=HERE, odin_root="/no/such/odin",
                          out_dir=_out())
        self.assertEqual(cm.exception.reason, "ODIN_ROOT_MISSING")

    def test_10_nonempty_output_dir_refused(self):
        out = _out()
        os.makedirs(out)
        with open(os.path.join(out, "rogue"), "w") as f:
            f.write("x")
        with self.assertRaises(ComponentPathError) as cm:
            run_with_fake(out)
        self.assertEqual(cm.exception.reason, "OUTPUT_DIR_NOT_EMPTY")

    def test_invalid_id_refused_before_runner(self):
        with self.assertRaises(ValidationError):
            run_with_fake(case_id="../evil")


class TestRunnerShortCircuit(unittest.TestCase):
    def _expect_fail(self, fail_at, demo_status, last_call):
        runner = FakeComponentRunner(fail_at=fail_at)
        with self.assertRaises(StepError) as cm:
            run_with_fake(runner=runner)
        self.assertEqual(cm.exception.demo_status, demo_status)
        # No operations recorded after the failing one.
        self.assertEqual(runner.calls[-1], last_call)
        return runner

    def test_11_aletheia_bundle_failure_stops_later(self):
        r = self._expect_fail("aletheia_bundle",
                              versions.FAILED_ALETHEIA_BUNDLE, "aletheia_bundle")
        self.assertEqual(r.calls, ["aletheia_bundle"])

    def test_12_aletheia_verify_failure_stops_later(self):
        r = self._expect_fail("aletheia_verify",
                              versions.FAILED_ALETHEIA_VERIFY, "aletheia_verify")
        self.assertNotIn("bridge_convert", r.calls)

    def test_13_bridge_convert_failure_stops_odin(self):
        r = self._expect_fail("bridge_convert",
                              versions.FAILED_BRIDGE_CONVERT, "bridge_convert")
        self.assertNotIn("odin_reason", r.calls)

    def test_14_bridge_verify_failure_stops_odin(self):
        r = self._expect_fail("bridge_verify",
                              versions.FAILED_BRIDGE_VERIFY, "bridge_verify")
        self.assertNotIn("odin_reason", r.calls)

    def test_15_odin_reason_failure_stops_verify(self):
        r = self._expect_fail("odin_reason",
                              versions.FAILED_ODIN_REASON, "odin_reason")
        self.assertNotIn("odin_verify", r.calls)

    def test_16_odin_verify_failure_produces_failed_status(self):
        self._expect_fail("odin_verify", versions.FAILED_ODIN_VERIFY,
                          "odin_verify")


class TestRunnerSuccess(unittest.TestCase):
    def test_17_successful_run_writes_all_files(self):
        out = _out()
        run_with_fake(out)
        for name in (versions.DEMO_REPORT_NAME, versions.DEMO_STEPS_NAME,
                     versions.CHECKSUMS_NAME):
            self.assertTrue(os.path.isfile(os.path.join(out, name)), name)
        for sub in versions.SUBFOLDERS:
            self.assertTrue(os.path.isdir(os.path.join(out, sub)), sub)

    def test_report_has_expected_statuses(self):
        out = _out()
        result = run_with_fake(out)
        r = result.report
        self.assertEqual(r["demo_status"], "DEMO_COMPLETED")
        self.assertEqual(r["aletheia_status"], "VERIFIED_PRESENT")
        self.assertEqual(r["bridge_status"], "CONVERTED")
        self.assertEqual(r["odin_reasoning_status"], "CONSISTENT")
        self.assertEqual(r["generated_claims"],
                         ["evidence.present", "evidence.integrity_verified"])

    def test_cli_run_success_exit_0(self):
        import argparse
        ns = argparse.Namespace(
            evidence_file=make_evidence_file(), case_id="case_001",
            evidence_id="evidence_001", aletheia_root="A", bridge_root="B",
            odin_root="O", out=_out())
        rc = demo.cmd_run(ns, runner=FakeComponentRunner())
        self.assertEqual(rc, 0)

    def test_cli_run_step_failure_exit_1(self):
        import argparse
        ns = argparse.Namespace(
            evidence_file=make_evidence_file(), case_id="case_001",
            evidence_id="evidence_001", aletheia_root="A", bridge_root="B",
            odin_root="O", out=_out())
        rc = demo.cmd_run(ns, runner=FakeComponentRunner(fail_at="odin_reason"))
        self.assertEqual(rc, 1)

    def test_cli_run_validation_failure_exit_2(self):
        import argparse
        ns = argparse.Namespace(
            evidence_file="/no/such/file", case_id="case_001",
            evidence_id="evidence_001", aletheia_root="A", bridge_root="B",
            odin_root="O", out=_out())
        rc = demo.cmd_run(ns, runner=FakeComponentRunner())
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
