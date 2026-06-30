"""Ordered Coordinator v0.3 step records with short-circuit logic."""

from . import versions
from .errors import STEP_COMPLETED, STEP_FAILED, STEP_SKIPPED

STEP_PLAN = (
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


def build_steps(statuses):
    if len(statuses) != len(STEP_PLAN):
        raise ValueError("statuses length mismatch")
    steps = []
    for (sid, op), status in zip(STEP_PLAN, statuses):
        steps.append({"step_id": sid, "operation": op, "status": status})
    return {
        "coordinator_workflow_steps_version": versions.COORDINATOR_WORKFLOW_VERSION,
        "steps": steps,
    }


def statuses_with_failure_at(index):
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
