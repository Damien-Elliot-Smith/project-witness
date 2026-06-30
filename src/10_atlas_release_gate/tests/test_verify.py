import os

from atlas_release_gate_lib import canonical, verifier
from atlas_release_gate_lib.errors import (
    VerifyError, RELEASE_GATE_PASSED, FAILED_DOCUMENTATION_CHECK)
from tests._helpers import TempCase


def _report_path(out_dir):
    return os.path.join(out_dir, "atlas_release_gate_report.json")


def _steps_path(out_dir):
    return os.path.join(out_dir, "atlas_release_gate_steps.json")


class TestVerify(TempCase):
    def _passed_run(self):
        out_dir, outcome = self.run_gate()
        self.assertEqual(outcome.status, RELEASE_GATE_PASSED)
        return out_dir

    def test_valid_output_verifies(self):
        out_dir = self._passed_run()
        result = verifier.verify(out_dir)
        self.assertTrue(result.ok)
        self.assertEqual(result.status, RELEASE_GATE_PASSED)

    def test_mutated_report_fails(self):
        out_dir = self._passed_run()
        data = canonical.read_bytes(_report_path(out_dir))
        canonical.atomic_write_bytes(_report_path(out_dir), data + b" ")
        with self.assertRaises(VerifyError):
            verifier.verify(out_dir)

    def test_mutated_steps_fails(self):
        out_dir = self._passed_run()
        data = canonical.read_bytes(_steps_path(out_dir))
        canonical.atomic_write_bytes(_steps_path(out_dir), data + b" ")
        with self.assertRaises(VerifyError):
            verifier.verify(out_dir)

    def test_mutated_export_registry_copy_fails(self):
        out_dir = self._passed_run()
        path = os.path.join(out_dir, "atlas_export", "atlas_registry_copy.json")
        canonical.atomic_write_bytes(path, canonical.read_bytes(path) + b" ")
        with self.assertRaises(VerifyError):
            verifier.verify(out_dir)

    def test_mutated_export_summary_fails(self):
        out_dir = self._passed_run()
        path = os.path.join(out_dir, "atlas_export", "atlas_summary.json")
        canonical.atomic_write_bytes(path, canonical.read_bytes(path) + b" ")
        with self.assertRaises(VerifyError):
            verifier.verify(out_dir)

    def test_missing_checksums_fails(self):
        out_dir = self._passed_run()
        os.unlink(os.path.join(out_dir, "atlas_release_gate_checksums.txt"))
        with self.assertRaises(VerifyError):
            verifier.verify(out_dir)

    def test_unknown_top_level_file_fails(self):
        out_dir = self._passed_run()
        canonical.atomic_write_bytes(os.path.join(out_dir, "surprise.txt"), b"x")
        with self.assertRaises(VerifyError):
            verifier.verify(out_dir)

    def test_unknown_export_file_fails(self):
        out_dir = self._passed_run()
        canonical.atomic_write_bytes(
            os.path.join(out_dir, "atlas_export", "extra.json"), b"{}")
        with self.assertRaises(VerifyError):
            verifier.verify(out_dir)

    def test_wrong_step_order_fails(self):
        out_dir = self._passed_run()
        steps_obj = canonical.load_json(_steps_path(out_dir))
        steps_obj["steps"][0], steps_obj["steps"][1] = (
            steps_obj["steps"][1], steps_obj["steps"][0])
        canonical.write_canonical(_steps_path(out_dir), steps_obj)
        self.rebuild_checksums(out_dir)
        with self.assertRaises(VerifyError):
            verifier.verify(out_dir)

    def test_passed_gate_with_skipped_step_fails(self):
        out_dir = self._passed_run()
        steps_obj = canonical.load_json(_steps_path(out_dir))
        steps_obj["steps"][8]["status"] = "SKIPPED_AFTER_FAILURE"
        canonical.write_canonical(_steps_path(out_dir), steps_obj)
        self.rebuild_checksums(out_dir)
        with self.assertRaises(VerifyError):
            verifier.verify(out_dir)

    def test_non_passed_status_fails(self):
        out_dir = self._passed_run()
        report = canonical.load_json(_report_path(out_dir))
        report["release_gate_status"] = FAILED_DOCUMENTATION_CHECK
        canonical.write_canonical(_report_path(out_dir), report)
        self.rebuild_checksums(out_dir)
        result = verifier.verify(out_dir)
        self.assertFalse(result.ok)

    def test_non_registry_verified_fails(self):
        out_dir = self._passed_run()
        report = canonical.load_json(_report_path(out_dir))
        report["registry_status"] = "REGISTRY_NOT_VERIFIED"
        canonical.write_canonical(_report_path(out_dir), report)
        self.rebuild_checksums(out_dir)
        with self.assertRaises(VerifyError):
            verifier.verify(out_dir)

    def test_non_export_verified_fails(self):
        out_dir = self._passed_run()
        report = canonical.load_json(_report_path(out_dir))
        report["export_status"] = "EXPORT_NOT_VERIFIED"
        canonical.write_canonical(_report_path(out_dir), report)
        self.rebuild_checksums(out_dir)
        with self.assertRaises(VerifyError):
            verifier.verify(out_dir)
