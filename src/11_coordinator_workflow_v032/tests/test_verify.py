import os

from coordinator_v03_lib import canonical, verifier, checksums
from coordinator_v03_lib.component_runners import FakeComponentRunner
from coordinator_v03_lib.errors import VerifyError, WORKFLOW_COMPLETED
from tests._helpers import TempCase


def _p(out, name):
    return os.path.join(out, name)


class TestVerify(TempCase):
    def _completed(self):
        out, oc = self.run_wf()
        self.assertEqual(oc.workflow_status, WORKFLOW_COMPLETED)
        return out

    def test_valid_output_verifies(self):
        out = self._completed()
        self.assertTrue(verifier.verify(out).ok)

    def test_mutated_atlas_validation_fails(self):
        out = self._completed()
        path = _p(out, "atlas_validation_report.json")
        canonical.atomic_write_bytes(path, canonical.read_bytes(path) + b" ")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_mutated_atlas_copy_fails(self):
        out = self._completed()
        path = _p(out, "atlas_registry_copy.json")
        canonical.atomic_write_bytes(path, canonical.read_bytes(path) + b" ")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_mutated_report_fails(self):
        out = self._completed()
        path = _p(out, "workflow_report.json")
        canonical.atomic_write_bytes(path, canonical.read_bytes(path) + b" ")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_mutated_steps_fails(self):
        out = self._completed()
        path = _p(out, "workflow_steps.json")
        canonical.atomic_write_bytes(path, canonical.read_bytes(path) + b" ")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_mutated_request_copy_fails(self):
        out = self._completed()
        path = _p(out, "workflow_request_copy.json")
        canonical.atomic_write_bytes(path, canonical.read_bytes(path) + b" ")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_unknown_top_level_file_fails(self):
        out = self._completed()
        canonical.atomic_write_bytes(_p(out, "surprise.txt"), b"x")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_missing_required_folder_fails(self):
        out = self._completed()
        import shutil
        shutil.rmtree(_p(out, "odin_output"))
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_wrong_step_order_fails(self):
        out = self._completed()
        steps_obj = canonical.load_json(_p(out, "workflow_steps.json"))
        steps_obj["steps"][0], steps_obj["steps"][1] = (
            steps_obj["steps"][1], steps_obj["steps"][0])
        canonical.write_canonical(_p(out, "workflow_steps.json"), steps_obj)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_completed_with_skipped_step_fails(self):
        out = self._completed()
        steps_obj = canonical.load_json(_p(out, "workflow_steps.json"))
        steps_obj["steps"][10]["status"] = "SKIPPED_AFTER_FAILURE"
        canonical.write_canonical(_p(out, "workflow_steps.json"), steps_obj)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_failed_then_completed_step_fails(self):
        out = self._completed()
        steps_obj = canonical.load_json(_p(out, "workflow_steps.json"))
        steps_obj["steps"][2]["status"] = "FAILED"  # step3 FAILED but step4.. COMPLETED
        canonical.write_canonical(_p(out, "workflow_steps.json"), steps_obj)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_non_validated_atlas_status_fails(self):
        out = self._completed()
        rep = canonical.load_json(_p(out, "workflow_report.json"))
        rep["atlas_validation_status"] = "FAILED_ATLAS_VERIFY"
        canonical.write_canonical(_p(out, "workflow_report.json"), rep)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_non_registry_verified_fails(self):
        out = self._completed()
        rep = canonical.load_json(_p(out, "workflow_report.json"))
        rep["atlas_registry_status"] = "REGISTRY_NOT_VERIFIED"
        canonical.write_canonical(_p(out, "workflow_report.json"), rep)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_observed_status_not_in_atlas_fails(self):
        out = self._completed()
        registry = canonical.load_json(_p(out, "atlas_registry_copy.json"))
        registry["statuses"] = [s for s in registry["statuses"]
                                if s["status"] != "CONSISTENT"]
        canonical.atomic_write_bytes(
            _p(out, "atlas_registry_copy.json"),
            canonical.atlas_canonical_bytes(registry))
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_observed_predicate_not_in_atlas_fails(self):
        out = self._completed()
        registry = canonical.load_json(_p(out, "atlas_registry_copy.json"))
        registry["claim_predicates"] = [p for p in registry["claim_predicates"]
                                        if p["predicate"] != "evidence.present"]
        canonical.atomic_write_bytes(
            _p(out, "atlas_registry_copy.json"),
            canonical.atlas_canonical_bytes(registry))
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_case_id_mismatch_fails(self):
        out = self._completed()
        manifest = canonical.load_json(_p(out, "case_bundle_v02/case_manifest.json"))
        manifest["case_id"] = "case_tampered00000"
        canonical.write_canonical(_p(out, "case_bundle_v02/case_manifest.json"), manifest)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_evidence_id_mismatch_fails(self):
        out = self._completed()
        manifest = canonical.load_json(_p(out, "aletheia_bundle/evidence_manifest.json"))
        manifest["evidence_id"] = "evidence_tampered"
        canonical.write_canonical(_p(out, "aletheia_bundle/evidence_manifest.json"), manifest)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_missing_checksum_key_fails(self):
        out = self._completed()
        # drop one line from checksums -> missing key
        path = _p(out, "workflow_checksums.txt")
        lines = canonical.read_bytes(path).decode().splitlines()
        canonical.atomic_write_bytes(path, ("\n".join(lines[:-1]) + "\n").encode())
        with self.assertRaises(VerifyError):
            verifier.verify(out)
