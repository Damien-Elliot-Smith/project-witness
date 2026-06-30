"""Companion CLI v0.3 orchestration: wrap Coordinator Workflow v0.3."""

import os

from . import (canonical, validation, request_builder, report as report_mod,
               steps as steps_mod, checksums, coordinator_output, verifier,
               versions)
from .errors import (
    COMPANION_COMPLETED, FAILED_INPUT_VALIDATION, FAILED_COORDINATOR_RUN,
    FAILED_COORDINATOR_VERIFY, FAILED_ATLAS_VALIDATION, FAILED_COMPANION_VERIFY,
    STEP_COMPLETED)

OUT_REQUEST = "workflow_request.json"
OUT_REPORT = "companion_report.json"
OUT_STEPS = "companion_steps.json"
OUT_CHECKSUMS = "companion_checksums.txt"
COORD_SUBDIR = "coordinator_output"


class CompanionOutcome:
    def __init__(self, companion_status, out_dir):
        self.companion_status = companion_status
        self.out_dir = out_dir
        self.completed = (companion_status == COMPANION_COMPLETED)


def _write_outputs(out_dir, companion_status, fields, step_statuses, case_id):
    report = report_mod.build_report(dict(fields, companion_status=companion_status))
    report_mod.write_report(os.path.join(out_dir, OUT_REPORT), report)
    steps_obj = steps_mod.build_steps(step_statuses, case_id)
    canonical.write_canonical(os.path.join(out_dir, OUT_STEPS), steps_obj)
    present = checksums.present_paths(out_dir)
    canonical.atomic_write_bytes(
        os.path.join(out_dir, OUT_CHECKSUMS),
        checksums.build_checksums_text(out_dir, present))


def _validate_inputs(p):
    if not validation.is_safe_token(p["case_id"]):
        return "unsafe case-id"
    if not validation.is_safe_token(p["evidence_id"]):
        return "unsafe evidence-id"
    if not validation.is_safe_token(p["case_directory_name"]):
        return "unsafe case-directory-name"
    if not validation.evidence_file_ok(p["evidence_file"]):
        return "evidence file missing / not a regular file / symlink / directory"
    if not validation.is_dir(p["allowed_root"]):
        return "allowed-root missing"
    if not validation.is_dir(p["coordinator_root"]):
        return "coordinator-root missing"
    for key in versions.COMPONENT_ROOT_KEYS:
        if not validation.is_dir(p["component_roots"][key]):
            return "component root missing: %s" % key
    if not validation.output_dir_ok(p["out"]):
        return "output directory is not empty"
    return None


def create_evidence_case(params, runner):
    out_dir = params["out"]
    requested_case_id = params["case_id"]
    evidence_id = params["evidence_id"]

    base = {
        "requested_case_id": requested_case_id,
        "evidence_id": evidence_id,
        "case_id": None,
        "workflow_type": versions.WORKFLOW_TYPE,
        "action_type": versions.ACTION_TYPE,
        "coordinator_workflow_version": versions.COORDINATOR_WORKFLOW_VERSION,
        "coordinator_workflow_status": None,
        "atlas_validation_status": None,
        "atlas_registry_status": None,
    }

    # step_001 VALIDATE_INPUTS
    err = _validate_inputs(params)
    if err is not None:
        os.makedirs(out_dir, exist_ok=True)
        _write_outputs(out_dir, FAILED_INPUT_VALIDATION, base,
                       steps_mod.statuses_with_failure_at(0),
                       requested_case_id)
        return CompanionOutcome(FAILED_INPUT_VALIDATION, out_dir)

    os.makedirs(out_dir, exist_ok=True)

    # step_002 WRITE_COORDINATOR_V03_REQUEST
    request = request_builder.build_request(
        requested_case_id, evidence_id, params["evidence_file"],
        params["allowed_root"], params["case_directory_name"],
        params["component_roots"])
    canonical.write_canonical(os.path.join(out_dir, OUT_REQUEST), request)

    # step_003 RUN_ATLAS_VALIDATED_WORKFLOW
    coord_dir = os.path.join(out_dir, COORD_SUBDIR)
    result = runner.run(request, coord_dir)
    if not result.ok:
        status = (FAILED_ATLAS_VALIDATION
                  if result.workflow_status == "FAILED_ATLAS_VALIDATION"
                  else FAILED_COORDINATOR_RUN)
        fields = dict(base, coordinator_workflow_status=result.workflow_status)
        _write_outputs(out_dir, status, fields,
                       steps_mod.statuses_with_failure_at(2), requested_case_id)
        return CompanionOutcome(status, out_dir)

    # step_004 VERIFY_COORDINATOR_V03_OUTPUT
    if not runner.verify(coord_dir):
        fields = dict(base, coordinator_workflow_status=result.workflow_status)
        _write_outputs(out_dir, FAILED_COORDINATOR_VERIFY, fields,
                       steps_mod.statuses_with_failure_at(3), requested_case_id)
        return CompanionOutcome(FAILED_COORDINATOR_VERIFY, out_dir)

    # step_005 MIRROR_ATLAS_TERMS
    creport = coordinator_output.read_workflow_report(coord_dir)
    case_id = creport.get("case_id")
    fields = dict(base)
    fields["case_id"] = case_id
    fields["coordinator_workflow_status"] = creport.get("workflow_status")
    fields["atlas_validation_status"] = creport.get("atlas_validation_status")
    fields["atlas_registry_status"] = creport.get("atlas_registry_status")
    fields["workflow_type"] = creport.get("workflow_type", versions.WORKFLOW_TYPE)
    for f in ("sentinel_status", "aletheia_status", "bridge_status",
              "odin_reasoning_status", "case_bundle_status"):
        fields[f] = creport.get(f)

    # step_006 WRITE_COMPANION_REPORT + step_007 VERIFY_COMPANION_OUTPUT
    _write_outputs(out_dir, COMPANION_COMPLETED, fields,
                   steps_mod.all_completed(), case_id)
    try:
        verifier.verify(out_dir)
    except Exception:
        _write_outputs(out_dir, FAILED_COMPANION_VERIFY, fields,
                       steps_mod.statuses_with_failure_at(6), case_id)
        return CompanionOutcome(FAILED_COMPANION_VERIFY, out_dir)

    return CompanionOutcome(COMPANION_COMPLETED, out_dir)
