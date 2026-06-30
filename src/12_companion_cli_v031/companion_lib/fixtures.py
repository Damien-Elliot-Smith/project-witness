"""Deterministic fixtures: a fake Atlas registry and a fake Coordinator v0.3
output folder. Used by the fake Coordinator runner, selfcheck, and unit tests so
the default suite needs no real frozen components and spawns no subprocesses.

The fake registry mirrors the frozen Atlas Registry v0.1 vocabulary that this
workflow observes. It INCLUDES COMPANION_COMPLETED (as the real Atlas does) and
deliberately does NOT include ATLAS_VALIDATED, because ATLAS_VALIDATED is the
Coordinator v0.3 validation result and is not an Atlas Registry v0.1 term.
"""

import hashlib
import os

from . import canonical, versions

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

# Coordinator v0.3 checksum paths (the 13 present in a completed run).
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

_COORD_STEP_PLAN = (
    ("step_001", "ATLAS_VALIDATE_REGISTRY"),
    ("step_002", "SENTINEL_CREATE_DIRECTORY"),
    ("step_003", "HISTOR_IMPORT_SENTINEL"),
    ("step_004", "ALETHEIA_BUNDLE_FILE"),
    ("step_005", "HISTOR_IMPORT_ALETHEIA"),
    ("step_006", "BRIDGE_CONVERT_ALETHEIA_TO_ODIN"),
    ("step_007", "ODIN_REASON"),
    ("step_008", "HISTOR_IMPORT_ODIN"),
    ("step_009", "CASE_BUNDLE_V02_BUILD"),
    ("step_010", "CASE_BUNDLE_V02_VERIFY"),
    ("step_011", "COORDINATOR_VERIFY_OUTPUT"),
)


def derive_case_id(case_directory_name):
    return "case_" + hashlib.sha256(
        case_directory_name.encode("utf-8")).hexdigest()[:16]


