# sentinel_core/reason_codes.py
# Frozen decision and reason-code registry.
# Decisions are narrow. Every receipt carries exactly one decision and one
# reason code, and the pairing is validated when a receipt is built.

# ── Decisions ──────────────────────────────────────────────────────────────
ALLOW = "ALLOW"
BLOCK = "BLOCK"
DRY_RUN = "DRY_RUN"
ERROR = "ERROR"

VALID_DECISIONS = frozenset({ALLOW, BLOCK, DRY_RUN, ERROR})

# ── Receipt stages (v0.2) ───────────────────────────────────────────────────
# Every receipt belongs to exactly one stage:
#   INTENT  - the action was approved for attempted execution but has NOT yet
#             executed. Persisted (and committed) BEFORE any filesystem
#             mutation, so a crash leaves a durable, detectable record of the
#             pending action. executed is always False on an INTENT.
#   RESULT  - the outcome was recorded. An ALLOW path's RESULT references its
#             INTENT (intent_receipt_id + intent_hash). BLOCK and DRY_RUN are
#             self-contained RESULT receipts with no INTENT (nothing was ever
#             approved for execution, so nothing needed pre-durability).
#   SESSION_CLOSE - the terminal close receipt.
STAGE_INTENT = "INTENT"
STAGE_RESULT = "RESULT"
STAGE_SESSION_CLOSE = "SESSION_CLOSE"
VALID_STAGES = frozenset({STAGE_INTENT, STAGE_RESULT, STAGE_SESSION_CLOSE})

# ── Reason codes ───────────────────────────────────────────────────────────
INTENT_CREATE_DIRECTORY = "INTENT_CREATE_DIRECTORY"
ALLOW_CREATE_DIRECTORY = "ALLOW_CREATE_DIRECTORY"
ALLOW_SESSION_CLOSE = "ALLOW_SESSION_CLOSE"
DRY_RUN_CREATE_DIRECTORY = "DRY_RUN_CREATE_DIRECTORY"
# CREATE_TEXT_FILE (Move 62): second Sentinel action, same receipt protocol.
INTENT_CREATE_TEXT_FILE = "INTENT_CREATE_TEXT_FILE"
ALLOW_CREATE_TEXT_FILE = "ALLOW_CREATE_TEXT_FILE"
DRY_RUN_CREATE_TEXT_FILE = "DRY_RUN_CREATE_TEXT_FILE"

BLOCK_SCHEMA_INVALID = "BLOCK_SCHEMA_INVALID"
BLOCK_UNKNOWN_ACTION = "BLOCK_UNKNOWN_ACTION"
BLOCK_PATH_TRAVERSAL = "BLOCK_PATH_TRAVERSAL"
BLOCK_OUTSIDE_ALLOWED_ROOT = "BLOCK_OUTSIDE_ALLOWED_ROOT"
BLOCK_TARGET_ALREADY_EXISTS = "BLOCK_TARGET_ALREADY_EXISTS"
BLOCK_PARENT_MISSING = "BLOCK_PARENT_MISSING"
BLOCK_PARENT_NOT_DIRECTORY = "BLOCK_PARENT_NOT_DIRECTORY"
BLOCK_SYMLINK_RISK = "BLOCK_SYMLINK_RISK"
BLOCK_ABSOLUTE_TARGET_NOT_ALLOWED = "BLOCK_ABSOLUTE_TARGET_NOT_ALLOWED"
BLOCK_EMPTY_PATH = "BLOCK_EMPTY_PATH"
BLOCK_ALLOWED_ROOT_MISSING = "BLOCK_ALLOWED_ROOT_MISSING"
BLOCK_ALLOWED_ROOT_NOT_DIRECTORY = "BLOCK_ALLOWED_ROOT_NOT_DIRECTORY"
BLOCK_SESSION_CLOSED = "BLOCK_SESSION_CLOSED"

ERROR_PERSISTENCE_FAILED = "ERROR_PERSISTENCE_FAILED"
ERROR_POSTCONDITION_FAILED = "ERROR_POSTCONDITION_FAILED"
ERROR_EXECUTION_FAILED = "ERROR_EXECUTION_FAILED"

# ── Registry ───────────────────────────────────────────────────────────────
_ALLOW_CODES = frozenset({INTENT_CREATE_DIRECTORY, ALLOW_CREATE_DIRECTORY, ALLOW_SESSION_CLOSE,
                         INTENT_CREATE_TEXT_FILE, ALLOW_CREATE_TEXT_FILE})
_DRY_RUN_CODES = frozenset({DRY_RUN_CREATE_DIRECTORY, DRY_RUN_CREATE_TEXT_FILE})
_BLOCK_CODES = frozenset({
    BLOCK_SCHEMA_INVALID,
    BLOCK_UNKNOWN_ACTION,
    BLOCK_PATH_TRAVERSAL,
    BLOCK_OUTSIDE_ALLOWED_ROOT,
    BLOCK_TARGET_ALREADY_EXISTS,
    BLOCK_PARENT_MISSING,
    BLOCK_PARENT_NOT_DIRECTORY,
    BLOCK_SYMLINK_RISK,
    BLOCK_ABSOLUTE_TARGET_NOT_ALLOWED,
    BLOCK_EMPTY_PATH,
    BLOCK_ALLOWED_ROOT_MISSING,
    BLOCK_ALLOWED_ROOT_NOT_DIRECTORY,
    BLOCK_SESSION_CLOSED,
})
_ERROR_CODES = frozenset({
    ERROR_PERSISTENCE_FAILED,
    ERROR_POSTCONDITION_FAILED,
    ERROR_EXECUTION_FAILED,
})

