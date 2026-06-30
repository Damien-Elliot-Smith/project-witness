import os

from stack_selfcheck_lib import canonical, report as report_mod, validation
from tests._helpers import TempCase


class TestReport(TempCase):
    def test_checked_components_recorded(self):
        report, checked = report_mod.build_selfcheck_report(self.inventory())
        self.assertEqual(len(checked), 22)
        for c in checked:
            self.assertEqual(c["check_status"], "COMPONENT_CHECKED")
            self.assertTrue(c["root_present"])

    def test_no_absolute_paths(self):
        report, _ = report_mod.build_selfcheck_report(self.inventory())
        self.assertTrue(validation.has_no_absolute_paths(report))

    def test_report_canonical(self):
        out = self.build_output(self.inventory())
        self.assertTrue(canonical.is_canonical_bytes(
            canonical.read_bytes(os.path.join(out, "stack_selfcheck_report.json"))))

    def test_steps_canonical(self):
        out = self.build_output(self.inventory())
        self.assertTrue(canonical.is_canonical_bytes(
            canonical.read_bytes(os.path.join(out, "stack_selfcheck_steps.json"))))

    def test_checksums_written(self):
        out = self.build_output(self.inventory())
        self.assertTrue(os.path.isfile(os.path.join(out, "stack_selfcheck_checksums.txt")))

    def test_component_count(self):
        report, _ = report_mod.build_selfcheck_report(self.inventory())
        self.assertEqual(report["component_count"], 22)
