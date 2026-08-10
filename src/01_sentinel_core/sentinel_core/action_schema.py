# sentinel_core/action_schema.py
# Strict structured-request validation.
#
# The deterministic core accepts ONLY structured action requests. It never
# accepts natural language. This module is the single gate that decides whether
# a dict is a well-formed request for one of the SUPPORTED_ACTIONS. Anything
# that is not a dict with exactly the expected fields, of the expected types, is
# rejected here before any path logic runs.
#
# Move 62 (Part Two, step 62) adds a SECOND action, CREATE_TEXT_FILE, alongside
# the original CREATE_DIRECTORY. Validation dispatches on action_type: the
# CREATE_DIRECTORY path is byte-for-byte the v1.1.0 validation (unchanged), and
# CREATE_TEXT_FILE has its own exact field set and declared pre/postconditions.

from sentinel_core.errors import SchemaError, require
from sentinel_core.versions import ACTION_SCHEMA_VERSION

ACTION_CREATE_DIRECTORY = "CREATE_DIRECTORY"
ACTION_CREATE_TEXT_FILE = "CREATE_TEXT_FILE"
SUPPORTED_ACTIONS = frozenset({ACTION_CREATE_DIRECTORY, ACTION_CREATE_TEXT_FILE})

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

# ── CREATE_TEXT_FILE (Move 62) ───────────────────────────────────────────────
# CREATE_TEXT_FILE adds two request fields over CREATE_DIRECTORY:
#   content              - the exact UTF-8 text to write (bounded).
#   allowed_path_prefix  - a declared prefix the target must sit inside. This is
#                          NOT a licence to widen the boundary: path policy
#                          requires the prefix itself to resolve INSIDE the
#                          manifest-authoritative allowed_root, so a request can
#                          only NARROW, never widen, the boundary. Missing
#                          allowed_path_prefix is a schema failure (fail closed).
# The declared pre/postconditions use the Move 62 vocabulary from the action
# specification.
_REQUIRED_FIELDS_TEXT_FILE = frozenset({
    "request_id",
    "action_type",
    "target_path",
    "content",
    "allowed_path_prefix",
    "dry_run",
    "preconditions",
    "postconditions",
    "schema_version",
})
_EXPECTED_PRECONDITIONS_TEXT_FILE = frozenset({
    "parent_directory_exists",
    "path_absent",
    "path_inside_allowed_prefix",
})
_EXPECTED_POSTCONDITIONS_TEXT_FILE = frozenset({
    "file_exists",
    "file_content_hash_matches",
    "file_is_utf8_text",
})

_REQUEST_ID_MAX = 128
_PATH_MAX = 4096
# Content is bounded so a receipt (which records the request faithfully) stays
# bounded. A larger body is rejected at the schema gate rather than truncated.
_CONTENT_MAX_BYTES = 65536


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
    NO path-policy evaluation — purely structural. Dispatches on action_type so
    the CREATE_DIRECTORY contract is unchanged and CREATE_TEXT_FILE gets its own
    exact contract.
    """
    require(type(request) is dict, "Action request must be a JSON object", SchemaError)
    # Dispatch on action_type WITHOUT mutating behaviour for CREATE_DIRECTORY:
    # only an explicit CREATE_TEXT_FILE action takes the new path; everything
    # else (including unknown/missing action_type and malformed requests) goes
    # through the original CREATE_DIRECTORY validation exactly as before.
    if request.get("action_type") == ACTION_CREATE_TEXT_FILE:
        return _validate_create_text_file(request)
    return _validate_create_directory(request)


def _validate_create_directory(request) -> dict:
    """The v1.1.0 CREATE_DIRECTORY validation. Unchanged behaviour."""
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


def _validate_create_text_file(request) -> dict:
    """CREATE_TEXT_FILE validation (Move 62). Structural only, fail closed."""
    keys = set(request.keys())
    require(
        keys == _REQUIRED_FIELDS_TEXT_FILE,
        f"Action request field mismatch: "
        f"missing={sorted(_REQUIRED_FIELDS_TEXT_FILE - keys)}, "
        f"extra={sorted(keys - _REQUIRED_FIELDS_TEXT_FILE)}",
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

    # allowed_path_prefix is REQUIRED and must be a clean non-empty string. Its
    # absence already fails the field-set check above; this enforces its type.
    require(type(request["allowed_path_prefix"]) is str,
            "allowed_path_prefix must be a string", SchemaError)
    require(_is_clean_str(request["allowed_path_prefix"]),
            "allowed_path_prefix must be a non-empty clean string", SchemaError)
    require(len(request["allowed_path_prefix"]) <= _PATH_MAX,
            "allowed_path_prefix is too long", SchemaError)

    # content MUST be a real text string. Reject non-str (e.g. bytes, numbers,
    # arrays => "binary"/non-text), reject a NUL byte (a binary marker), and
    # reject anything that cannot be encoded as strict UTF-8 (lone surrogates).
    require(type(request["content"]) is str, "content must be a string (UTF-8 text)", SchemaError)
    require("\x00" not in request["content"], "content must not contain a NUL byte", SchemaError)
    try:
        encoded = request["content"].encode("utf-8", "strict")
    except UnicodeEncodeError as e:
        raise SchemaError(f"content is not valid UTF-8 text: {e}")
    require(len(encoded) <= _CONTENT_MAX_BYTES,
            f"content exceeds {_CONTENT_MAX_BYTES} bytes when UTF-8 encoded", SchemaError)

    require(type(request["dry_run"]) is bool, "dry_run must be a boolean", SchemaError)

    require(type(request["preconditions"]) is list, "preconditions must be an array", SchemaError)
    require(type(request["postconditions"]) is list, "postconditions must be an array", SchemaError)
    for item in request["preconditions"]:
        require(type(item) is str, "each precondition must be a string", SchemaError)
    for item in request["postconditions"]:
        require(type(item) is str, "each postcondition must be a string", SchemaError)

    require(
        set(request["preconditions"]) == _EXPECTED_PRECONDITIONS_TEXT_FILE,
        f"preconditions must declare exactly {sorted(_EXPECTED_PRECONDITIONS_TEXT_FILE)}",
        SchemaError,
    )
    require(
        set(request["postconditions"]) == _EXPECTED_POSTCONDITIONS_TEXT_FILE,
        f"postconditions must declare exactly {sorted(_EXPECTED_POSTCONDITIONS_TEXT_FILE)}",
        SchemaError,
    )

    normalised = {
        "request_id": request["request_id"],
        "action_type": request["action_type"],
        "target_path": request["target_path"],
        "content": request["content"],
        "allowed_path_prefix": request["allowed_path_prefix"],
        "dry_run": request["dry_run"],
        "preconditions": sorted(request["preconditions"]),
        "postconditions": sorted(request["postconditions"]),
        "schema_version": request["schema_version"],
    }
    return normalised


def is_supported_action(action_type: str) -> bool:
    return action_type in SUPPORTED_ACTIONS
