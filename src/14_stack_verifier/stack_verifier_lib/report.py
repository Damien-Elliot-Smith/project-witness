"""Stack Verifier v0.1 report construction and the check orchestration."""

import re

from . import (versions, source_reader, source_verifier, manifest_reader,
               atlas_checks, artifact_checks)
from .errors import (CheckError, STACK_VERIFIED, SOURCE_VERIFIED,
                     MANIFEST_VERIFIED, MANIFEST_NOT_PROVIDED, NOT_APPLICABLE,
                     FAILED_CASE_ID_MISMATCH, FAILED_EVIDENCE_ID_MISMATCH,
                     FAILED_STATUS_INVALID, FAILED_TRUTH_CLAIM,
                     SENTINEL_OK, ALETHEIA_OK, BRIDGE_OK, ODIN_OK, CASE_BUNDLE_OK)

KNOWN_LIMITATIONS = (
    "Stack Verifier v0.1 verifies structure, checksums, IDs, statuses, Atlas vocabulary boundaries, and manifest consistency.",
    "It does not run workflows.",
    "It does not copy evidence contents.",
    "It does not prove evidence contents are true.",
    "It does not prove ODIN claims are true.",
    "It does not verify external reality.",
    "It does not sign or externally anchor outputs.",
)

_TRUTH_PATTERNS = (
    re.compile(r"\b(?:is|are|was|were)\s+true\b"),
    re.compile(r"\b(?:is|are|was|were)\s+authentic\b"),
    re.compile(r"\b(?:is|are|was|were)\s+trusted\b"),
    re.compile(r"\bproves?\s+reality\b"),
    re.compile(r"\bproves?\s+truth\b"),
    re.compile(r"\bevidence\s+is\s+true\b"),
    re.compile(r"\bclaims?\s+are\s+true\b"),
)
_NEGATION = ("does not", "do not", "not ", "no ", "never", "without", "n't")
_SENT = re.compile(r"[.\n;:!?]+")


