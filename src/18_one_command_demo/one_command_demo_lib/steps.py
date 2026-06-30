"""Fixed wrapper step order and step-record helpers."""

from .errors import COMPLETED, FAILED, SKIPPED_AFTER_FAILURE

STEPS_ORDER = (
    ("step_001", "VALIDATE_CONFIG"),
    ("step_002", "CHECK_CONNECTED_DEMO_ROOT"),
    ("step_003", "RUN_CONNECTED_DEMO"),
    ("step_004", "VERIFY_CONNECTED_DEMO"),
    ("step_005", "READ_CONNECTED_DEMO_REPORT"),
    ("step_006", "CHECK_REQUIRED_STATUSES"),
    ("step_007", "WRITE_ONE_COMMAND_REPORT"),
    ("step_008", "VERIFY_ONE_COMMAND_OUTPUT"),
)


def build_steps(completed_through, failed_id=None):
    """Build the ordered steps list. completed_through is the number of steps that
    COMPLETED. If failed_id is given, that step is FAILED and later steps are
    SKIPPED_AFTER_FAILURE."""
    records = []
    failed_seen = False
    for index, (step_id, name) in enumerate(STEPS_ORDER):
        if failed_id is not None and step_id == failed_id:
            status = FAILED
            failed_seen = True
        elif failed_seen:
            status = SKIPPED_AFTER_FAILURE
        elif index < completed_through:
            status = COMPLETED
        else:
            status = SKIPPED_AFTER_FAILURE
        records.append({"step_id": step_id, "name": name, "status": status})
    return records


def all_completed():
    return build_steps(len(STEPS_ORDER))
