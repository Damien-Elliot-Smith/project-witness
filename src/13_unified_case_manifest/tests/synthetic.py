"""Synthetic Coordinator v0.3 / Companion v0.3 source outputs for tests and
selfcheck. Standard library only; no real frozen components, no subprocesses.

The synthetic Atlas registry mirrors the frozen Atlas Registry v0.1 vocabulary:
it INCLUDES COMPANION_COMPLETED and deliberately EXCLUDES ATLAS_VALIDATED (which
is the Coordinator v0.3 validation result, not an Atlas term).
"""

import hashlib
import json
import os

_COMPONENTS = (
    "sentinel_core", "histor_lite", "aletheia_evidence_bundle",
    "aletheia_odin_bridge", "odin_claim_reasoner",
    "histor_lite_aletheia_importer", "histor_lite_odin_importer",
    "case_bundle_v02", "coordinator_workflow_v02", "atlas_registry",
)
_STATUS_GROUPS = (
    ("PASS_STRICT", "sentinel_statuses"),
    ("VERIFIED_PRESENT", "aletheia_statuses"),
    ("CONVERTED", "bridge_statuses"),
    ("CONSISTENT", "odin_reasoning_statuses"),
    ("CONTRADICTION_DETECTED", "odin_reasoning_statuses"),
    ("INVALID_INPUT", "odin_reasoning_statuses"),
    ("IMPORTED_VERIFIED_SENTINEL", "histor_import_statuses"),
    ("IMPORTED_VERIFIED_ALETHEIA", "histor_import_statuses"),
    ("IMPORTED_VERIFIED_ODIN", "histor_import_statuses"),
    ("BUNDLED_VERIFIED_CASE", "case_bundle_statuses"),
    ("WORKFLOW_COMPLETED", "coordinator_statuses"),
    ("COMPANION_COMPLETED", "companion_statuses"),
    ("REGISTRY_VERIFIED", "verification_statuses"),
    ("COMPLETED", "step_statuses"),
    ("FAILED", "step_statuses"),
    ("SKIPPED_AFTER_FAILURE", "step_statuses"),
)
_PREDICATES = ("evidence.present", "evidence.integrity_verified")
_COORD_PATHS = (
    "workflow_request_copy.json", "workflow_report.json", "workflow_steps.json",
    "atlas_validation_report.json", "atlas_registry_copy.json",
    "sentinel_run/run_report.json", "histor_sentinel_case/case_summary.json",
    "aletheia_bundle/evidence_manifest.json",
    "histor_aletheia_case/evidence_case_summary.json",
    "bridge_output/odin_claims.json", "odin_output/reasoning_report.json",
    "histor_odin_case/odin_case_summary.json",
    "case_bundle_v02/case_manifest.json",
)
_COORD_STEPS = tuple(("step_%03d" % i, "OP_%03d" % i) for i in range(1, 12))


def _canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def _atlas_canon(obj):
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False) + "\n").encode("utf-8")


def _write(path, raw):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(raw)


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def derive_case_id(name):
    return "case_" + hashlib.sha256(name.encode("utf-8")).hexdigest()[:16]


def build_registry(omit_status=None, omit_predicate=None,
                   truth_claim_status=False, truth_claim_predicate=False,
                   forbidden_action=None):
    action_types = [{"action_type": "CREATE_DIRECTORY",
                     "introduced_by_component": "sentinel_core"}]
    if forbidden_action:
        action_types.append({"action_type": forbidden_action,
                             "introduced_by_component": "sentinel_core"})
    statuses = []
    for name, group in _STATUS_GROUPS:
        if name == omit_status:
            continue
        entry = {"status": name, "status_group": group, "truth_claim": False}
        if truth_claim_status and name == "PASS_STRICT":
            entry["truth_claim"] = True
        statuses.append(entry)
    predicates = []
    for pred in _PREDICATES:
        if pred == omit_predicate:
            continue
        entry = {"predicate": pred, "truth_claim": False}
        if truth_claim_predicate and pred == "evidence.present":
            entry["truth_claim"] = True
        predicates.append(entry)
    return {
        "atlas_registry_version": "0.1.0",
        "registry_id": "project_witness_local_v1_registry",
        "components": [{"component_id": c, "frozen_status": "frozen"}
                       for c in _COMPONENTS],
        "workflow_types": [{"workflow_type": "CREATE_EVIDENCE_REASONING_CASE"}],
        "action_types": action_types,
        "statuses": statuses,
        "claim_predicates": predicates,
        "case_record_types": [],
        "known_limitations": ["Atlas Registry v0.1 is a read-only registry."],
    }


