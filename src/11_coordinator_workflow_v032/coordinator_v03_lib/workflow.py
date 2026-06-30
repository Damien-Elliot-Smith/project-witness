"""Coordinator Workflow v0.3 run engine: Atlas validation + the v0.2 workflow."""

import os

from . import (canonical, versions, atlas_validation, report as report_mod,
               steps as steps_mod, checksums)
from .component_runners import WorkflowContext
from .errors import (
    ATLAS_VALIDATED, REGISTRY_VERIFIED, REGISTRY_NOT_VERIFIED,
    WORKFLOW_COMPLETED, FAILED_ATLAS_VALIDATION, FAILED_SENTINEL,
    FAILED_HISTOR_SENTINEL, FAILED_ALETHEIA, FAILED_HISTOR_ALETHEIA,
    FAILED_BRIDGE, FAILED_ODIN, FAILED_HISTOR_ODIN,
    FAILED_CASE_BUNDLE_BUILD, FAILED_CASE_BUNDLE_VERIFY,
    STEP_COMPLETED,
)

OUT_REQUEST_COPY = "workflow_request_copy.json"
OUT_REPORT = "workflow_report.json"
OUT_STEPS = "workflow_steps.json"
OUT_CHECKSUMS = "workflow_checksums.txt"
OUT_ATLAS_VALIDATION = "atlas_validation_report.json"
OUT_ATLAS_COPY = "atlas_registry_copy.json"

# step index -> (runner method name, workflow failure status, report status field)
_COMPONENT_STEPS = (
    (1, "sentinel_create_directory", FAILED_SENTINEL, "sentinel_status"),
    (2, "histor_import_sentinel", FAILED_HISTOR_SENTINEL, "histor_sentinel_status"),
    (3, "aletheia_bundle", FAILED_ALETHEIA, "aletheia_status"),
    (4, "histor_import_aletheia", FAILED_HISTOR_ALETHEIA, "histor_aletheia_status"),
    (5, "bridge_convert", FAILED_BRIDGE, "bridge_status"),
    (6, "odin_reason", FAILED_ODIN, "odin_reasoning_status"),
    (7, "histor_import_odin", FAILED_HISTOR_ODIN, "histor_odin_status"),
    (8, "case_bundle_build", FAILED_CASE_BUNDLE_BUILD, "case_bundle_status"),
    (9, "case_bundle_verify", FAILED_CASE_BUNDLE_VERIFY, "case_bundle_verify_status"),
)


class RunOutcome:
    def __init__(self, workflow_status, out_dir):
        self.workflow_status = workflow_status
        self.out_dir = out_dir
        self.completed = (workflow_status == WORKFLOW_COMPLETED)


def _write_request_copy(out_dir, request):
    canonical.write_canonical(os.path.join(out_dir, OUT_REQUEST_COPY), request)


def _write_outputs(out_dir, report_fields, statuses):
    report = report_mod.build_report(report_fields)
    report_mod.write_report(os.path.join(out_dir, OUT_REPORT), report)
    steps_obj = steps_mod.build_steps(statuses)
    canonical.write_canonical(os.path.join(out_dir, OUT_STEPS), steps_obj)
    present = checksums.present_paths(out_dir)
    canonical.atomic_write_bytes(
        os.path.join(out_dir, OUT_CHECKSUMS),
        checksums.build_checksums_text(out_dir, present))


def run_workflow(request, out_dir, runner, verify_fn=atlas_validation.inprocess_verify):
    os.makedirs(out_dir, exist_ok=True)
    _write_request_copy(out_dir, request)

    atlas_root = request.get("component_roots", {}).get("atlas_registry_root")
    requested_case_id = request.get("requested_case_id")
    evidence_id = request.get("evidence_id")

    base_fields = {
        "requested_case_id": requested_case_id,
        "evidence_id": evidence_id,
        "workflow_type": request.get("workflow_type"),
        "case_id": None,
        "atlas_validation_status": None,
        "atlas_registry_status": REGISTRY_NOT_VERIFIED,
    }

    # step_001 ATLAS_VALIDATE_REGISTRY
    result = atlas_validation.validate(atlas_root, verify_fn=verify_fn)
    canonical.write_canonical(
        os.path.join(out_dir, OUT_ATLAS_VALIDATION), result.report)
    if result.registry_bytes is not None:
        canonical.atomic_write_bytes(
            os.path.join(out_dir, OUT_ATLAS_COPY), result.registry_bytes)

    base_fields["atlas_validation_status"] = result.status
    base_fields["atlas_registry_status"] = (
        REGISTRY_VERIFIED if result.report.get("atlas_registry_status") ==
        REGISTRY_VERIFIED else REGISTRY_NOT_VERIFIED)

    if not result.ok:
        fields = dict(base_fields)
        fields["workflow_status"] = FAILED_ATLAS_VALIDATION
        _write_outputs(out_dir, fields, steps_mod.statuses_with_failure_at(0))
        return RunOutcome(FAILED_ATLAS_VALIDATION, out_dir)

    # steps 2..10 — the v0.2 component workflow
    ctx = WorkflowContext(
        out_dir=out_dir,
        case_directory_name=request.get("case_directory_name"),
        evidence_id=evidence_id,
        evidence_file=request.get("evidence_file"))

    observed = {}
    for step_index, method_name, fail_status, field in _COMPONENT_STEPS:
        method = getattr(runner, method_name)
        res = method(ctx)
        if field == "case_bundle_verify_status":
            observed["case_bundle_status"] = res.status
        else:
            observed[field] = res.status
        if not res.ok:
            fields = dict(base_fields)
            fields["case_id"] = ctx.case_id
            fields.update(observed)
            fields["workflow_status"] = fail_status
            _write_outputs(out_dir, fields,
                           steps_mod.statuses_with_failure_at(step_index))
            return RunOutcome(fail_status, out_dir)

    # success: step_011 COORDINATOR_VERIFY_OUTPUT
    fields = dict(base_fields)
    fields["case_id"] = ctx.case_id
    fields.update(observed)
    fields["workflow_status"] = WORKFLOW_COMPLETED
    fields["final_bundle_path"] = "case_bundle_v02"
    _write_outputs(out_dir, fields, steps_mod.all_completed())
    return RunOutcome(WORKFLOW_COMPLETED, out_dir)
