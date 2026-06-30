# sentinel_core/action_schema.py
# Strict structured-request validation.
#
# The deterministic core accepts ONLY structured action requests. It never
# accepts natural language. This module is the single gate that decides whether
# a dict is a well-formed CREATE_DIRECTORY request. Anything that is not a dict
# with exactly the expected fields, of the expected types, is rejected here
# before any path logic runs.

from sentinel_core.errors import SchemaError, require
from sentinel_core.versions import ACTION_SCHEMA_VERSION

ACTION_CREATE_DIRECTORY = "CREATE_DIRECTORY"
SUPPORTED_ACTIONS = frozenset({ACTION_CREATE_DIRECTORY})

# Exact field set for a v1.1.0 CREATE_DIRECTORY request.
#
# v1.1.0 REMOVED "allowed_root" from the request. The boundary is configured
# once in the run manifest and is AUTHORITATIVE: the kernel passes
# manifest["allowed_root"] into path policy. A request can no longer name (and
# thereby choose) its own root. A request that still carries "allowed_root" is
# rejected as an extra field (BLOCK_SCHEMA_INVALID), which fails closed for
# v1.0.0-style requests rather than silently honouring a caller-selected root.
_REQUIRED_FIELDS = frozenset({
    "request_id",
    "action_type",
    "target_path",
    "dry_run",
    "preconditions",
    "postconditions",
    "schema_version",
})

# The canonical declared pre/postconditions for CREATE_DIRECTORY. The request
# must declare exactly these (order-independent). This keeps the contract
# explicit and prevents silently-ignored or smuggled condition names.
_EXPECTED_PRECONDITIONS = frozenset({
    "target_absent",
    "parent_exists",
    "inside_allowed_root",
})
_EXPECTED_POSTCONDITIONS = frozenset({
    "target_exists",
    "target_is_directory",
})

_REQUEST_ID_MAX = 128
_PATH_MAX = 4096


def _is_clean_str(value) -> bool:
    if type(value) is not str:
        return False
    if value == "":
        return False
    # Reject control characters outright; they have no place in a path or id
    # and are a classic smuggling vector.
    for ch in value:
        if ord(ch) < 0x20 or ord(ch) == 0x7F:
            return False
    return True


def validate_action_request(request) -> dict:
    """Validate a structured action request.

    Returns a normalised copy of the request on success. Raises SchemaError
    with a precise message on any failure. Performs NO filesystem access and
    NO path-policy evaluation — purely structural.
    """
    require(type(request) is dict, "Action request must be a JSON object", SchemaError)

    keys = set(request.keys())
    require(
        keys == _REQUIRED_FIELDS,
        f"Action request field mismatch: "
        f"missing={sorted(_REQUIRED_FIELDS - keys)}, extra={sorted(keys - _REQUIRED_FIELDS)}",
        SchemaError,
    )

    require(
        request["schema_version"] == ACTION_SCHEMA_VERSION,
        f"Unsupported schema_version: {request['schema_version']!r} "
        f"(expected {ACTION_SCHEMA_VERSION!r})",
        SchemaError,
    )

    require(_is_clean_str(request["request_id"]), "request_id must be a non-empty clean string", SchemaError)
    require(len(request["request_id"]) <= _REQUEST_ID_MAX,
            f"request_id exceeds {_REQUEST_ID_MAX} characters", SchemaError)

    require(type(request["action_type"]) is str, "action_type must be a string", SchemaError)

    require(type(request["target_path"]) is str, "target_path must be a string", SchemaError)
    require(len(request["target_path"]) <= _PATH_MAX, "target_path is too long", SchemaError)

    require(type(request["dry_run"]) is bool, "dry_run must be a boolean", SchemaError)

    require(type(request["preconditions"]) is list, "preconditions must be an array", SchemaError)
    require(type(request["postconditions"]) is list, "postconditions must be an array", SchemaError)
    for item in request["preconditions"]:
        require(type(item) is str, "each precondition must be a string", SchemaError)
    for item in request["postconditions"]:
        require(type(item) is str, "each postcondition must be a string", SchemaError)

    require(
        set(request["preconditions"]) == _EXPECTED_PRECONDITIONS,
        f"preconditions must declare exactly {sorted(_EXPECTED_PRECONDITIONS)}",
        SchemaError,
    )
    require(
        set(request["postconditions"]) == _EXPECTED_POSTCONDITIONS,
        f"postconditions must declare exactly {sorted(_EXPECTED_POSTCONDITIONS)}",
        SchemaError,
    )

    # Return a normalised copy with conditions sorted for canonical receipts.
    normalised = {
        "request_id": request["request_id"],
        "action_type": request["action_type"],
        "target_path": request["target_path"],
        "dry_run": request["dry_run"],
        "preconditions": sorted(request["preconditions"]),
        "postconditions": sorted(request["postconditions"]),
        "schema_version": request["schema_version"],
    }
    return normalised


def is_supported_action(action_type: str) -> bool:
    return action_type in SUPPORTED_ACTIONS
