import os

from coordinator_v03_lib import canonical
from coordinator_v03_lib.component_runners import FakeComponentRunner
from coordinator_v03_lib.errors import (
    WORKFLOW_COMPLETED, FAILED_ATLAS_VALIDATION, FAILED_SENTINEL,
    FAILED_ODIN, FAILED_CASE_BUNDLE_BUILD, ODIN_CONSISTENT, ODIN_CONTRADICTION,
    ODIN_INVALID_INPUT, STEP_COMPLETED, STEP_FAILED, STEP_SKIPPED)
from tests._helpers import TempCase

_REQUIRED_DIRS = (
    "sentinel_run", "histor_sentinel_case", "aletheia_bundle",
    "histor_aletheia_case", "bridge_output", "odin_output",
    "histor_odin_case", "case_bundle_v02")
_REQUIRED_FILES = (
    "workflow_request_copy.json", "workflow_report.json", "workflow_steps.json",
    "workflow_checksums.txt", "atlas_validation_report.json",
    "atlas_registry_copy.json")


def _steps(out_dir):
    return canonical.load_json(os.path.join(out_dir, "workflow_steps.json"))["steps"]


def _report(out_dir):
    return canonical.load_json(os.path.join(out_dir, "workflow_report.json"))


class TestWorkflow(TempCase):
    def test_valid_request_accepted(self):
        _, oc = self.run_wf()
        self.assertEqual(oc.workflow_status, WORKFLOW_COMPLETED)

    def test_atlas_validation_report_written(self):
        out, _ = self.run_wf()
        av = canonical.load_json(os.path.join(out, "atlas_validation_report.json"))
        self.assertEqual(av["atlas_validation_status"], "ATLAS_VALIDATED")

    def test_atlas_registry_copy_written(self):
        out, _ = self.run_wf()
        raw = canonical.read_bytes(os.path.join(out, "atlas_registry_copy.json"))
        self.assertTrue(canonical.is_atlas_canonical_bytes(raw))

    def test_successful_workflow_writes_all(self):
        out, _ = self.run_wf()
        for f in _REQUIRED_FILES:
            self.assertTrue(os.path.isfile(os.path.join(out, f)), f)
        for d in _REQUIRED_DIRS:
            self.assertTrue(os.path.isdir(os.path.join(out, d)), d)

    def test_atlas_failure_short_circuits(self):
        out, oc = self.run_wf(atlas_opts={"break_verify": True})
        self.assertEqual(oc.workflow_status, FAILED_ATLAS_VALIDATION)
        steps = _steps(out)
        self.assertEqual(steps[0]["status"], STEP_FAILED)
        self.assertTrue(all(s["status"] == STEP_SKIPPED for s in steps[1:]))
        # no sentinel output produced
        self.assertFalse(os.path.isdir(os.path.join(out, "sentinel_run")))

    def test_lower_component_failure_short_circuits(self):
        out, oc = self.run_wf(runner=FakeComponentRunner(fail_op="SENTINEL_CREATE_DIRECTORY"))
        self.assertEqual(oc.workflow_status, FAILED_SENTINEL)
        steps = _steps(out)
        self.assertEqual(steps[0]["status"], STEP_COMPLETED)  # atlas ok
        self.assertEqual(steps[1]["status"], STEP_FAILED)     # sentinel failed
        self.assertTrue(all(s["status"] == STEP_SKIPPED for s in steps[2:]))

    def test_case_id_derived_and_propagated(self):
        out, _ = self.run_wf()
        rep = _report(out)
        case_id = rep["case_id"]
        self.assertTrue(case_id.startswith("case_"))
        for rel in ("sentinel_run/run_report.json",
                    "histor_sentinel_case/case_summary.json",
                    "case_bundle_v02/case_manifest.json"):
            obj = canonical.load_json(os.path.join(out, rel))
            self.assertEqual(obj["case_id"], case_id)

    def test_evidence_id_preserved(self):
        out, _ = self.run_wf(evidence_id="evidence_001")
        self.assertEqual(_report(out)["evidence_id"], "evidence_001")

    def test_observed_statuses_in_atlas(self):
        out, _ = self.run_wf()
        rep = _report(out)
        registry = canonical.load_json(os.path.join(out, "atlas_registry_copy.json"))
        atlas_statuses = {s["status"] for s in registry["statuses"]}
        for field in ("sentinel_status", "aletheia_status", "bridge_status",
                      "odin_reasoning_status", "case_bundle_status", "workflow_status"):
            self.assertIn(rep[field], atlas_statuses)

    def test_observed_predicates_in_atlas(self):
        out, _ = self.run_wf()
        registry = canonical.load_json(os.path.join(out, "atlas_registry_copy.json"))
        atlas_preds = {p["predicate"] for p in registry["claim_predicates"]}
        claims = canonical.load_json(os.path.join(out, "bridge_output/odin_claims.json"))
        for pred in claims["predicates"]:
            self.assertIn(pred, atlas_preds)

    def test_odin_consistent_accepted(self):
        _, oc = self.run_wf(runner=FakeComponentRunner(odin_status=ODIN_CONSISTENT))
        self.assertEqual(oc.workflow_status, WORKFLOW_COMPLETED)

    def test_odin_contradiction_accepted(self):
        _, oc = self.run_wf(runner=FakeComponentRunner(odin_status=ODIN_CONTRADICTION))
        self.assertEqual(oc.workflow_status, WORKFLOW_COMPLETED)

    def test_odin_invalid_input_fails(self):
        _, oc = self.run_wf(runner=FakeComponentRunner(odin_status=ODIN_INVALID_INPUT))
        self.assertEqual(oc.workflow_status, FAILED_ODIN)

    def test_case_bundle_non_bundled_fails(self):
        _, oc = self.run_wf(runner=FakeComponentRunner(case_bundle_status="UNBUNDLED"))
        self.assertEqual(oc.workflow_status, FAILED_CASE_BUNDLE_BUILD)
