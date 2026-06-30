"""Ordered Stack Verifier v0.1 step records with short-circuit logic."""

from . import versions
from .errors import STEP_COMPLETED, STEP_FAILED, STEP_SKIPPED

STEP_PLAN = (
    ("step_001", "VALIDATE_INPUTS"),
    ("step_002", "VERIFY_SOURCE_STRUCTURE"),
    ("step_003", "VERIFY_SOURCE_CHECKSUMS"),
    ("step_004", "VERIFY_ATLAS_VOCABULARY"),
    ("step_005", "VERIFY_UNIFIED_MANIFEST"),
    ("step_006", "CROSS_CHECK_IDS_AND_STATUSES"),
    ("step_007", "CHECK_TRUTH_BOUNDARY"),
    ("step_008", "WRITE_STACK_VERIFICATION_REPORT"),
    ("step_009", "VERIFY_STACK_VERIFIER_OUTPUT"),
)


def build_steps(statuses):
    if len(statuses) != len(STEP_PLAN):
        raise ValueError("statuses length mismatch")
    steps = [{"step_id": sid, "operation": op, "status": status}
             for (sid, op), status in zip(STEP_PLAN, statuses)]
    return {"stack_verification_steps_version": versions.STACK_STEPS_VERSION,
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
