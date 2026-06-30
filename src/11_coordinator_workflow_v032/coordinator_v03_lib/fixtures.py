"""Deterministic fixtures: a fake Atlas registry and a fake workflow request.

Used by selfcheck and the unit tests so the default suite needs no real frozen
components and spawns no subprocesses.
"""

import os

from . import canonical, versions

_COMPONENTS = (
    ("sentinel_core", "frozen_module"),
    ("histor_lite", "frozen_module"),
    ("aletheia_evidence_bundle", "frozen_module"),
    ("aletheia_odin_bridge", "frozen_module"),
    ("odin_claim_reasoner", "frozen_module"),
    ("histor_lite_aletheia_importer", "frozen_module"),
    ("histor_lite_odin_importer", "frozen_module"),
    ("case_bundle_v02", "frozen_module"),
    ("coordinator_workflow_v02", "frozen_module"),
    ("atlas_registry", "frozen_module"),
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
    ("REGISTRY_VERIFIED", "verification_statuses"),
    ("COMPLETED", "step_statuses"),
    ("FAILED", "step_statuses"),
    ("SKIPPED_AFTER_FAILURE", "step_statuses"),
)

_PREDICATES = ("evidence.present", "evidence.integrity_verified")


def build_registry(omit_workflow_type=False, omit_action_type=False,
                   omit_component=None, omit_status=None, omit_predicate=None,
                   truth_claim_status=False, truth_claim_predicate=False,
                   forbidden_action=None):
    workflow_types = []
    if not omit_workflow_type:
        workflow_types.append({"workflow_type": versions.WORKFLOW_TYPE,
                               "introduced_by_component": "coordinator_workflow_v02"})
    action_types = []
    if not omit_action_type:
        action_types.append({"action_type": versions.ACTION_TYPE,
                             "introduced_by_component": "sentinel_core"})
    if forbidden_action:
        action_types.append({"action_type": forbidden_action,
                             "introduced_by_component": "sentinel_core"})

    components = []
    for cid, ctype in _COMPONENTS:
        if cid == omit_component:
            continue
        components.append({"component_id": cid, "component_type": ctype,
                          "component_version": "0.1.0", "frozen_status": "frozen"})

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
        "atlas_registry_version": versions.ATLAS_REGISTRY_VERSION,
        "registry_id": "project_witness_local_v1_registry",
        "components": components,
        "workflow_types": workflow_types,
        "action_types": action_types,
        "statuses": statuses,
        "claim_predicates": predicates,
        "case_record_types": [],
        "known_limitations": ["Atlas Registry v0.1 is a read-only registry."],
    }


def make_fake_atlas_root(base_dir, missing_registry=False, break_verify=False,
                         **registry_opts):
    os.makedirs(os.path.join(base_dir, "registry"), exist_ok=True)
    if missing_registry:
        return base_dir
    registry = build_registry(**registry_opts)
    path = os.path.join(base_dir, "registry", "atlas_registry.json")
    data = canonical.atlas_canonical_bytes(registry)
    if break_verify:
        data = data.rstrip(b"\n")  # drop trailing newline -> not Atlas-canonical
    canonical.atomic_write_bytes(path, data)
    return base_dir


def build_request(work_root, atlas_root, evidence_file,
                  requested_case_id="case_001", evidence_id="evidence_001"):
    roots = {
        "atlas_registry_root": atlas_root,
        "sentinel_root": os.path.join(work_root, "sentinel"),
        "histor_lite_root": os.path.join(work_root, "histor"),
        "aletheia_root": os.path.join(work_root, "aletheia"),
        "bridge_root": os.path.join(work_root, "bridge"),
        "odin_root": os.path.join(work_root, "odin"),
        "histor_aletheia_root": os.path.join(work_root, "histor_aletheia"),
        "histor_odin_root": os.path.join(work_root, "histor_odin"),
        "case_bundle_v02_root": os.path.join(work_root, "case_bundle_v02"),
    }
    return {
        "coordinator_workflow_request_version":
            versions.COORDINATOR_WORKFLOW_REQUEST_VERSION,
        "workflow_type": versions.WORKFLOW_TYPE,
        "requested_case_id": requested_case_id,
        "evidence_id": evidence_id,
        "allowed_root": os.path.join(work_root, "cases"),
        "case_directory_name": requested_case_id,
        "evidence_file": evidence_file,
        "component_roots": roots,
    }
