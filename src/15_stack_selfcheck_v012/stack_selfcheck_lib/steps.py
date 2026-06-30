"""Ordered Stack Selfcheck v0.1 step records with short-circuit logic."""

from . import versions
from .errors import STEP_COMPLETED, STEP_FAILED, STEP_SKIPPED

STEP_PLAN = (
    ("step_001", "VALIDATE_INVENTORY"),
    ("step_002", "CHECK_REQUIRED_COMPONENTS"),
    ("step_003", "CHECK_COMPONENT_ROOTS"),
    ("step_004", "CHECK_ZIP_SIDECARS"),
    ("step_005", "CHECK_DOCUMENTATION_BOUNDARIES"),
    ("step_006", "CHECK_TRUTH_BOUNDARY"),
    ("step_007", "CHECK_OPTIONAL_STACK_VERIFIER_OUTPUT"),
    ("step_008", "WRITE_STACK_SELFCHECK_REPORT"),
    ("step_009", "VERIFY_STACK_SELFCHECK_OUTPUT"),
)


def build_steps(statuses):
    if len(statuses) != len(STEP_PLAN):
        raise ValueError("statuses length mismatch")
    steps = [{"step_id": sid, "operation": op, "status": status}
             for (sid, op), status in zip(STEP_PLAN, statuses)]
    return {"stack_selfcheck_steps_version": versions.STACK_SELFCHECK_STEPS_VERSION,
            "steps": steps}


def all_completed():
    return [STEP_COMPLETED] * len(STEP_PLAN)


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