def build_coordinator_source(coord_dir, case_directory_name="case_001",
                             requested_case_id="case_001",
                             evidence_id="evidence_001",
                             workflow_status="WORKFLOW_COMPLETED",
                             atlas_validation_status="ATLAS_VALIDATED",
                             sentinel_status="PASS_STRICT",
                             aletheia_status="VERIFIED_PRESENT",
                             bridge_status="CONVERTED",
                             odin_status="CONSISTENT",
                             case_bundle_status="BUNDLED_VERIFIED_CASE",
                             case_id_override=None,
                             manifest_case_id=None, manifest_evidence_id=None,
                             registry_opts=None):
    os.makedirs(coord_dir, exist_ok=True)
    case_id = case_id_override or derive_case_id(case_directory_name)
    registry = build_registry(**(registry_opts or {}))
    _write(os.path.join(coord_dir, "atlas_registry_copy.json"),
           _atlas_canon(registry))

    def w(rel, obj):
        _write(os.path.join(coord_dir, rel), _canon(obj))

    request = {"coordinator_workflow_request_version": "0.3.0",
               "workflow_type": "CREATE_EVIDENCE_REASONING_CASE",
               "requested_case_id": requested_case_id, "evidence_id": evidence_id,
               "case_directory_name": case_directory_name}
    w("workflow_request_copy.json", request)
    w("atlas_validation_report.json", {
        "atlas_validation_version": "0.1.0",
        "atlas_registry_status": "REGISTRY_VERIFIED",
        "atlas_validation_status": atlas_validation_status})
    w("workflow_report.json", {
        "coordinator_workflow_version": "0.3.0", "workflow_status": workflow_status,
        "requested_case_id": requested_case_id, "case_id": case_id,
        "evidence_id": evidence_id, "workflow_type": "CREATE_EVIDENCE_REASONING_CASE",
        "atlas_validation_status": atlas_validation_status,
        "atlas_registry_status": "REGISTRY_VERIFIED",
        "sentinel_status": sentinel_status, "aletheia_status": aletheia_status,
        "bridge_status": bridge_status, "odin_reasoning_status": odin_status,
        "histor_sentinel_status": "IMPORTED_VERIFIED_SENTINEL",
        "histor_aletheia_status": "IMPORTED_VERIFIED_ALETHEIA",
        "histor_odin_status": "IMPORTED_VERIFIED_ODIN",
        "case_bundle_status": case_bundle_status})
    w("workflow_steps.json", {"coordinator_workflow_steps_version": "0.3.0",
        "steps": [{"step_id": sid, "operation": op, "status": "COMPLETED"}
                  for sid, op in _COORD_STEPS]})
    w("sentinel_run/run_report.json", {"sentinel_status": sentinel_status, "case_id": case_id})
    w("histor_sentinel_case/case_summary.json", {"case_id": case_id})
    w("aletheia_bundle/evidence_manifest.json", {"case_id": case_id, "evidence_id": evidence_id})
    w("histor_aletheia_case/evidence_case_summary.json", {"case_id": case_id})
    w("bridge_output/odin_claims.json", {"case_id": case_id, "predicates": list(_PREDICATES)})
    w("odin_output/reasoning_report.json", {"odin_reasoning_status": odin_status, "case_id": case_id})
    w("histor_odin_case/odin_case_summary.json", {"case_id": case_id})
    w("case_bundle_v02/case_manifest.json", {
        "case_bundle_status": case_bundle_status,
        "case_id": manifest_case_id or case_id,
        "evidence_id": manifest_evidence_id or evidence_id})

    present = [p for p in _COORD_PATHS if os.path.isfile(os.path.join(coord_dir, p))]
    lines = ["%s  %s" % (_sha(os.path.join(coord_dir, p)), p) for p in present]
    _write(os.path.join(coord_dir, "workflow_checksums.txt"),
           ("\n".join(lines) + "\n").encode("utf-8"))
    return case_id


def build_companion_source(root, companion_status="COMPANION_COMPLETED",
                           companion_case_id=None, companion_evidence_id=None,
                           **coord_kwargs):
    os.makedirs(root, exist_ok=True)
    coord_dir = os.path.join(root, "coordinator_output")
    case_id = build_coordinator_source(coord_dir, **coord_kwargs)
    evidence_id = coord_kwargs.get("evidence_id", "evidence_001")
    requested = coord_kwargs.get("requested_case_id", "case_001")

    def w(rel, obj):
        _write(os.path.join(root, rel), _canon(obj))

    w("workflow_request.json", {
        "coordinator_workflow_request_version": "0.3.0",
        "workflow_type": "CREATE_EVIDENCE_REASONING_CASE",
        "requested_case_id": requested,
        "evidence_id": companion_evidence_id or evidence_id})
    w("companion_report.json", {
        "companion_cli_version": "0.3.0", "command": "create-evidence-case",
        "companion_status": companion_status, "requested_case_id": requested,
        "case_id": companion_case_id or case_id,
        "evidence_id": companion_evidence_id or evidence_id})
    w("companion_steps.json", {"companion_steps_version": "0.3.0",
        "case_id": companion_case_id or case_id,
        "steps": [{"step_id": "step_%03d" % i, "component": "companion_cli",
                   "operation": "OP", "status": "COMPLETED"} for i in range(1, 8)]})
    comp_paths = ("workflow_request.json", "companion_report.json",
                  "companion_steps.json",
                  "coordinator_output/workflow_report.json",
                  "coordinator_output/workflow_steps.json",
                  "coordinator_output/atlas_validation_report.json",
                  "coordinator_output/atlas_registry_copy.json",
                  "coordinator_output/case_bundle_v02/case_manifest.json")
    lines = ["%s  %s" % (_sha(os.path.join(root, p)), p) for p in comp_paths]
    _write(os.path.join(root, "companion_checksums.txt"),
           ("\n".join(lines) + "\n").encode("utf-8"))
    return case_id
