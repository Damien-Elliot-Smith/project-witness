import os

from atlas_release_gate_lib import canonical, report as report_mod
from atlas_release_gate_lib.errors import (
    RELEASE_GATE_PASSED, REGISTRY_VERIFIED, EXPORT_VERIFIED)
from tests._helpers import TempCase


class TestReport(TempCase):
    def test_report_canonical(self):
        out_dir, outcome = self.run_gate()
        self.assertEqual(outcome.status, RELEASE_GATE_PASSED)
        raw = canonical.read_bytes(
            os.path.join(out_dir, "atlas_release_gate_report.json"))
        self.assertTrue(canonical.is_canonical_bytes(raw))

    def test_steps_canonical(self):
        out_dir, _ = self.run_gate()
        raw = canonical.read_bytes(
            os.path.join(out_dir, "atlas_release_gate_steps.json"))
        self.assertTrue(canonical.is_canonical_bytes(raw))

    def test_report_fields(self):
        rpt = report_mod.build_report(
            RELEASE_GATE_PASSED, REGISTRY_VERIFIED, EXPORT_VERIFIED,
            True, True, True, True)
        self.assertEqual(rpt["release_gate_version"]
                         if "release_gate_version" in rpt
                         else rpt["atlas_release_gate_version"], "0.1.0")
        self.assertEqual(rpt["checked_component"], "atlas_registry")
        self.assertIn("known_limitations", rpt)
        self.assertTrue(any("does not prove truth" in s.lower()
                            for s in rpt["known_limitations"]))

    def test_output_files_written(self):
        out_dir, _ = self.run_gate()
        for name in ("atlas_release_gate_report.json",
                     "atlas_release_gate_steps.json",
                     "atlas_release_gate_checksums.txt"):
            self.assertTrue(os.path.isfile(os.path.join(out_dir, name)))
        for name in ("atlas_registry_copy.json", "atlas_summary.json",
                     "atlas_checksums.txt"):
            self.assertTrue(os.path.isfile(
                os.path.join(out_dir, "atlas_export", name)))