def _collect(obj, out):
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            out.append(k)
            _collect(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _collect(v, out)


def _scan_truth(*objs):
    strings = []
    for obj in objs:
        _collect(obj, strings)
    for text in strings:
        for sentence in (s.strip() for s in _SENT.split(text) if s.strip()):
            low = sentence.lower()
            if any(m in low for m in _NEGATION):
                continue
            for pat in _TRUTH_PATTERNS:
                if pat.search(low):
                    raise CheckError(FAILED_TRUTH_CLAIM,
                                     "truth-like claim: %r" % sentence)


def _require_status(value, allowed, label):
    if value not in allowed:
        raise CheckError(FAILED_STATUS_INVALID, "%s status invalid: %r" % (label, value))


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
    if not case_id or any(c != case_id for c in case_ids):
        raise CheckError(FAILED_CASE_ID_MISMATCH, "case_id mismatch")
    if not evidence_id or any(e != evidence_id for e in evidence_ids):
        raise CheckError(FAILED_EVIDENCE_ID_MISMATCH, "evidence_id mismatch")
    return case_id, evidence_id


def build_stack_report(source_type, source_run, manifest_run=None):
    """Run the stack check. Returns (report, checked_artifacts).
    Raises CheckError on any failure."""
    # step_002 / step_003: locate, structure, checksums
    coord_dir, coord_prefix = source_reader.locate_coordinator_dir(
        source_type, source_run)
    source_reader.check_required_source_files(source_type, source_run, coord_dir)
    source_verifier.verify_structure(source_type, source_run, coord_dir)
    source_verifier.verify_checksums(source_type, source_run, coord_dir)

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

    fields = {
        "workflow_type": creport.get("workflow_type"),
        "action_type": versions.ACTION_TYPE,
        "companion_status": companion_status,
        "coordinator_workflow_status": creport.get("workflow_status"),
        "atlas_validation_status": creport.get("atlas_validation_status"),
        "atlas_registry_status": creport.get("atlas_registry_status"),
        "sentinel_status": creport.get("sentinel_status"),
        "aletheia_status": creport.get("aletheia_status"),
        "bridge_status": creport.get("bridge_status"),
        "odin_reasoning_status": creport.get("odin_reasoning_status"),
        "case_bundle_status": creport.get("case_bundle_status"),
        "case_id": case_id, "evidence_id": evidence_id,
    }

    _require_status(fields["coordinator_workflow_status"], ("WORKFLOW_COMPLETED",), "workflow")
    _require_status(fields["atlas_validation_status"], ("ATLAS_VALIDATED",), "atlas_validation")
    _require_status(fields["atlas_registry_status"], ("REGISTRY_VERIFIED",), "atlas_registry")
    _require_status(fields["sentinel_status"], SENTINEL_OK, "sentinel")
    _require_status(fields["aletheia_status"], ALETHEIA_OK, "aletheia")
    _require_status(fields["bridge_status"], BRIDGE_OK, "bridge")
    _require_status(fields["odin_reasoning_status"], ODIN_OK, "odin")
    _require_status(fields["case_bundle_status"], CASE_BUNDLE_OK, "case_bundle")
    if fields["workflow_type"] != versions.WORKFLOW_TYPE:
        raise CheckError(FAILED_STATUS_INVALID, "workflow type invalid")

    # step_004: Atlas vocabulary (ATLAS_VALIDATED excluded -- not an Atlas term)
    atlas_checks.check_workflow_and_action(registry)
    observed = [fields["coordinator_workflow_status"], fields["atlas_registry_status"],
                fields["sentinel_status"], fields["aletheia_status"],
                fields["bridge_status"], fields["odin_reasoning_status"],
                fields["case_bundle_status"]]
    if companion_status != NOT_APPLICABLE:
        observed.append(companion_status)
    atlas_checks.check_statuses_present(registry, observed)
    atlas_checks.check_predicates_present(registry)
    atlas_checks.check_no_truth_claims(registry)
    atlas_checks.check_no_forbidden_actions(registry)

    # step_020: record checked artifacts
    checked = artifact_checks.build_checked_artifacts(
        source_type, source_run, coord_dir, coord_prefix, manifest_run)
    source_artifacts = [a for a in checked
                        if a["source_label"] == versions.LABEL_SOURCE]

    # step_005 / step_006: manifest cross-check
    if manifest_run is not None:
        manifest_reader.structural_verify(manifest_run)
        manifest, _index = manifest_reader.load(manifest_run)
        manifest_reader.cross_check(manifest, fields, source_artifacts)
        manifest_status = MANIFEST_VERIFIED
        manifest_consistent = True
    else:
        manifest_status = MANIFEST_NOT_PROVIDED
        manifest_consistent = True

    # step_007: truth boundary
    _scan_truth(reports["coordinator_workflow_report"], reports["bridge_claims"],
                reports["odin_reasoning_report"], reports["case_bundle_manifest"])

    report = {
        "stack_verifier_version": versions.STACK_VERIFIER_VERSION,
        "source_type": source_type,
        "stack_verification_status": STACK_VERIFIED,
        "source_status": SOURCE_VERIFIED,
        "manifest_status": manifest_status,
        "case_id": case_id,
        "requested_case_id": requested_case_id,
        "evidence_id": evidence_id,
        "workflow_type": fields["workflow_type"],
        "action_type": fields["action_type"],
        "companion_status": companion_status,
        "coordinator_workflow_status": fields["coordinator_workflow_status"],
        "atlas_validation_status": fields["atlas_validation_status"],
        "atlas_registry_status": fields["atlas_registry_status"],
        "sentinel_status": fields["sentinel_status"],
        "aletheia_status": fields["aletheia_status"],
        "bridge_status": fields["bridge_status"],
        "odin_reasoning_status": fields["odin_reasoning_status"],
        "case_bundle_status": fields["case_bundle_status"],
        "case_id_consistent": True,
        "evidence_id_consistent": True,
        "checksums_valid": True,
        "atlas_vocabulary_valid": True,
        "manifest_consistent": manifest_consistent,
        "truth_boundary_valid": True,
        "source_artifact_count": len(checked),
        "checked_artifacts": checked,
        "known_limitations": list(KNOWN_LIMITATIONS),
    }
    return report, checked