def build_registry(omit_status=None, omit_predicate=None,
                   truth_claim_status=False, truth_claim_predicate=False,
                   forbidden_action=None):
    action_types = [{"action_type": versions.ACTION_TYPE,
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
        entry = {"predicate": pred, "truth_claim": False,
                 "allowed_object_types": ["boolean"]}
        if truth_claim_predicate and pred == "evidence.present":
            entry["truth_claim"] = True
        predicates.append(entry)
    return {
        "atlas_registry_version": "0.1.0",
        "registry_id": "project_witness_local_v1_registry",
        "components": [{"component_id": c, "component_type": "frozen_module",
                        "component_version": "0.1.0", "frozen_status": "frozen"}
                       for c in _COMPONENTS],
        "workflow_types": [{"workflow_type": versions.WORKFLOW_TYPE,
                            "introduced_by_component": "coordinator_workflow_v02"}],
        "action_types": action_types,
        "statuses": statuses,
        "claim_predicates": predicates,
        "case_record_types": [],
        "known_limitations": ["Atlas Registry v0.1 is a read-only registry."],
    }


def _coord_known_limitations():
    return [
        "Coordinator Workflow v0.3 validates vocabulary against Atlas Registry v0.1.",
        "Atlas validation does not prove evidence contents are true.",
        "Atlas validation does not prove ODIN claims are true.",
        "Coordinator Workflow v0.3 does not use natural language or LLMs.",
        "Coordinator Workflow v0.3 does not sign or externally anchor outputs.",
        "Coordinator Workflow v0.3 supports one workflow at a time.",
    ]


def build_coordinator_output(coord_dir, request, atlas_validation_status="ATLAS_VALIDATED",
                             workflow_status="WORKFLOW_COMPLETED",
                             odin_status="CONSISTENT",
                             case_bundle_status="BUNDLED_VERIFIED_CASE",
                             registry_opts=None):
    """Write a faithful Coordinator v0.3 output folder under coord_dir."""
    os.makedirs(coord_dir, exist_ok=True)
    case_id = derive_case_id(request["case_directory_name"])
    evidence_id = request["evidence_id"]
    registry = build_registry(**(registry_opts or {}))

    def w(rel, obj):
        canonical.write_canonical(os.path.join(coord_dir, rel), obj)

    # registry copy keeps Atlas canonical (trailing newline)
    canonical.atomic_write_bytes(
        os.path.join(coord_dir, "atlas_registry_copy.json"),
        canonical.atlas_canonical_bytes(registry))

    w("workflow_request_copy.json", request)
    w("atlas_validation_report.json", {
        "atlas_validation_version": "0.1.0",
        "atlas_registry_version": "0.1.0",
        "atlas_registry_status": "REGISTRY_VERIFIED",
        "atlas_validation_status": atlas_validation_status,
        "workflow_type_checked": versions.WORKFLOW_TYPE,
        "action_type_checked": versions.ACTION_TYPE,
        "required_components_present": True,
        "required_statuses_present": True,
        "required_predicates_present": True,
        "truth_claims_absent": True,
        "forbidden_future_actions_absent": True,
        "known_limitations": [
            "Coordinator Workflow v0.3 uses Atlas Registry v0.1 as a read-only vocabulary boundary.",
            "Atlas validation does not prove evidence contents are true.",
            "Atlas validation does not prove ODIN claims are true.",
            "Atlas validation does not verify external reality.",
            "Atlas validation does not sign or externally anchor outputs.",
        ],
    })
    w("workflow_report.json", {
        "coordinator_workflow_version": "0.3.0",
        "workflow_status": workflow_status,
        "requested_case_id": request["requested_case_id"],
        "case_id": case_id,
        "evidence_id": evidence_id,
        "workflow_type": request["workflow_type"],
        "atlas_validation_status": atlas_validation_status,
        "atlas_registry_status": "REGISTRY_VERIFIED",
        "sentinel_status": "PASS_STRICT",
        "aletheia_status": "VERIFIED_PRESENT",
        "bridge_status": "CONVERTED",
        "odin_reasoning_status": odin_status,
        "histor_sentinel_status": "IMPORTED_VERIFIED_SENTINEL",
        "histor_aletheia_status": "IMPORTED_VERIFIED_ALETHEIA",
        "histor_odin_status": "IMPORTED_VERIFIED_ODIN",
        "case_bundle_status": case_bundle_status,
        "final_bundle_path": "case_bundle_v02",
        "known_limitations": _coord_known_limitations(),
    })
    steps = [{"step_id": sid, "operation": op, "status": "COMPLETED"}
             for sid, op in _COORD_STEP_PLAN]
    w("workflow_steps.json", {"coordinator_workflow_steps_version": "0.3.0",
                              "steps": steps})
    w("sentinel_run/run_report.json", {
        "sentinel_status": "PASS_STRICT", "action_type": "CREATE_DIRECTORY",
        "case_id": case_id, "evidence_id": evidence_id,
        "case_directory_name": request["case_directory_name"]})
    w("histor_sentinel_case/case_summary.json", {
        "histor_sentinel_status": "IMPORTED_VERIFIED_SENTINEL", "case_id": case_id})
    w("aletheia_bundle/evidence_manifest.json", {
        "aletheia_status": "VERIFIED_PRESENT", "case_id": case_id,
        "evidence_id": evidence_id, "predicate": "evidence.present"})
    w("histor_aletheia_case/evidence_case_summary.json", {
        "histor_aletheia_status": "IMPORTED_VERIFIED_ALETHEIA",
        "case_id": case_id, "evidence_id": evidence_id})
    w("bridge_output/odin_claims.json", {
        "bridge_status": "CONVERTED", "case_id": case_id,
        "evidence_id": evidence_id, "predicates": list(_PREDICATES)})
    w("odin_output/reasoning_report.json", {
        "odin_reasoning_status": odin_status, "case_id": case_id,
        "predicates": list(_PREDICATES)})
    w("histor_odin_case/odin_case_summary.json", {
        "histor_odin_status": "IMPORTED_VERIFIED_ODIN", "case_id": case_id})
    w("case_bundle_v02/case_manifest.json", {
        "case_bundle_status": case_bundle_status, "case_id": case_id,
        "evidence_id": evidence_id})

    from .checksums import sha256_file
    present = [p for p in _COORD_PATHS
               if os.path.isfile(os.path.join(coord_dir, p))]
    lines = ["%s  %s" % (sha256_file(os.path.join(coord_dir, p)), p)
             for p in present]
    canonical.atomic_write_bytes(
        os.path.join(coord_dir, "workflow_checksums.txt"),
        ("\n".join(lines) + "\n").encode("utf-8"))
    return coord_dir


COORD_PATHS = _COORD_PATHS
