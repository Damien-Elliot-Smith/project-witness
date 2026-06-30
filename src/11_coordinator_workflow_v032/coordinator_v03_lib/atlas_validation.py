"""Read-only Atlas Registry v0.1 vocabulary validation for Coordinator v0.3.

Atlas is read-only. This module never writes to the Atlas folder, never adds
terms, and never uses Atlas to prove truth. It only confirms that the workflow's
vocabulary (workflow type, action type, components, statuses, predicates) exists
in Atlas and that Atlas itself is truth-free and free of forbidden future actions.
"""

import os

from . import canonical, versions
from .errors import (
    ATLAS_VALIDATED, FAILED_ATLAS_ROOT_MISSING, FAILED_ATLAS_REGISTRY_MISSING,
    FAILED_ATLAS_VERIFY, FAILED_ATLAS_WORKFLOW_TYPE_MISSING,
    FAILED_ATLAS_ACTION_TYPE_MISSING, FAILED_ATLAS_COMPONENT_MISSING,
    FAILED_ATLAS_STATUS_MISSING, FAILED_ATLAS_PREDICATE_MISSING,
    FAILED_ATLAS_TRUTH_CLAIM, FAILED_ATLAS_FORBIDDEN_ACTION,
    REGISTRY_VERIFIED, REGISTRY_NOT_VERIFIED,
)

_REGISTRY_REL = os.path.join("registry", "atlas_registry.json")
_REQUIRED_TOP_LEVEL = (
    "action_types", "atlas_registry_version", "claim_predicates",
    "components", "statuses", "workflow_types",
)

# Statuses this one-case workflow can legitimately observe and therefore expects
# Atlas to record. Step statuses and the coordinator status are included.
_REQUIRED_STATUSES = (
    "PASS_STRICT", "VERIFIED_PRESENT", "CONVERTED",
    "CONSISTENT", "CONTRADICTION_DETECTED",
    "IMPORTED_VERIFIED_SENTINEL", "IMPORTED_VERIFIED_ALETHEIA",
    "IMPORTED_VERIFIED_ODIN", "BUNDLED_VERIFIED_CASE",
    "WORKFLOW_COMPLETED", "REGISTRY_VERIFIED",
    "COMPLETED", "FAILED", "SKIPPED_AFTER_FAILURE",
)

_TRUTH_LIKE_STATUS = ("PROVEN_TRUE", "AUTHENTIC", "SOURCE_TRUSTED",
                      "VERIFIED_TRUE", "REALITY_PROVEN")
_TRUTH_LIKE_PREDICATE = ("contents.true", "file.authentic", "reality.proven",
                         "source.trusted", "claim.true")


class AtlasValidationResult:
    def __init__(self, status, report, registry_obj=None, registry_bytes=None):
        self.status = status
        self.report = report
        self.registry_obj = registry_obj
        self.registry_bytes = registry_bytes
        self.ok = (status == ATLAS_VALIDATED)


def _names(items, key):
    out = []
    for it in items if isinstance(items, list) else []:
        if isinstance(it, dict) and key in it:
            out.append(it[key])
    return out


def inprocess_verify(registry_bytes, registry_obj):
    """Strict in-process structural verifier matching Atlas v0.1 shape.

    Returns True if structurally valid (canonical Atlas form + required fields +
    list shapes). It does NOT judge truth claims or forbidden actions here; those
    are reported with their own distinct statuses by the validator.
    """
    if not canonical.is_atlas_canonical_bytes(registry_bytes):
        return False
    if not isinstance(registry_obj, dict):
        return False
    for field in _REQUIRED_TOP_LEVEL:
        if field not in registry_obj:
            return False
    for field in ("action_types", "claim_predicates", "components",
                  "statuses", "workflow_types"):
        if not isinstance(registry_obj[field], list):
            return False
    return True


def _build_report(status, **flags):
    report = {
        "atlas_validation_version": versions.ATLAS_VALIDATION_VERSION,
        "atlas_registry_version": versions.ATLAS_REGISTRY_VERSION,
        "atlas_registry_status": (REGISTRY_VERIFIED if flags.get("verified")
                                  else REGISTRY_NOT_VERIFIED),
        "atlas_validation_status": status,
        "workflow_type_checked": versions.WORKFLOW_TYPE,
        "action_type_checked": versions.ACTION_TYPE,
        "required_components_present": bool(flags.get("components")),
        "required_statuses_present": bool(flags.get("statuses")),
        "required_predicates_present": bool(flags.get("predicates")),
        "truth_claims_absent": bool(flags.get("truth_absent")),
        "forbidden_future_actions_absent": bool(flags.get("forbidden_absent")),
        "known_limitations": [
            "Coordinator Workflow v0.3 uses Atlas Registry v0.1 as a read-only vocabulary boundary.",
            "Atlas validation does not prove evidence contents are true.",
            "Atlas validation does not prove ODIN claims are true.",
            "Atlas validation does not verify external reality.",
            "Atlas validation does not sign or externally anchor outputs.",
        ],
    }
    return report