_DECISION_TO_CODES = {
    ALLOW: _ALLOW_CODES,
    DRY_RUN: _DRY_RUN_CODES,
    BLOCK: _BLOCK_CODES,
    ERROR: _ERROR_CODES,
}

_ALL_CODES = _ALLOW_CODES | _DRY_RUN_CODES | _BLOCK_CODES | _ERROR_CODES

_DESCRIPTIONS = {
    INTENT_CREATE_DIRECTORY: "Directory creation approved; intent recorded before execution.",
    ALLOW_CREATE_DIRECTORY: "Directory creation passed all checks and was executed.",
    ALLOW_SESSION_CLOSE: "Operator closed the session; the run was sealed.",
    DRY_RUN_CREATE_DIRECTORY: "Directory creation passed all checks; dry-run, not executed.",
    INTENT_CREATE_TEXT_FILE: "Text-file creation approved; intent recorded before execution.",
    ALLOW_CREATE_TEXT_FILE: "Text-file creation passed all checks and was executed.",
    DRY_RUN_CREATE_TEXT_FILE: "Text-file creation passed all checks; dry-run, not executed.",
    BLOCK_SCHEMA_INVALID: "The action request failed schema validation.",
    BLOCK_UNKNOWN_ACTION: "The action_type is not supported by this Sentinel version.",
    BLOCK_PATH_TRAVERSAL: "The target path used traversal to escape allowed_root.",
    BLOCK_OUTSIDE_ALLOWED_ROOT: "The resolved target lies outside allowed_root.",
    BLOCK_TARGET_ALREADY_EXISTS: "The target path already exists; no overwrite is permitted.",
    BLOCK_PARENT_MISSING: "The parent directory of the target does not exist.",
    BLOCK_PARENT_NOT_DIRECTORY: "The parent path exists but is not a directory.",
    BLOCK_SYMLINK_RISK: "A symlink in the path could allow escape from allowed_root.",
    BLOCK_ABSOLUTE_TARGET_NOT_ALLOWED: "An absolute target path outside allowed_root was supplied.",
    BLOCK_EMPTY_PATH: "The target path was empty.",
    BLOCK_ALLOWED_ROOT_MISSING: "The allowed_root does not exist.",
    BLOCK_ALLOWED_ROOT_NOT_DIRECTORY: "The allowed_root exists but is not a directory.",
    BLOCK_SESSION_CLOSED: "The session is closed; the request was refused.",
    ERROR_PERSISTENCE_FAILED: "Receipt persistence failed; no state was committed.",
    ERROR_POSTCONDITION_FAILED: "The action executed but a postcondition did not hold.",
    ERROR_EXECUTION_FAILED: "The action raised an OS error during execution.",
}


def all_codes() -> frozenset:
    return _ALL_CODES


def valid_pairing(decision: str, reason_code: str) -> bool:
    return reason_code in _DECISION_TO_CODES.get(decision, frozenset())


def describe(reason_code: str) -> str:
    return _DESCRIPTIONS.get(reason_code, "(no description)")


# ── Session-close protocol (v0.1.3) ─────────────────────────────────────────
# Single source of truth for what a session-closing receipt must look like.
# Only an ALLOW_SESSION_CLOSE receipt with this EXACT shape may transition a
# session OPEN -> CLOSED_BY_OPERATOR; every other receipt must stay OPEN ->
# OPEN. receipts.py, run_seal.py and replay.py all enforce against this one
# definition so the closure grammar cannot drift between layers. This closes
# the v0.1.2 gap where a CREATE/BLOCK/DRY_RUN/ERROR receipt could have its
# post_session_state edited to CLOSED, be rehashed, and pass.

CLOSE_SESSION_ACTION_TYPE = "CLOSE_SESSION"

# The exact, canonical request object a close receipt must carry.
CLOSE_SESSION_REQUEST = {"action_type": CLOSE_SESSION_ACTION_TYPE}


def is_session_close_shape(decision, reason_code, request, executed) -> bool:
    """True iff this receipt has the EXACT, complete session-close shape.

    A receipt may transition OPEN -> CLOSED_BY_OPERATOR only when every one of
    these holds: decision=ALLOW, reason_code=ALLOW_SESSION_CLOSE,
    request={'action_type': 'CLOSE_SESSION'}, executed is False. Any deviation
    means it is not a legitimate close receipt.
    """
    return (
        decision == ALLOW
        and reason_code == ALLOW_SESSION_CLOSE
        and executed is False
        and request == CLOSE_SESSION_REQUEST
    )


# ── Stage helpers (v0.2) ────────────────────────────────────────────────────
# The reason codes that mark a receipt as an INTENT (approved, not yet
# executed). Every two-stage action contributes exactly one INTENT code.
INTENT_REASON_CODES = frozenset({INTENT_CREATE_DIRECTORY, INTENT_CREATE_TEXT_FILE})


def stage_for_reason(reason_code) -> str:
    """The stage a given reason_code must belong to."""
    if reason_code in INTENT_REASON_CODES:
        return STAGE_INTENT
    if reason_code == ALLOW_SESSION_CLOSE:
        return STAGE_SESSION_CLOSE
    return STAGE_RESULT
