"""Read-only Atlas vocabulary checks against the copied Atlas registry.

ATLAS_VALIDATED is the Coordinator v0.3 validation result, NOT an Atlas Registry
v0.1 term; it is confirmed as a fixed value elsewhere, never looked up here.
"""

from . import versions
from .errors import CheckError, FAILED_ATLAS_INVALID, FAILED_TRUTH_CLAIM


def _names(registry, field, key):
    return {it[key] for it in registry.get(field, [])
            if isinstance(it, dict) and key in it}


def check_workflow_and_action(registry):
    if versions.WORKFLOW_TYPE not in _names(registry, "workflow_types", "workflow_type"):
        raise CheckError(FAILED_ATLAS_INVALID, "workflow type not in Atlas registry")
    if versions.ACTION_TYPE not in _names(registry, "action_types", "action_type"):
        raise CheckError(FAILED_ATLAS_INVALID, "action type not in Atlas registry")


def check_statuses_present(registry, observed_statuses):
    present = _names(registry, "statuses", "status")
    for status in observed_statuses:
        if status not in present:
            raise CheckError(FAILED_ATLAS_INVALID,
                             "status not in Atlas registry: %r" % status)


def check_predicates_present(registry):
    present = _names(registry, "claim_predicates", "predicate")
    for pred in versions.REQUIRED_PREDICATES:
        if pred not in present:
            raise CheckError(FAILED_ATLAS_INVALID,
                             "predicate not in Atlas registry: %r" % pred)


def check_no_truth_claims(registry):
    for s in registry.get("statuses", []):
        if isinstance(s, dict) and s.get("truth_claim") is True:
            raise CheckError(FAILED_TRUTH_CLAIM, "Atlas registry truth-claim status")
    for p in registry.get("claim_predicates", []):
        if isinstance(p, dict) and p.get("truth_claim") is True:
            raise CheckError(FAILED_TRUTH_CLAIM, "Atlas registry truth-claim predicate")


def check_no_forbidden_actions(registry):
    actions = _names(registry, "action_types", "action_type")
    for forbidden in versions.FORBIDDEN_ACTION_TYPES:
        if forbidden in actions:
            raise CheckError(FAILED_ATLAS_INVALID,
                             "forbidden action type in Atlas registry: %r" % forbidden)
