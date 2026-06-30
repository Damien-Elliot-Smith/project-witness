# evidence_reasoning_demo/steps.py
# Build the ordered demo_steps document. The six steps are fixed; their statuses
# reflect how far the chain got (COMPLETED, FAILED, or SKIPPED_AFTER_FAILURE).

from evidence_reasoning_demo import versions

# Fixed ordered (component, operation) sequence.
STEP_SEQUENCE = (
    ("aletheia_evidence_bundle", "bundle-file"),
    ("aletheia_evidence_bundle", "verify"),
    ("aletheia_odin_bridge", "convert"),
    ("aletheia_odin_bridge", "verify"),
    ("odin_claim_reasoner", "reason"),
    ("odin_claim_reasoner", "verify"),
)


def build_steps(case_id, completed_count, failed_index=None):
    """Build the steps doc. `completed_count` steps are COMPLETED; if `failed_index`
    is not None, that step is FAILED and all later steps are SKIPPED_AFTER_FAILURE.
    """
    steps = []
    for i, (component, operation) in enumerate(STEP_SEQUENCE):
        if failed_index is not None and i == failed_index:
            status = versions.STEP_FAILED
        elif failed_index is not None and i > failed_index:
            status = versions.STEP_SKIPPED_AFTER_FAILURE
        elif i < completed_count:
            status = versions.STEP_COMPLETED
        else:
            status = versions.STEP_SKIPPED_AFTER_FAILURE
        steps.append({
            "step_id": f"step_{i + 1:03d}",
            "component": component,
            "operation": operation,
            "status": status,
        })
    return {
        "demo_steps_version": versions.DEMO_STEPS_VERSION,
        "case_id": case_id,
        "steps": steps,
    }


def all_completed_steps(case_id):
    return build_steps(case_id, completed_count=len(STEP_SEQUENCE))
