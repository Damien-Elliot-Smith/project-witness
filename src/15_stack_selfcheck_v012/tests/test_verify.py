import os

from stack_selfcheck_lib import canonical, verifier
from stack_selfcheck_lib.errors import VerifyError
from tests._helpers import TempCase


class TestVerify(TempCase):
    def _out(self):
        return self.build_output(self.inventory())

    def _append(self, path):
        canonical.atomic_write_bytes(path, canonical.read_bytes(path) + b" ")

    def test_valid_verifies(self):
        self.assertTrue(verifier.verify(self._out()).ok)

    def test_mutated_report_fails(self):
        out = self._out(); self._append(os.path.join(out, "stack_selfcheck_report.json"))
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_mutated_steps_fails(self):
        out = self._out(); self._append(os.path.join(out, "stack_selfcheck_steps.json"))
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_unknown_top_level_fails(self):
        out = self._out(); canonical.atomic_write_bytes(os.path.join(out, "x.txt"), b"x")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_invalid_stack_selfcheck_status_fails(self):
        out = self._out(); self.edit_report(out, stack_selfcheck_status="FAILED_INVENTORY_INVALID")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_invalid_inventory_status_fails(self):
        out = self._out(); self.edit_report(out, inventory_status="FAILED_INVENTORY_INVALID")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def _bool_false(self, field):
        out = self._out(); self.edit_report(out, **{field: False})
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_required_components_present_false_fails(self):
        self._bool_false("required_components_present")

    def test_component_versions_consistent_false_fails(self):
        self._bool_false("component_versions_consistent")

    def test_component_roots_present_false_fails(self):
        self._bool_false("component_roots_present")

    def test_zip_sidecars_valid_false_fails(self):
        self._bool_false("zip_sidecars_valid")

    def test_documentation_boundaries_present_false_fails(self):
        self._bool_false("documentation_boundaries_present")

    def test_truth_boundary_valid_false_fails(self):
        self._bool_false("truth_boundary_valid")

    def test_duplicate_checked_component_id_fails(self):
        out = self._out()
        rep = canonical.load_json(os.path.join(out, "stack_selfcheck_report.json"))
        rep["checked_components"][1]["component_id"] = rep["checked_components"][0]["component_id"]
        canonical.write_canonical(os.path.join(out, "stack_selfcheck_report.json"), rep)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_absolute_path_in_report_fails(self):
        out = self._out()
        rep = canonical.load_json(os.path.join(out, "stack_selfcheck_report.json"))
        rep["checked_components"][0]["note"] = "/abs/path/here"
        canonical.write_canonical(os.path.join(out, "stack_selfcheck_report.json"), rep)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_wrong_step_order_fails(self):
        out = self._out()
        steps = canonical.load_json(os.path.join(out, "stack_selfcheck_steps.json"))
        steps["steps"][0], steps["steps"][1] = steps["steps"][1], steps["steps"][0]
        canonical.write_canonical(os.path.join(out, "stack_selfcheck_steps.json"), steps)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_passed_with_skipped_step_fails(self):
        out = self._out()
        steps = canonical.load_json(os.path.join(out, "stack_selfcheck_steps.json"))
        steps["steps"][8]["status"] = "SKIPPED_AFTER_FAILURE"
        canonical.write_canonical(os.path.join(out, "stack_selfcheck_steps.json"), steps)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_failed_then_completed_fails(self):
        out = self._out()
        steps = canonical.load_json(os.path.join(out, "stack_selfcheck_steps.json"))
        steps["steps"][3]["status"] = "FAILED"
        canonical.write_canonical(os.path.join(out, "stack_selfcheck_steps.json"), steps)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)
