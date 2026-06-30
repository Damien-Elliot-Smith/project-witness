import os

from stack_verifier_lib import canonical, verifier
from stack_verifier_lib.errors import VerifyError
from tests._helpers import TempCase, COORD, COMP


class TestVerify(TempCase):
    def _out(self, manifest=False):
        if manifest:
            src = self.companion_source(); man = self.manifest_output(COMP, src)
            return self.build_output(COMP, src, man)
        return self.build_output(COORD, self.coord_source())

    def _append(self, path):
        canonical.atomic_write_bytes(path, canonical.read_bytes(path) + b" ")

    def test_valid_verifies(self):
        self.assertTrue(verifier.verify(self._out()).ok)

    def test_valid_with_manifest_verifies(self):
        self.assertTrue(verifier.verify(self._out(manifest=True)).ok)

    def test_mutated_report_fails(self):
        out = self._out(); self._append(os.path.join(out, "stack_verification_report.json"))
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_mutated_steps_fails(self):
        out = self._out(); self._append(os.path.join(out, "stack_verification_steps.json"))
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_unknown_top_level_fails(self):
        out = self._out(); canonical.atomic_write_bytes(os.path.join(out, "x.txt"), b"x")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_invalid_stack_status_fails(self):
        out = self._out(); self.edit_report(out, stack_verification_status="FAILED_SOURCE_VERIFY")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_invalid_source_status_fails(self):
        out = self._out(); self.edit_report(out, source_status="FAILED_SOURCE_VERIFY")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_invalid_manifest_status_fails(self):
        out = self._out(); self.edit_report(out, manifest_status="WEIRD")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_invalid_case_id_fails(self):
        out = self._out(); self.edit_report(out, case_id="../bad")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_invalid_evidence_id_fails(self):
        out = self._out(); self.edit_report(out, evidence_id="a/b")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_wrong_action_type_fails(self):
        out = self._out(); self.edit_report(out, action_type="WRITE_FILE")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_boolean_case_id_consistent_false_fails(self):
        out = self._out(); self.edit_report(out, case_id_consistent=False)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_boolean_evidence_id_consistent_false_fails(self):
        out = self._out(); self.edit_report(out, evidence_id_consistent=False)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_boolean_checksums_valid_false_fails(self):
        out = self._out(); self.edit_report(out, checksums_valid=False)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_boolean_atlas_vocabulary_valid_false_fails(self):
        out = self._out(); self.edit_report(out, atlas_vocabulary_valid=False)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_boolean_truth_boundary_valid_false_fails(self):
        out = self._out(); self.edit_report(out, truth_boundary_valid=False)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_manifest_verified_requires_consistent(self):
        out = self._out(manifest=True); self.edit_report(out, manifest_consistent=False)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_absolute_artifact_path_fails(self):
        out = self._out()
        rep = canonical.load_json(os.path.join(out, "stack_verification_report.json"))
        rep["checked_artifacts"][0]["relative_path"] = "/abs/x.json"
        canonical.write_canonical(os.path.join(out, "stack_verification_report.json"), rep)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_duplicate_artifact_id_fails(self):
        out = self._out()
        rep = canonical.load_json(os.path.join(out, "stack_verification_report.json"))
        rep["checked_artifacts"][1]["artifact_id"] = rep["checked_artifacts"][0]["artifact_id"]
        rep["checked_artifacts"][1]["source_label"] = rep["checked_artifacts"][0]["source_label"]
        canonical.write_canonical(os.path.join(out, "stack_verification_report.json"), rep)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_duplicate_artifact_path_fails(self):
        out = self._out()
        rep = canonical.load_json(os.path.join(out, "stack_verification_report.json"))
        rep["checked_artifacts"][1]["relative_path"] = rep["checked_artifacts"][0]["relative_path"]
        rep["checked_artifacts"][1]["source_label"] = rep["checked_artifacts"][0]["source_label"]
        canonical.write_canonical(os.path.join(out, "stack_verification_report.json"), rep)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)
