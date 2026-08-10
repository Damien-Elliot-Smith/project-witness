# sentinel_core/decision.py
# Pure decision evaluation. No side effects, no filesystem mutation.
#
# Given a raw action request, decide what SHOULD happen. This function performs
# read-only path-policy evaluation but never creates anything. The kernel uses
# the Decision to drive persistence and (for ALLOW) execution.

from sentinel_core.action_schema import (
    validate_action_request, is_supported_action, ACTION_CREATE_DIRECTORY,
    ACTION_CREATE_TEXT_FILE,
)
from sentinel_core.errors import SchemaError
from sentinel_core.path_policy import evaluate_create_directory, evaluate_create_text_file
from sentinel_core.reason_codes import (
    ALLOW, BLOCK, DRY_RUN,
    ALLOW_CREATE_DIRECTORY, DRY_RUN_CREATE_DIRECTORY,
    ALLOW_CREATE_TEXT_FILE, DRY_RUN_CREATE_TEXT_FILE,
    BLOCK_SCHEMA_INVALID, BLOCK_UNKNOWN_ACTION,
)


class Decision:
    """A pure decision about a single action request.

    normalised_request is the schema-normalised request (or None if schema
    invalid). resolved_target is set only when the decision permits execution.
    """

    __slots__ = ("decision", "reason_code", "detail", "normalised_request", "resolved_target")

    def __init__(self, decision, reason_code, detail, normalised_request, resolved_target=None):
        self.decision = decision
        self.reason_code = reason_code
        self.detail = detail
        self.normalised_request = normalised_request
        self.resolved_target = resolved_target


def evaluate(raw_request, allowed_root: str) -> Decision:
    """Evaluate a raw action request into a pure Decision. No side effects.

    allowed_root is the AUTHORITATIVE boundary, taken from the run manifest by
    the kernel. It is never read from the request (v1.1.0 removed the field),
    so a request cannot select its own root.
    """
    # 1. Schema gate.
    try:
        request = validate_action_request(raw_request)
    except SchemaError as e:
        return Decision(BLOCK, BLOCK_SCHEMA_INVALID, {"schema_error": str(e)}, None)

    # 2. Action-type gate.
    if not is_supported_action(request["action_type"]):
        return Decision(BLOCK, BLOCK_UNKNOWN_ACTION,
                        {"action_type": request["action_type"]}, request)

    # 3. CREATE_DIRECTORY path policy (read-only).
    if request["action_type"] == ACTION_CREATE_DIRECTORY:
        result = evaluate_create_directory(request["target_path"], allowed_root)
        if not result.ok:
            return Decision(BLOCK, result.reason_code, dict(result.detail), request)
        if request["dry_run"]:
            return Decision(DRY_RUN, DRY_RUN_CREATE_DIRECTORY, dict(result.detail),
                            request, resolved_target=result.resolved_target)
        return Decision(ALLOW, ALLOW_CREATE_DIRECTORY, dict(result.detail),
                        request, resolved_target=result.resolved_target)

    # 4. CREATE_TEXT_FILE path policy (read-only). Move 62.
    if request["action_type"] == ACTION_CREATE_TEXT_FILE:
        result = evaluate_create_text_file(
            request["target_path"], allowed_root, request["allowed_path_prefix"])
        if not result.ok:
            return Decision(BLOCK, result.reason_code, dict(result.detail), request)
        if request["dry_run"]:
            return Decision(DRY_RUN, DRY_RUN_CREATE_TEXT_FILE, dict(result.detail),
                            request, resolved_target=result.resolved_target)
        return Decision(ALLOW, ALLOW_CREATE_TEXT_FILE, dict(result.detail),
                        request, resolved_target=result.resolved_target)

    # Unreachable given the action-type gate, but fail closed if reached.
    return Decision(BLOCK, BLOCK_UNKNOWN_ACTION,
                    {"action_type": request["action_type"]}, request)
