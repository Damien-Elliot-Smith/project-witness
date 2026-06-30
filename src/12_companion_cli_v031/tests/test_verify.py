import os
import shutil

from companion_lib import canonical, verifier
from companion_lib.coordinator_runner import FakeCoordinatorRunner
from companion_lib.errors import VerifyError, COMPANION_COMPLETED
from tests._helpers import TempCase


def _p(out, *parts):
    return os.path.join(out, *parts)


class TestVerify(TempCase):
    def _ok(self, **runner_kwargs):
        oc = self.run_companion(runner=FakeCoordinatorRunner(**runner_kwargs))
        self.assertEqual(oc.companion_status, COMPANION_COMPLETED)
        return oc.out_dir

    def _append(self, path):
        canonical.atomic_write_bytes(path, canonical.read_bytes(path) + b" ")

    def test_valid_verifies(self):
        self.assertTrue(verifier.verify(self._ok()).ok)

    def test_mutated_companion_report_fails(self):
        out = self._ok(); self._append(_p(out, "companion_report.json"))
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_mutated_companion_steps_fails(self):
        out = self._ok(); self._append(_p(out, "companion_steps.json"))
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_mutated_workflow_request_fails(self):
        out = self._ok(); self._append(_p(out, "workflow_request.json"))
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_mutated_coordinator_report_fails(self):
        out = self._ok(); self._append(_p(out, "coordinator_output", "workflow_report.json"))
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_mutated_coordinator_atlas_validation_fails(self):
        out = self._ok(); self._append(_p(out, "coordinator_output", "atlas_validation_report.json"))
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_mutated_coordinator_atlas_copy_fails(self):
        out = self._ok(); self._append(_p(out, "coordinator_output", "atlas_registry_copy.json"))
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_unknown_top_level_file_fails(self):
        out = self._ok()
        canonical.atomic_write_bytes(_p(out, "extra.txt"), b"x")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_missing_coordinator_output_fails(self):
        out = self._ok()
        shutil.rmtree(_p(out, "coordinator_output"))
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def _mutate_companion_report(self, out, **changes):
        rep = canonical.load_json(_p(out, "companion_report.json"))
        rep.update(changes)
        canonical.write_canonical(_p(out, "companion_report.json"), rep)
        self.rebuild_checksums(out)

    def test_wrong_step_order_fails(self):
        out = self._ok()
        steps = canonical.load_json(_p(out, "companion_steps.json"))
        steps["steps"][0], steps["steps"][1] = steps["steps"][1], steps["steps"][0]
        canonical.write_canonical(_p(out, "companion_steps.json"), steps)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_completed_with_skipped_step_fails(self):
        out = self._ok()
        steps = canonical.load_json(_p(out, "companion_steps.json"))
        steps["steps"][6]["status"] = "SKIPPED_AFTER_FAILURE"
        canonical.write_canonical(_p(out, "companion_steps.json"), steps)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_failed_then_completed_fails(self):
        out = self._ok()
        steps = canonical.load_json(_p(out, "companion_steps.json"))
        steps["steps"][2]["status"] = "FAILED"
        canonical.write_canonical(_p(out, "companion_steps.json"), steps)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_non_workflow_completed_fails(self):
        out = self._ok()
        self._mutate_companion_report(out, coordinator_workflow_status="FAILED_ODIN")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_non_atlas_validated_fails(self):
        out = self._ok()
        self._mutate_companion_report(out, atlas_validation_status="FAILED_ATLAS_VERIFY")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_non_registry_verified_fails(self):
        out = self._ok()
        self._mutate_companion_report(out, atlas_registry_status="REGISTRY_NOT_VERIFIED")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_mirror_mismatch_fails(self):
        out = self._ok()
        # change a mirrored field that is not otherwise pinned by a fixed value
        self._mutate_companion_report(out, sentinel_status="VERIFIED_PRESENT")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def _mutate_registry(self, out, **opts):
        from companion_lib import fixtures
        registry = fixtures.build_registry(**opts)
        canonical.atomic_write_bytes(
            _p(out, "coordinator_output", "atlas_registry_copy.json"),
            canonical.atlas_canonical_bytes(registry))
        self.rebuild_checksums(out)

    def test_observed_status_not_in_atlas_fails(self):
        out = self._ok()
        self._mutate_registry(out, omit_status="CONSISTENT")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_observed_predicate_not_in_atlas_fails(self):
        out = self._ok()
        self._mutate_registry(out, omit_predicate="evidence.present")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_atlas_truth_claim_status_fails(self):
        out = self._ok()
        self._mutate_registry(out, truth_claim_status=True)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_atlas_truth_claim_predicate_fails(self):
        out = self._ok()
        self._mutate_registry(out, truth_claim_predicate=True)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_forbidden_action_in_atlas_fails(self):
        out = self._ok()
        self._mutate_registry(out, forbidden_action="WRITE_FILE")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_odin_invalid_input_fails(self):
        out = self._ok()
        # mutate both companion and coordinator reports to keep mirror equal
        for rel in ("companion_report.json", "coordinator_output/workflow_report.json"):
            obj = canonical.load_json(_p(out, rel))
            key = "odin_reasoning_status"
            obj[key] = "INVALID_INPUT"
            canonical.write_canonical(_p(out, rel), obj)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_case_bundle_non_bundled_fails(self):
        out = self._ok()
        for rel in ("companion_report.json", "coordinator_output/workflow_report.json"):
            obj = canonical.load_json(_p(out, rel))
            obj["case_bundle_status"] = "UNBUNDLED"
            canonical.write_canonical(_p(out, rel), obj)
        # also the coordinator case manifest
        man = canonical.load_json(_p(out, "coordinator_output/case_bundle_v02/case_manifest.json"))
        man["case_bundle_status"] = "UNBUNDLED"
        canonical.write_canonical(_p(out, "coordinator_output/case_bundle_v02/case_manifest.json"), man)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_case_id_mismatch_fails(self):
        out = self._ok()
        man = canonical.load_json(_p(out, "coordinator_output/case_bundle_v02/case_manifest.json"))
        man["case_id"] = "case_tampered00000"
        canonical.write_canonical(_p(out, "coordinator_output/case_bundle_v02/case_manifest.json"), man)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_evidence_id_mismatch_fails(self):
        out = self._ok()
        req = canonical.load_json(_p(out, "workflow_request.json"))
        req["evidence_id"] = "evidence_tampered"
        canonical.write_canonical(_p(out, "workflow_request.json"), req)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)
