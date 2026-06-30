"""Ordered Companion v0.3 step records with short-circuit logic."""

from . import versions
from .errors import STEP_COMPLETED, STEP_FAILED, STEP_SKIPPED

STEP_PLAN = (
    ("step_001", "companion_cli", "VALIDATE_INPUTS"),
    ("step_002", "companion_cli", "WRITE_COORDINATOR_V03_REQUEST"),
    ("step_003", "coordinator_workflow_v03", "RUN_ATLAS_VALIDATED_WORKFLOW"),
    ("step_004", "coordinator_workflow_v03", "VERIFY_COORDINATOR_V03_OUTPUT"),
    ("step_005", "companion_cli", "MIRROR_ATLAS_TERMS"),
    ("step_006", "companion_cli", "WRITE_COMPANION_REPORT"),
    ("step_007", "companion_cli", "VERIFY_COMPANION_OUTPUT"),
)


def build_steps(statuses, case_id):
    if len(statuses) != len(STEP_PLAN):
        raise ValueError("statuses length mismatch")
    steps = []
    for (sid, comp, op), status in zip(STEP_PLAN, statuses):
        steps.append({"step_id": sid, "component": comp,
                      "operation": op, "status": status})
    return {
        "companion_steps_version": versions.COMPANION_STEPS_VERSION,
        "case_id": case_id,
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
