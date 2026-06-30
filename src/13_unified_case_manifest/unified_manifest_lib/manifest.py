"""Assemble the unified case manifest from an existing source case output."""

from . import versions, source_reader, atlas_checks, artifact_index
from .errors import (BuildError, SOURCE_VERIFIED, NOT_APPLICABLE,
                     FAILED_CASE_ID_MISMATCH, FAILED_EVIDENCE_ID_MISMATCH,
                     FAILED_STATUS_INVALID, SENTINEL_OK, ALETHEIA_OK, BRIDGE_OK,
                     ODIN_OK, CASE_BUNDLE_OK)

KNOWN_LIMITATIONS = (
    "Unified Case Manifest v0.1 summarizes one existing Project Witness case output.",
    "It does not run workflows.",
    "It does not copy evidence contents.",
    "It does not prove evidence contents are true.",
    "It does not prove ODIN claims are true.",
    "It does not verify external reality.",
    "It does not sign or externally anchor outputs.",
)

_UNKNOWN_COMPONENTS = (
    ("sentinel_core_v022", "source_component"),
    ("histor_lite_v012", "source_component"),
    ("aletheia_evidence_bundle_v01", "source_component"),
    ("aletheia_odin_bridge_v01", "source_component"),
    ("odin_claim_reasoner_v01", "source_component"),
    ("histor_lite_aletheia_importer_v01", "source_component"),
    ("histor_lite_odin_importer_v01", "source_component"),
    ("case_bundle_v02", "source_component"),
)


def _require_status(value, allowed, label):
    if value not in allowed:
        raise BuildError(FAILED_STATUS_INVALID,
                         "%s status invalid: %r" % (label, value))


def _check_ids(reports, source_type):
    creport = reports["coordinator_workflow_report"]
    manifest = reports["case_bundle_manifest"]
    case_id = creport.get("case_id")
    evidence_id = creport.get("evidence_id")
    case_ids = [case_id, manifest.get("case_id")]
    evidence_ids = [evidence_id, manifest.get("evidence_id")]
    if source_type == versions.SOURCE_TYPE_COMPANION:
        case_ids.append(reports["companion_report"].get("case_id"))
        evidence_ids.append(reports["companion_report"].get("evidence_id"))
        evidence_ids.append(reports["workflow_request"].get("evidence_id"))
    if any(c != case_id for c in case_ids) or not case_id:
        raise BuildError(FAILED_CASE_ID_MISMATCH, "case_id mismatch across records")
    if any(e != evidence_id for e in evidence_ids) or not evidence_id:
        raise BuildError(FAILED_EVIDENCE_ID_MISMATCH,
                         "evidence_id mismatch across records")
    return case_id, evidence_id


def _component_versions(reports, source_type):
    creport = reports["coordinator_workflow_report"]
    registry = reports["atlas_registry_copy"]
    out = []
    if source_type == versions.SOURCE_TYPE_COMPANION:
        out.append({"component_id": "companion_cli_v03",
                    "component_version": reports["companion_report"].get(
                        "companion_cli_version", versions.UNKNOWN_FROM_SOURCE),
                    "role": "source_companion"})
    out.append({"component_id": "coordinator_workflow_v03",
                "component_version": creport.get(
                    "coordinator_workflow_version", versions.UNKNOWN_FROM_SOURCE),
                "role": "source_workflow"})
    out.append({"component_id": "atlas_registry_v01",
                "component_version": registry.get(
                    "atlas_registry_version", versions.UNKNOWN_FROM_SOURCE),
                "role": "source_registry"})
    for component_id, role in _UNKNOWN_COMPONENTS:
        out.append({"component_id": component_id,
                    "component_version": versions.UNKNOWN_FROM_SOURCE,
                    "role": role})
    out.append({"component_id": "unified_case_manifest_v01",
                "component_version": versions.UNIFIED_CASE_MANIFEST_VERSION,
                "role": "manifest_tool"})
    return out


