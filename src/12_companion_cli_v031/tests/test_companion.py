import os

from companion_lib import canonical
from companion_lib.coordinator_runner import FakeCoordinatorRunner
from companion_lib.errors import (
    COMPANION_COMPLETED, FAILED_COORDINATOR_RUN, FAILED_COORDINATOR_VERIFY,
    FAILED_ATLAS_VALIDATION, ATLAS_VALIDATED, REGISTRY_VERIFIED,
    ODIN_CONTRADICTION, STEP_COMPLETED, STEP_FAILED, STEP_SKIPPED)
from tests._helpers import TempCase

_REQUIRED = ("workflow_request.json", "companion_report.json",
             "companion_steps.json", "companion_checksums.txt")


def _report(out):
    return canonical.load_json(os.path.join(out, "companion_report.json"))


def _steps(out):
    return canonical.load_json(os.path.join(out, "companion_steps.json"))["steps"]


class TestCompanion(TempCase):
    def test_successful_run_writes_all(self):
        oc = self.run_companion()
        for f in _REQUIRED:
            self.assertTrue(os.path.isfile(os.path.join(oc.out_dir, f)), f)
        self.assertTrue(os.path.isdir(os.path.join(oc.out_dir, "coordinator_output")))

    def test_coordinator_run_failure_short_circuits(self):
        oc = self.run_companion(runner=FakeCoordinatorRunner(
            run_ok=False, workflow_status="FAILED_SENTINEL"))
        self.assertEqual(oc.companion_status, FAILED_COORDINATOR_RUN)
        steps = _steps(oc.out_dir)
        self.assertEqual(steps[2]["status"], STEP_FAILED)
        self.assertTrue(all(s["status"] == STEP_SKIPPED for s in steps[3:]))

    def test_coordinator_verify_failure_short_circuits(self):
        oc = self.run_companion(runner=FakeCoordinatorRunner(verify_ok=False))
        self.assertEqual(oc.companion_status, FAILED_COORDINATOR_VERIFY)
        self.assertEqual(_steps(oc.out_dir)[3]["status"], STEP_FAILED)

    def test_atlas_validation_failure_maps(self):
        oc = self.run_companion(runner=FakeCoordinatorRunner(
            run_ok=False, workflow_status="FAILED_ATLAS_VALIDATION"))
        self.assertEqual(oc.companion_status, FAILED_ATLAS_VALIDATION)

    def test_seven_step_order(self):
        oc = self.run_companion()
        ids = [s["step_id"] for s in _steps(oc.out_dir)]
        self.assertEqual(ids, ["step_%03d" % i for i in range(1, 8)])
        self.assertTrue(all(s["status"] == STEP_COMPLETED for s in _steps(oc.out_dir)))

    def test_mirror_atlas_validation_status(self):
        oc = self.run_companion()
        self.assertEqual(_report(oc.out_dir)["atlas_validation_status"], ATLAS_VALIDATED)

    def test_mirror_atlas_registry_status(self):
        oc = self.run_companion()
        self.assertEqual(_report(oc.out_dir)["atlas_registry_status"], REGISTRY_VERIFIED)

    def test_mirror_workflow_and_action_type(self):
        rep = _report(self.run_companion().out_dir)
        self.assertEqual(rep["workflow_type"], "CREATE_EVIDENCE_REASONING_CASE")
        self.assertEqual(rep["action_type"], "CREATE_DIRECTORY")

    def test_case_id_preserved(self):
        oc = self.run_companion()
        rep = _report(oc.out_dir)
        creport = canonical.load_json(
            os.path.join(oc.out_dir, "coordinator_output", "workflow_report.json"))
        self.assertEqual(rep["case_id"], creport["case_id"])

    def test_evidence_id_preserved(self):
        self.assertEqual(_report(self.run_companion().out_dir)["evidence_id"],
                         "evidence_001")

    def test_report_canonical(self):
        oc = self.run_companion()
        raw = canonical.read_bytes(os.path.join(oc.out_dir, "companion_report.json"))
        self.assertTrue(canonical.is_canonical_bytes(raw))

    def test_steps_canonical(self):
        oc = self.run_companion()
        raw = canonical.read_bytes(os.path.join(oc.out_dir, "companion_steps.json"))
        self.assertTrue(canonical.is_canonical_bytes(raw))

    def test_checksums_written(self):
        oc = self.run_companion()
        self.assertTrue(os.path.isfile(
            os.path.join(oc.out_dir, "companion_checksums.txt")))

    def test_odin_consistent_accepted(self):
        oc = self.run_companion(runner=FakeCoordinatorRunner(odin_status="CONSISTENT"))
        self.assertEqual(oc.companion_status, COMPANION_COMPLETED)

    def test_odin_contradiction_accepted(self):
        oc = self.run_companion(runner=FakeCoordinatorRunner(odin_status=ODIN_CONTRADICTION))
        self.assertEqual(oc.companion_status, COMPANION_COMPLETED)
