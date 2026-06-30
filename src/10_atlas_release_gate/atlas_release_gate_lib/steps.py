"""Ordered release-gate step records (canonical JSON) with short-circuit logic."""

from . import versions
from .errors import STEP_COMPLETED, STEP_FAILED, STEP_SKIPPED

STEP_PLAN = (
    ("step_001", "CHECK_REQUIRED_FILES"),
    ("step_002", "VERIFY_ATLAS_REGISTRY"),
    ("step_003", "EXPORT_ATLAS_REGISTRY"),
    ("step_004", "VERIFY_ATLAS_EXPORT"),
    ("step_005", "CHECK_DOCUMENTATION"),
    ("step_006", "CHECK_HONESTY_BOUNDARY"),
    ("step_007", "CHECK_FORBIDDEN_FEATURES"),
    ("step_008", "WRITE_RELEASE_GATE_REPORT"),
    ("step_009", "VERIFY_RELEASE_GATE_OUTPUT"),
)


def build_steps(statuses):
    if len(statuses) != len(STEP_PLAN):
        raise ValueError("statuses length mismatch")
    steps = []
    for (sid, op), status in zip(STEP_PLAN, statuses):
        steps.append({"step_id": sid, "operation": op, "status": status})
    return {
        "atlas_release_gate_steps_version": versions.ATLAS_RELEASE_GATE_STEPS_VERSION,
        "steps": steps,
    }


def statuses_with_failure_at(index):
    """COMPLETED before index, FAILED at index, SKIPPED_AFTER_FAILURE after."""
    out = []
    for i in range(len(STEP_PLAN)):
        if i < index:
            out.append(STEP_COMPLETED)
        elif i == index:
            out.append(STEP_FAILED)
        else:
            out.append(STEP_SKIPPED)
    return out


def all_completed():
    return [STEP_COMPLETED] * len(STEP_PLAN)