def build_manifest_data(source_type, source_run):
    """Read the source and return (manifest_dict, source_index_dict).
    Raises BuildError on any failure."""
    coord_dir, coord_prefix = source_reader.locate_coordinator_dir(
        source_type, source_run)
    source_reader.check_required_source_files(source_type, source_run, coord_dir)
    if source_type == versions.SOURCE_TYPE_COMPANION:
        source_reader.structural_verify_companion(source_run)
    source_reader.structural_verify_coordinator(coord_dir)

    reports = source_reader.load_reports(source_type, source_run, coord_dir)
    creport = reports["coordinator_workflow_report"]
    registry = reports["atlas_registry_copy"]

    case_id, evidence_id = _check_ids(reports, source_type)

    if source_type == versions.SOURCE_TYPE_COMPANION:
        companion_status = reports["companion_report"].get("companion_status")
        _require_status(companion_status, ("COMPANION_COMPLETED",), "companion")
        requested_case_id = reports["companion_report"].get(
            "requested_case_id", creport.get("requested_case_id"))
    else:
        companion_status = NOT_APPLICABLE
        requested_case_id = creport.get("requested_case_id")

    workflow_status = creport.get("workflow_status")
    atlas_validation_status = creport.get("atlas_validation_status")
    atlas_registry_status = creport.get("atlas_registry_status")
    sentinel_status = creport.get("sentinel_status")
    aletheia_status = creport.get("aletheia_status")
    bridge_status = creport.get("bridge_status")
    odin_status = creport.get("odin_reasoning_status")
    case_bundle_status = creport.get("case_bundle_status")
    workflow_type = creport.get("workflow_type")
    action_type = versions.ACTION_TYPE

    _require_status(workflow_status, ("WORKFLOW_COMPLETED",), "workflow")
    _require_status(atlas_validation_status, ("ATLAS_VALIDATED",), "atlas_validation")
    _require_status(atlas_registry_status, ("REGISTRY_VERIFIED",), "atlas_registry")
    _require_status(sentinel_status, SENTINEL_OK, "sentinel")
    _require_status(aletheia_status, ALETHEIA_OK, "aletheia")
    _require_status(bridge_status, BRIDGE_OK, "bridge")
    _require_status(odin_status, ODIN_OK, "odin")
    _require_status(case_bundle_status, CASE_BUNDLE_OK, "case_bundle")

    if workflow_type != versions.WORKFLOW_TYPE:
        raise BuildError(FAILED_STATUS_INVALID, "workflow type invalid")

    atlas_checks.check_workflow_and_action(registry)
    # ATLAS_VALIDATED is the Coordinator validation result, not an Atlas term, so
    # it is NOT included in the Atlas-membership check below.
    observed = [workflow_status, atlas_registry_status, sentinel_status,
                aletheia_status, bridge_status, odin_status, case_bundle_status]
    if companion_status != NOT_APPLICABLE:
        observed.append(companion_status)
    atlas_checks.check_statuses_present(registry, observed)
    atlas_checks.check_predicates_present(registry)
    atlas_checks.check_no_truth_claims(registry)
    atlas_checks.check_no_forbidden_actions(registry)

    artifacts = artifact_index.build_source_artifacts(
        source_type, source_run, coord_dir, coord_prefix)
    source_index = artifact_index.build_source_index(
        source_type, source_run, artifacts)

    manifest = {
        "unified_case_manifest_version": versions.UNIFIED_CASE_MANIFEST_VERSION,
        "source_type": source_type,
        "case_id": case_id,
        "requested_case_id": requested_case_id,
        "evidence_id": evidence_id,
        "workflow_type": workflow_type,
        "action_type": action_type,
        "source_status": SOURCE_VERIFIED,
        "companion_status": companion_status,
        "coordinator_workflow_status": workflow_status,
        "atlas_validation_status": atlas_validation_status,
        "atlas_registry_status": atlas_registry_status,
        "sentinel_status": sentinel_status,
        "aletheia_status": aletheia_status,
        "bridge_status": bridge_status,
        "odin_reasoning_status": odin_status,
        "case_bundle_status": case_bundle_status,
        "source_artifacts": artifacts,
        "component_versions": _component_versions(reports, source_type),
        "known_limitations": list(KNOWN_LIMITATIONS),
    }
    return manifest, source_index