def validate(atlas_root, verify_fn=inprocess_verify):
    """Validate the Atlas registry as a read-only vocabulary boundary."""
    if not atlas_root or not os.path.isdir(atlas_root):
        return AtlasValidationResult(FAILED_ATLAS_ROOT_MISSING,
                                     _build_report(FAILED_ATLAS_ROOT_MISSING))
    reg_path = os.path.join(atlas_root, _REGISTRY_REL)
    if not os.path.isfile(reg_path):
        return AtlasValidationResult(FAILED_ATLAS_REGISTRY_MISSING,
                                     _build_report(FAILED_ATLAS_REGISTRY_MISSING))

    registry_bytes = canonical.read_bytes(reg_path)
    try:
        import json
        registry_obj = json.loads(registry_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return AtlasValidationResult(FAILED_ATLAS_VERIFY,
                                     _build_report(FAILED_ATLAS_VERIFY))

    if not verify_fn(registry_bytes, registry_obj):
        return AtlasValidationResult(FAILED_ATLAS_VERIFY,
                                     _build_report(FAILED_ATLAS_VERIFY),
                                     registry_obj, registry_bytes)

    workflow_types = _names(registry_obj.get("workflow_types"), "workflow_type")
    action_types = _names(registry_obj.get("action_types"), "action_type")
    components = _names(registry_obj.get("components"), "component_id")
    statuses = _names(registry_obj.get("statuses"), "status")
    predicates = _names(registry_obj.get("claim_predicates"), "predicate")

    flags = {"verified": True}

    if versions.WORKFLOW_TYPE not in workflow_types:
        return AtlasValidationResult(
            FAILED_ATLAS_WORKFLOW_TYPE_MISSING,
            _build_report(FAILED_ATLAS_WORKFLOW_TYPE_MISSING, **flags),
            registry_obj, registry_bytes)

    if versions.ACTION_TYPE not in action_types:
        return AtlasValidationResult(
            FAILED_ATLAS_ACTION_TYPE_MISSING,
            _build_report(FAILED_ATLAS_ACTION_TYPE_MISSING, **flags),
            registry_obj, registry_bytes)

    missing_components = [c for c in versions.REQUIRED_COMPONENTS
                         if c not in components]
    if missing_components:
        return AtlasValidationResult(
            FAILED_ATLAS_COMPONENT_MISSING,
            _build_report(FAILED_ATLAS_COMPONENT_MISSING, **flags),
            registry_obj, registry_bytes)
    flags["components"] = True

    missing_statuses = [s for s in _REQUIRED_STATUSES if s not in statuses]
    if missing_statuses:
        return AtlasValidationResult(
            FAILED_ATLAS_STATUS_MISSING,
            _build_report(FAILED_ATLAS_STATUS_MISSING, **flags),
            registry_obj, registry_bytes)
    flags["statuses"] = True

    missing_predicates = [p for p in versions.REQUIRED_PREDICATES
                         if p not in predicates]
    if missing_predicates:
        return AtlasValidationResult(
            FAILED_ATLAS_PREDICATE_MISSING,
            _build_report(FAILED_ATLAS_PREDICATE_MISSING, **flags),
            registry_obj, registry_bytes)
    flags["predicates"] = True

    if _has_truth_claim(registry_obj):
        return AtlasValidationResult(
            FAILED_ATLAS_TRUTH_CLAIM,
            _build_report(FAILED_ATLAS_TRUTH_CLAIM, **flags),
            registry_obj, registry_bytes)
    flags["truth_absent"] = True

    if _has_forbidden_action(action_types):
        return AtlasValidationResult(
            FAILED_ATLAS_FORBIDDEN_ACTION,
            _build_report(FAILED_ATLAS_FORBIDDEN_ACTION, **flags),
            registry_obj, registry_bytes)
    flags["forbidden_absent"] = True

    return AtlasValidationResult(
        ATLAS_VALIDATED, _build_report(ATLAS_VALIDATED, **flags),
        registry_obj, registry_bytes)


def _has_truth_claim(registry_obj):
    for status in registry_obj.get("statuses", []):
        if isinstance(status, dict):
            if status.get("truth_claim") is True:
                return True
            if status.get("status") in _TRUTH_LIKE_STATUS:
                return True
    for pred in registry_obj.get("claim_predicates", []):
        if isinstance(pred, dict):
            if pred.get("truth_claim") is True:
                return True
            if pred.get("predicate") in _TRUTH_LIKE_PREDICATE:
                return True
    return False


def _has_forbidden_action(action_types):
    return any(a in versions.FORBIDDEN_ACTION_TYPES for a in action_types)
