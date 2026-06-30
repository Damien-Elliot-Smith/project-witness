"""Read-only Atlas vocabulary checks against the copied Atlas registry.

ATLAS_VALIDATED is the Coordinator v0.3 validation result, NOT an Atlas Registry
v0.1 term; it is confirmed as a fixed value elsewhere and is never looked up in
the Atlas status vocabulary here.
"""

from . import versions
from .errors import (BuildError, FAILED_ATLAS_INVALID, FAILED_TRUTH_CLAIM)


def _names(registry, field, key):
    return {it[key] for it in registry.get(field, [])
            if isinstance(it, dict) and key in it}


def atlas_statuses(registry):
    return _names(registry, "statuses", "status")


def atlas_workflow_types(registry):
    return _names(registry, "workflow_types", "workflow_type")


def atlas_action_types(registry):
    return _names(registry, "action_types", "action_type")


def atlas_predicates(registry):
    return _names(registry, "claim_predicates", "predicate")


def check_statuses_present(registry, observed_statuses):
    present = atlas_statuses(registry)
    for status in observed_statuses:
        if status not in present:
            raise BuildError(FAILED_ATLAS_INVALID,
                             "status not in Atlas registry: %r" % status)


def check_predicates_present(registry):
    present = atlas_predicates(registry)
    for pred in versions.REQUIRED_PREDICATES:
        if pred not in present:
            raise BuildError(FAILED_ATLAS_INVALID,
                             "predicate not in Atlas registry: %r" % pred)


def check_no_truth_claims(registry):
    for s in registry.get("statuses", []):
        if isinstance(s, dict) and s.get("truth_claim") is True:
            raise BuildError(FAILED_TRUTH_CLAIM,
                             "Atlas registry has a truth-claim status")
    for p in registry.get("claim_predicates", []):
        if isinstance(p, dict) and p.get("truth_claim") is True:
            raise BuildError(FAILED_TRUTH_CLAIM,
                             "Atlas registry has a truth-claim predicate")


def check_no_forbidden_actions(registry):
    actions = atlas_action_types(registry)
    for forbidden in versions.FORBIDDEN_ACTION_TYPES:
        if forbidden in actions:
            raise BuildError(FAILED_ATLAS_INVALID,
                             "forbidden action type in Atlas registry: %r" % forbidden)


def check_workflow_and_action(registry):
    if versions.WORKFLOW_TYPE not in atlas_workflow_types(registry):
        raise BuildError(FAILED_ATLAS_INVALID, "workflow type not in Atlas registry")
    if versions.ACTION_TYPE not in atlas_action_types(registry):
        raise BuildError(FAILED_ATLAS_INVALID, "action type not in Atlas registry")
