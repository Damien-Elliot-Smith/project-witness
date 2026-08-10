"""Move 81 structured-verdict adapter.

Reads the existing adopted verification lanes WITHOUT changing their
default output or verdict behaviour, and emits exactly one canonical
structured record describing the outcome. This adds no verification
capability and creates no Rust PASS path.

Trust model (binding clarification 3): the adapter NEVER searches PATH
and NEVER chooses defaults. Every implementation and authority path is
supplied explicitly as an absolute path and validated. The adapter merely
executes what it is explicitly given; it does not itself claim those
paths are trusted -- the Move 81 adoption gate is responsible for
resolving and validating trusted paths and passing them in.

Output contract (binding clarification 8): exactly one canonical
top-level JSON object followed by exactly one newline on stdout, and
nothing else -- no progress text, headings, debug lines, multiple
objects, or legacy verifier output. Underlying verifier output is
captured internally and validated before the structured object is
emitted.

Exit contract (binding clarification 4) is implemented in main().
"""

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import schema  # noqa: E402  (local module, explicit sys.path above)


# A deterministic default timeout (seconds) for underlying verifier
# invocation. Fixed constant; never derived from input. The gate/tests
# may override via --timeout for controlled timeout proofs.
DEFAULT_TIMEOUT_SECONDS = 120


class AdapterMeasurementError(Exception):
    """Raised internally when the underlying verifier result cannot be
    honestly established. Carries the adapter measurement_error_code and
    optional already-established context fields."""

    def __init__(self, code, detail=None, exit_code=None):
        super().__init__(code)
        self.code = code
        self.detail = detail
        self.exit_code = exit_code


# ----------------------------------------------------------------------
# Path validation (no PATH search, no defaults)
# ----------------------------------------------------------------------

def _require_abs_regular_file(path, what):
    if path is None:
        raise ValueError("missing required path: %s" % what)
    if not os.path.isabs(path):
        raise ValueError("%s must be an absolute path: %r" % (what, path))
    if not os.path.exists(path):
        raise ValueError("%s does not exist: %r" % (what, path))
    if not os.path.isfile(path):
        raise ValueError("%s is not a regular file: %r" % (what, path))


def _require_abs_readable_file(path, what):
    _require_abs_regular_file(path, what)
    if not os.access(path, os.R_OK):
        raise ValueError("%s is not readable: %r" % (what, path))


def _require_abs_executable(path, what):
    _require_abs_regular_file(path, what)
    if not os.access(path, os.X_OK):
        raise ValueError("%s is not executable: %r" % (what, path))


# ----------------------------------------------------------------------
# Deterministic safety check for the optional detail field
# ----------------------------------------------------------------------

_UNSAFE_DETAIL_PATTERNS = (
    re.compile(r"/"),                      # any slash: path disclosure risk
    re.compile(r"\\"),                     # backslash path
    re.compile(r"[A-Za-z]:\\"),            # windows drive
    re.compile(r"\btmp\b|/tmp|TMPDIR|tmp[0-9A-Za-z]{4,}"),  # temp dirs
    re.compile(r"\d{4}-\d{2}-\d{2}"),      # date-like
    re.compile(r"\d{2}:\d{2}:\d{2}"),      # time-like
    re.compile(r"0x[0-9a-fA-F]+"),         # pointer-ish
)


def _detail_is_safe(text):
    """A detail string is included ONLY when it is demonstrably free of
    absolute paths, temp-dir names, host-specific values, timestamps,
    random values, nondeterministically ordered data, and input-derived
    path disclosure. Conservative: any slash or suspicious token omits it.
    """
    if text is None:
        return False
    if not isinstance(text, str):
        return False
    if text == "":
        return True
    for pat in _UNSAFE_DETAIL_PATTERNS:
        if pat.search(text):
            return False
    # printable ASCII only, to avoid uncontrolled encodings
    if any(ord(ch) < 0x20 or ord(ch) > 0x7E for ch in text):
        return False
    return True


# ----------------------------------------------------------------------
# reason_map (frozen, supplied explicitly)
# ----------------------------------------------------------------------

_REASON_MAP_LANES = ("python_bundle", "rust_bundle", "archive")
_REASON_MATCH_TYPES = ("exact", "regex")


def load_reason_map(reason_map_path):
    """Load and COMPLETELY validate the inherited frozen reason map.

    Every entry is validated here, BEFORE any verifier is invoked, so an
    unusable authority can never cause a verifier to run and can never
    surface later as an uncaught AttributeError/KeyError/TypeError/
    re.error traceback part-way through a measurement.

    Semantics (existing, unchanged): an unusable --reason-map is adapter
    CLI misuse, exactly as an absent lane already was. It raises
    ValueError, which main() reports as a usage error -- adapter exit 2,
    NO record emitted, deterministic usage text on stderr, no traceback.
    This uses only the existing adapter failure vocabulary; no new schema
    version and no new measurement-error code is introduced."""
    _require_abs_readable_file(reason_map_path, "--reason-map")
    try:
        with open(reason_map_path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (ValueError, OSError):
        raise ValueError("--reason-map is not readable JSON")
    if not isinstance(data, dict):
        raise ValueError("--reason-map is not a JSON object")
    for lane in _REASON_MAP_LANES:
        if lane not in data or not isinstance(data[lane], list):
            raise ValueError("reason_map missing lane: %s" % lane)
        for entry in data[lane]:
            _validate_reason_entry(lane, entry)
    return data


def _validate_reason_entry(lane, entry):
    """Validate one reason-map entry. Raises ValueError (adapter usage
    error) on any structural problem, so nothing malformed can reach the
    matching code path later."""
    if not isinstance(entry, dict):
        raise ValueError("reason_map %s entry is not an object" % lane)
    match_type = entry.get("match_type")
    if match_type not in _REASON_MATCH_TYPES:
        raise ValueError(
            "reason_map %s entry has missing or unknown match_type" % lane)
    value = entry.get("value")
    if not isinstance(value, str) or value == "":
        raise ValueError(
            "reason_map %s entry has missing or non-string value" % lane)
    if match_type == "regex":
        try:
            re.compile(value)
        except re.error:
            raise ValueError(
                "reason_map %s entry has a malformed regex value" % lane)
    reason_class = entry.get("class")
    if not isinstance(reason_class, str) or reason_class.strip() == "":
        raise ValueError(
            "reason_map %s entry has missing or non-string class" % lane)
    stage = entry.get("stage")
    if not isinstance(stage, str) or stage.strip() == "":
        raise ValueError(
            "reason_map %s entry has missing or non-string stage" % lane)


def _resolve_reason_and_stage(reason_map, map_lane, raw_value):
    """Resolve (class, stage) for a raw reason value using the frozen map
    for the given lane. Exact matches take precedence over regex. Returns
    (reason_class, stage). Raises AdapterMeasurementError(UNKNOWN_REASON)
    if no entry matches; a matched entry without a stage raises
    MISSING_STAGE_MAPPING."""
    entries = reason_map[map_lane]
    # exact matches first
    for entry in entries:
        if entry.get("match_type") == "exact" and entry.get("value") == raw_value:
            return _entry_class_stage(entry)
    # then regex
    for entry in entries:
        if entry.get("match_type") == "regex":
            try:
                if re.search(entry["value"], raw_value):
                    return _entry_class_stage(entry)
            except re.error:
                # a malformed frozen pattern is not something we invent
                # around; treat as unusable mapping
                raise AdapterMeasurementError(schema.ERR_MISSING_STAGE_MAPPING)
    raise AdapterMeasurementError(schema.ERR_UNKNOWN_REASON)


def _entry_class_stage(entry):
    reason_class = entry.get("class")
    stage = entry.get("stage")
    if not reason_class:
        raise AdapterMeasurementError(schema.ERR_UNKNOWN_REASON)
    if not stage:
        raise AdapterMeasurementError(schema.ERR_MISSING_STAGE_MAPPING)
    return reason_class, stage


# ----------------------------------------------------------------------
# Python implementation version (binding clarification 5)
# ----------------------------------------------------------------------

def resolve_python_verifier_version(python_entry):
    """Obtain the Python verifier's authoritative implementation version
    from its OWN source tree (companion_lib/versions.COMPANION_CLI_VERSION),
    NEVER from the input bundle. Returns the version string, or None if
    the adopted implementation does not expose an authoritative constant
    (in which case verifier_version is omitted for the Python lane).

    python_entry is the absolute path to the adopted companion.py entry
    point; its sibling companion_lib/versions.py is the authority.
    """
    entry_dir = os.path.dirname(os.path.abspath(python_entry))
    versions_path = os.path.join(entry_dir, "companion_lib", "versions.py")
    if not os.path.isfile(versions_path):
        return None
    # Parse the constant literally from source without importing, so no
    # implementation code runs inside the adapter and no sys.path games
    # are needed. Deterministic single-line constant.
    pattern = re.compile(
        r'^COMPANION_CLI_VERSION\s*=\s*"([^"]+)"\s*$', re.MULTILINE)
    with open(versions_path, encoding="utf-8") as handle:
        text = handle.read()
    match = pattern.search(text)
    if not match:
        return None
    return match.group(1)


# ----------------------------------------------------------------------
# Underlying invocation + validation (fail closed)
# ----------------------------------------------------------------------

def _run(argv, timeout):
    """Invoke an underlying verifier. Returns (exit_code, stdout_bytes,
    stderr_bytes). Raises AdapterMeasurementError for launch failure,
    timeout, or signal termination."""
    try:
        proc = subprocess.run(
            argv, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise AdapterMeasurementError(schema.ERR_TIMEOUT)
    except OSError:
        # EVERY launch-time OS failure is an invocation error: a missing
        # file, a permission refusal, an invalid executable format
        # (Errno 8 "Exec format error" -- which an absolute, regular,
        # chmod-executable file can still produce), and any other
        # OS-level refusal to start the process. FileNotFoundError and
        # PermissionError are OSError subclasses, so this subsumes them.
        #
        # No exit_code is recorded: the process never completed normally,
        # so there is no honestly established exit status. No detail is
        # attached either, so no path or host string can leak into the
        # canonical record.
        raise AdapterMeasurementError(schema.ERR_INVOCATION_ERROR)
    rc = proc.returncode
    if rc is not None and rc < 0:
        # Terminated by signal N (returncode -N). A negative value is
        # SIGNAL METADATA, not a normal process exit code, so no exit_code
        # is recorded: exit_code is retained only when the underlying
        # process completed normally.
        raise AdapterMeasurementError(schema.ERR_SIGNAL_TERMINATION)
    return rc, proc.stdout, proc.stderr


def _parse_single_json_object(stdout_bytes, stderr_bytes):
    """Validate that stdout is EXACTLY one canonical JSON object,
    optionally followed by exactly one trailing newline, and that stderr
    is empty. Surrounding whitespace/blank lines/prefix/suffix are
    contamination, not harmless formatting. Returns the parsed object.
    Fails closed.

    Underlying stderr is rejected for EVERY lane (repair 2): any stderr
    bytes -> ADAPTER_UNEXPECTED_STDERR."""
    if stderr_bytes:
        raise AdapterMeasurementError(schema.ERR_UNEXPECTED_STDERR)
    try:
        text = stdout_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise AdapterMeasurementError(schema.ERR_MALFORMED_JSON)
    if text == "":
        raise AdapterMeasurementError(schema.ERR_INCOMPLETE_RESULT)
    # Strict framing: the object must start at byte 0 (no leading
    # whitespace/blank lines/prefix) and be followed by at most a single
    # trailing newline (no trailing spaces, extra blank lines, or suffix).
    if text[0] != "{":
        # distinguish contamination (a valid object appears later) from
        # outright malformed JSON (no object at all)
        brace = text.find("{")
        if brace != -1:
            decoder = json.JSONDecoder()
            try:
                obj, _ = decoder.raw_decode(text[brace:])
                if isinstance(obj, dict):
                    raise AdapterMeasurementError(
                        schema.ERR_STDOUT_CONTAMINATION)
            except AdapterMeasurementError:
                raise
            except ValueError:
                pass
        raise AdapterMeasurementError(schema.ERR_MALFORMED_JSON)
    decoder = json.JSONDecoder()
    try:
        obj, end = decoder.raw_decode(text)
    except ValueError:
        raise AdapterMeasurementError(schema.ERR_MALFORMED_JSON)
    trailer = text[end:]
    # accept exactly zero or one trailing newline and nothing else
    if trailer not in ("", "\n"):
        # anything else after the object: another object, or stray
        # whitespace/text -> contamination or multiple objects
        stripped_trailer = trailer.strip()
        if stripped_trailer.startswith("{"):
            raise AdapterMeasurementError(schema.ERR_MULTIPLE_OBJECTS)
        raise AdapterMeasurementError(schema.ERR_STDOUT_CONTAMINATION)
    if not isinstance(obj, dict):
        raise AdapterMeasurementError(schema.ERR_MALFORMED_JSON)
    return obj


# ----------------------------------------------------------------------
# Lane verdict construction
# ----------------------------------------------------------------------

def _verdict_record(lane, operation, input_type, verdict, reason_code,
                    stage, exit_code, verifier_version, detail):
    rec = schema.envelope(schema.RECORD_VERDICT)
    rec["implementation_lane"] = lane
    rec["verifier"] = schema.LANE_VERIFIER[lane]
    if verifier_version is not None:
        rec["verifier_version"] = verifier_version
    rec["operation"] = operation
    rec["input_type"] = input_type
    rec["verdict"] = verdict
    rec["reason_code"] = reason_code
    rec["stage"] = stage
    rec["capability_scope"] = schema.LANE_CAPABILITY_SCOPE[lane]
    rec["exit_code"] = exit_code
    if detail is not None and _detail_is_safe(detail):
        rec["detail"] = detail
    return rec


def _check_verdict_exit_pair(lane, verdict, exit_code):
    allowed = schema.LANE_VERDICT_EXIT[lane]
    if verdict not in allowed or allowed[verdict] != exit_code:
        raise AdapterMeasurementError(
            schema.ERR_IMPOSSIBLE_VERDICT_EXIT_PAIR, exit_code=exit_code)


def evaluate_python_bundle(python_bin, python_entry, bundle_dir,
                           reason_map, timeout,
                           verifier_version):
    """Invoke the adopted Python companion verify and normalize its
    result into a verdict record. Fails closed on any measurement
    problem.

    Reason normalization matches the adopted harness behaviour exactly:
        out.get("error", out.get("reason", ""))
    i.e. the "error" key is used first when present, otherwise "reason".
    A genuine Python FAIL commonly reports its cause under "error"."""
    argv = [python_bin, python_entry, "verify", "--run", bundle_dir]
    rc, out, err = _run(argv, timeout)
    # EXIT 2 TAKES PRECEDENCE. A usage/invocation failure is never a
    # verification verdict, and its stdout/stderr must NOT be parsed or
    # reinterpreted as a verifier result: usage text on stderr is normal
    # for an invocation failure and must not become UNEXPECTED_STDERR.
    if rc == 2:
        raise AdapterMeasurementError(schema.ERR_INVOCATION_ERROR,
                                      exit_code=2)
    obj = _parse_single_json_object(out, err)
    if "verify_ok" not in obj:
        raise AdapterMeasurementError(schema.ERR_INCOMPLETE_RESULT,
                                      exit_code=rc)
    verify_ok = obj.get("verify_ok")
    if verify_ok is True:
        verdict = schema.VERDICT_PASS
        # PASS uses "reason" (adopted PASS form: reason="companion completed")
        raw_reason = obj.get("reason", "")
    elif verify_ok is False:
        verdict = schema.VERDICT_FAIL
        # FAIL: adopted harness uses out.get("error", out.get("reason",""))
        raw_reason = obj.get("error", obj.get("reason", ""))
    else:
        raise AdapterMeasurementError(schema.ERR_INCOMPLETE_RESULT,
                                      exit_code=rc)
    # an empty or non-string reason/error fails closed
    if not isinstance(raw_reason, str) or raw_reason == "":
        raise AdapterMeasurementError(schema.ERR_INCOMPLETE_RESULT,
                                      exit_code=rc)
    _check_verdict_exit_pair(schema.LANE_PYTHON, verdict, rc)
    reason_class, stage = _resolve_reason_and_stage(
        reason_map, "python_bundle", raw_reason)
    return _verdict_record(
        schema.LANE_PYTHON, schema.OP_VERIFY_BUNDLE,
        schema.INPUT_BUNDLE_DIR, verdict, reason_class, stage, rc,
        verifier_version, raw_reason)


def _rust_version_from_obj(obj):
    """The Rust verifier's authoritative version is embedded by the
    executing binary itself in every emitted line as the "version" field.
    Read it from the actual invocation output (NOT from a hardcoded
    adapter constant and NOT from the input bundle). A missing/blank
    version from a binary that always self-reports is an incomplete
    result."""
    version = obj.get("version")
    if not version or not isinstance(version, str):
        raise AdapterMeasurementError(schema.ERR_INCOMPLETE_RESULT)
    return version


def _require_rust_identity(obj):
    """Repair 5: require the underlying Rust object to self-identify as
    witness-verify. Absent, non-string, empty, or different -> measurement
    error (never inferred from the selected lane)."""
    verifier = obj.get("verifier")
    if not isinstance(verifier, str) or verifier == "" \
            or verifier != schema.VERIFIER_RUST:
        raise AdapterMeasurementError(
            schema.ERR_VERIFIER_IDENTITY_MISMATCH)


def evaluate_rust_bundle(rust_bin, bundle_dir, reason_map, timeout):
    argv = [rust_bin, "verify", bundle_dir]
    rc, out, err = _run(argv, timeout)
    # EXIT 2 TAKES PRECEDENCE (see evaluate_python_bundle).
    if rc == 2:
        raise AdapterMeasurementError(schema.ERR_INVOCATION_ERROR,
                                      exit_code=2)
    obj = _parse_single_json_object(out, err)
    _require_rust_identity(obj)
    verdict = obj.get("verdict")
    if verdict not in (schema.VERDICT_FAIL, schema.VERDICT_INCONCLUSIVE):
        raise AdapterMeasurementError(
            schema.ERR_IMPOSSIBLE_VERDICT_EXIT_PAIR, exit_code=rc)
    _check_verdict_exit_pair(schema.LANE_RUST, verdict, rc)
    raw_reason = obj.get("reason_code")
    if not isinstance(raw_reason, str) or raw_reason == "":
        raise AdapterMeasurementError(schema.ERR_INCOMPLETE_RESULT,
                                      exit_code=rc)
    reason_class, stage = _resolve_reason_and_stage(
        reason_map, "rust_bundle", raw_reason)
    rust_version = _rust_version_from_obj(obj)
    return _verdict_record(
        schema.LANE_RUST, schema.OP_VERIFY_BUNDLE, schema.INPUT_BUNDLE_DIR,
        verdict, reason_class, stage, rc, rust_version, obj.get("detail"))


def evaluate_archive(rust_bin, archive_zip, reason_map, timeout):
    argv = [rust_bin, "inspect-archive", archive_zip]
    rc, out, err = _run(argv, timeout)
    # EXIT 2 TAKES PRECEDENCE (see evaluate_python_bundle).
    if rc == 2:
        raise AdapterMeasurementError(schema.ERR_INVOCATION_ERROR,
                                      exit_code=2)
    obj = _parse_single_json_object(out, err)
    _require_rust_identity(obj)
    verdict = obj.get("verdict")
    if verdict not in (schema.VERDICT_FAIL, schema.VERDICT_INCONCLUSIVE):
        raise AdapterMeasurementError(
            schema.ERR_IMPOSSIBLE_VERDICT_EXIT_PAIR, exit_code=rc)
    _check_verdict_exit_pair(schema.LANE_ARCHIVE, verdict, rc)
    raw_reason = obj.get("reason_code")
    if not isinstance(raw_reason, str) or raw_reason == "":
        raise AdapterMeasurementError(schema.ERR_INCOMPLETE_RESULT,
                                      exit_code=rc)
    reason_class, stage = _resolve_reason_and_stage(
        reason_map, "archive", raw_reason)
    rust_version = _rust_version_from_obj(obj)
    return _verdict_record(
        schema.LANE_ARCHIVE, schema.OP_INSPECT_ARCHIVE,
        schema.INPUT_ARCHIVE_ZIP, verdict, reason_class, stage, rc,
        rust_version, obj.get("detail"))


# ----------------------------------------------------------------------
# measurement-error record
# ----------------------------------------------------------------------

def measurement_error_record(code, lane=None, operation=None,
                             input_type=None, exit_code=None, detail=None):
    rec = schema.envelope(schema.RECORD_MEASUREMENT_ERROR)
    if lane is not None:
        rec["implementation_lane"] = lane
    if operation is not None:
        rec["operation"] = operation
    if input_type is not None:
        rec["input_type"] = input_type
    rec["measurement_error_code"] = code
    if exit_code is not None:
        rec["exit_code"] = exit_code
    if detail is not None and _detail_is_safe(detail):
        rec["detail"] = detail
    return rec


# ----------------------------------------------------------------------
# canonical serialization + single-object emission
# ----------------------------------------------------------------------

def canonical_bytes(obj):
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False) + "\n").encode("utf-8")


def emit(obj):
    sys.stdout.buffer.write(canonical_bytes(obj))
    sys.stdout.buffer.flush()


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

_USAGE = (
    "usage: adapter.py verdict --lane <python_bundle|rust_bundle|archive>\n"
    "         --input <path> --reason-map <path>\n"
    "         [--python-bin <path>] [--python-entry <path>]\n"
    "         [--rust-bin <path>] [--timeout <seconds>]\n"
    "       adapter.py compare --input <bundle_dir> --reason-map <path>\n"
    "         --python-bin <path> --python-entry <path> --rust-bin <path>\n"
    "         --case-id <id> --comparison-contract <path>\n"
    "         [--timeout <seconds>]\n"
)


def _usage_error(message):
    sys.stderr.write(message.rstrip("\n") + "\n")
    sys.stderr.write(_USAGE)
    return schema.USAGE_EXIT


def _parse_args(argv):
    """Minimal deterministic arg parser (no argparse help-to-stderr
    surprises). Returns (subcommand, options dict) or raises ValueError
    for adapter CLI misuse."""
    if not argv:
        raise ValueError("no subcommand")
    sub = argv[0]
    if sub not in ("verdict", "compare"):
        raise ValueError("unknown subcommand: %r" % (sub,))
    opts = {"timeout": DEFAULT_TIMEOUT_SECONDS}
    i = 1
    flags = {
        "--lane": "lane", "--input": "input", "--reason-map": "reason_map",
        "--python-bin": "python_bin", "--python-entry": "python_entry",
        "--rust-bin": "rust_bin", "--timeout": "timeout",
        "--case-id": "case_id", "--comparison-contract": "comparison_contract",
    }
    while i < len(argv):
        flag = argv[i]
        if flag not in flags:
            raise ValueError("unknown argument: %r" % (flag,))
        if i + 1 >= len(argv):
            raise ValueError("missing value for %s" % flag)
        value = argv[i + 1]
        if flag == "--timeout":
            try:
                value = int(value)
            except ValueError:
                raise ValueError("--timeout must be an integer")
                
            if value <= 0:
                raise ValueError("--timeout must be positive")
        opts[flags[flag]] = value
        i += 2
    return sub, opts


def _do_verdict(opts):
    lane = opts.get("lane")
    if lane not in schema.LANES:
        raise ValueError("--lane must be one of %s" % (schema.LANES,))
    reason_map_path = opts.get("reason_map")
    input_path = opts.get("input")
    if input_path is None:
        raise ValueError("missing required path: --input")
    if not os.path.isabs(input_path):
        raise ValueError("--input must be an absolute path")
    if not os.path.exists(input_path):
        raise ValueError("--input does not exist")
    # Repair 6: validate the input TYPE honestly for the selected lane.
    if lane in (schema.LANE_PYTHON, schema.LANE_RUST):
        if not os.path.isdir(input_path):
            raise ValueError(
                "--input must be an existing directory for lane %s" % lane)
    else:  # archive
        if not os.path.isfile(input_path):
            raise ValueError(
                "--input must be an existing regular file for lane archive")
        if not os.access(input_path, os.R_OK):
            raise ValueError("--input archive file is not readable")
    reason_map = load_reason_map(reason_map_path)
    timeout = opts["timeout"]
    try:
        if lane == schema.LANE_PYTHON:
            python_bin = opts.get("python_bin")
            python_entry = opts.get("python_entry")
            _require_abs_executable(python_bin, "--python-bin")
            _require_abs_readable_file(python_entry, "--python-entry")
            version = resolve_python_verifier_version(python_entry)
            rec = evaluate_python_bundle(
                python_bin, python_entry, input_path, reason_map, timeout,
                version)
        elif lane == schema.LANE_RUST:
            rust_bin = opts.get("rust_bin")
            _require_abs_executable(rust_bin, "--rust-bin")
            rec = evaluate_rust_bundle(rust_bin, input_path, reason_map,
                                       timeout)
        else:  # archive
            rust_bin = opts.get("rust_bin")
            _require_abs_executable(rust_bin, "--rust-bin")
            rec = evaluate_archive(rust_bin, input_path, reason_map,
                                   timeout)
    except AdapterMeasurementError as exc:
        op = (schema.OP_VERIFY_BUNDLE if lane != schema.LANE_ARCHIVE
              else schema.OP_INSPECT_ARCHIVE)
        itype = (schema.INPUT_BUNDLE_DIR if lane != schema.LANE_ARCHIVE
                 else schema.INPUT_ARCHIVE_ZIP)
        rec = measurement_error_record(
            exc.code, lane=lane, operation=op, input_type=itype,
            exit_code=exc.exit_code, detail=exc.detail)
        emit(rec)
        return schema.MEASUREMENT_ERROR_EXIT
    emit(rec)
    return schema.VERDICT_EXIT[rec["verdict"]]


class ComparisonContractInvalid(Exception):
    """The supplied frozen comparison contract is structurally invalid.
    Raised deterministically -- never a raw traceback."""


def _expected_lane_shape_ok(obj, lane):
    """An expected lane record must carry verdict, reason_class, stage and
    exit_code with correct types, allowed values, a valid adopted
    (verdict, exit_code) pairing for that lane, and a verdict the lane can
    currently reach. Usage exit 2 is never a verdict expectation."""
    if not isinstance(obj, dict):
        return False
    verdict = obj.get("verdict")
    reason_class = obj.get("reason_class")
    stage = obj.get("stage")
    exit_code = obj.get("exit_code")
    if verdict not in schema.VERDICTS:
        return False
    if not isinstance(reason_class, str) or reason_class.strip() == "":
        return False
    if not isinstance(stage, str) or stage.strip() == "":
        return False
    # bool is a subclass of int; require a real int, not a bool
    if isinstance(exit_code, bool) or not isinstance(exit_code, int):
        return False
    # usage exit 2 is an invocation failure, never a verification verdict
    if exit_code == 2:
        return False
    # the verdict must be currently reachable by THIS lane
    if verdict not in schema.LANE_REACHABLE_VERDICTS[lane]:
        return False
    # and the (verdict, exit_code) pairing must be the adopted one
    allowed = schema.LANE_VERDICT_EXIT[lane]
    if verdict not in allowed or allowed[verdict] != exit_code:
        return False
    return True


def _is_safe_case_token(value):
    """A case_id must be a nonempty, non-whitespace-only safe token."""
    if not isinstance(value, str):
        return False
    if value.strip() == "":
        return False
    for ch in value:
        if not (ch.isalnum() or ch in "_-."):
            return False
    return True


def load_comparison_contract(contract_path, expected_lane):
    """Load and COMPLETELY validate the frozen comparison authority.

    Structural: top-level object; corpus lane identifier (so a bundle
    comparison cannot silently use the archive corpus); cases is a list;
    every case an object; unique safe nonempty case_id; per-case lane
    matches the corpus; valid category; valid scopes; expected is an
    object.

    Semantic: category/scope consistency; a well-formed expected record for
    every in-scope lane (correct types, adopted verdict/exit pairing, no
    exit 2, only lane-reachable verdicts); a present and valid
    normalized_outcome consistent with every in-scope lane's verdict under
    the adopted agreement semantics; for KNOWN_DIVERGENCE_CASE a present
    expected_divergence whose class/stage values exactly match the expected
    lane records; and for SINGLE_IMPLEMENTATION_CASE a well-formed
    out-of-scope observed record when one is present.

    Returns a dict case_id -> case. Raises ComparisonContractInvalid
    deterministically on any failure -- never a raw traceback."""
    _require_abs_readable_file(contract_path, "--comparison-contract")
    try:
        with open(contract_path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (ValueError, OSError):
        raise ComparisonContractInvalid("contract is not readable JSON")
    if not isinstance(data, dict):
        raise ComparisonContractInvalid("contract is not a JSON object")
    if data.get("lane") != expected_lane:
        raise ComparisonContractInvalid(
            "contract corpus lane is not the expected corpus")
    cases = data.get("cases")
    if not isinstance(cases, list):
        raise ComparisonContractInvalid("contract 'cases' is not a list")
    by_id = {}
    for case in cases:
        if not isinstance(case, dict):
            raise ComparisonContractInvalid("a case is not an object")
        cid = case.get("case_id")
        if not _is_safe_case_token(cid):
            raise ComparisonContractInvalid("a case has no valid case_id")
        if cid in by_id:
            raise ComparisonContractInvalid("duplicate case_id")
        # the per-case lane must match the corpus lane
        if case.get("lane") != expected_lane:
            raise ComparisonContractInvalid("case lane is not the corpus lane")
        category = case.get("category")
        if category not in schema.CONTRACT_CATEGORIES:
            raise ComparisonContractInvalid("invalid case category")
        scopes = {}
        for lane in (schema.LANE_PYTHON, schema.LANE_RUST):
            scope = case.get(schema.CONTRACT_SCOPE_KEY[lane])
            if scope not in schema.CONTRACT_SCOPES:
                raise ComparisonContractInvalid("invalid lane scope")
            scopes[lane] = scope
        in_scope_lanes = [lane for lane in scopes
                          if scopes[lane] == schema.SCOPE_IN]
        if category in (schema.CATEGORY_AGREEMENT,
                        schema.CATEGORY_KNOWN_DIVERGENCE):
            if len(in_scope_lanes) != 2:
                raise ComparisonContractInvalid(
                    "agreement/known-divergence case without both lanes in scope")
        else:  # SINGLE_IMPLEMENTATION_CASE
            if len(in_scope_lanes) != 1:
                raise ComparisonContractInvalid(
                    "single-implementation case without exactly one lane in scope")
        expected = case.get("expected")
        if not isinstance(expected, dict):
            raise ComparisonContractInvalid("case 'expected' is not an object")
        outcome = expected.get("normalized_outcome")
        if outcome not in schema.NORMALIZED_OUTCOMES:
            raise ComparisonContractInvalid("invalid normalized_outcome")
        # every IN-SCOPE lane needs a valid expected record whose verdict
        # normalizes to the declared outcome (adopted agreement semantics)
        for lane in in_scope_lanes:
            rec = expected.get(schema.CONTRACT_LANE_KEY[lane])
            if not _expected_lane_shape_ok(rec, lane):
                raise ComparisonContractInvalid(
                    "malformed expected lane record")
            if schema.VERDICT_TO_OUTCOME[rec["verdict"]] != outcome:
                raise ComparisonContractInvalid(
                    "expected lane verdict inconsistent with normalized_outcome")
        # out-of-scope observed metadata, when present, must be well formed
        for lane in (schema.LANE_PYTHON, schema.LANE_RUST):
            if scopes[lane] == schema.SCOPE_IN:
                continue
            observed = expected.get(schema.CONTRACT_OBSERVED_KEY[lane])
            if observed is None:
                continue
            if not _expected_lane_shape_ok(observed, lane):
                raise ComparisonContractInvalid(
                    "malformed out-of-scope observed record")
        # known-divergence metadata must be present and exactly consistent
        if category == schema.CATEGORY_KNOWN_DIVERGENCE:
            div = case.get("expected_divergence")
            if not isinstance(div, dict):
                raise ComparisonContractInvalid(
                    "known-divergence case without expected_divergence")
            py_rec = expected[schema.CONTRACT_LANE_KEY[schema.LANE_PYTHON]]
            rust_rec = expected[schema.CONTRACT_LANE_KEY[schema.LANE_RUST]]
            if div.get("python_class") != py_rec["reason_class"] \
                    or div.get("python_stage") != py_rec["stage"] \
                    or div.get("rust_class") != rust_rec["reason_class"] \
                    or div.get("rust_stage") != rust_rec["stage"]:
                raise ComparisonContractInvalid(
                    "expected_divergence inconsistent with expected lanes")
            # A DIVERGENCE must actually diverge: at least one of the
            # reason class or the decisive stage must differ between the
            # lanes. Identical class AND stage is agreement, not
            # divergence, however self-consistent the metadata looks.
            if py_rec["reason_class"] == rust_rec["reason_class"] \
                    and py_rec["stage"] == rust_rec["stage"]:
                raise ComparisonContractInvalid(
                    "known-divergence case whose lanes do not diverge")
            # Preserve the adopted frozen-corpus rule: the declared known
            # divergences are REJECTED outcomes. An "accepted divergence"
            # is not something Move 81 may invent.
            if outcome != schema.OUTCOME_REJECTED:
                raise ComparisonContractInvalid(
                    "known-divergence case is not a rejected outcome")
        elif category == schema.CATEGORY_AGREEMENT:
            if "expected_divergence" in case:
                raise ComparisonContractInvalid(
                    "non-divergence case carries expected_divergence")
            # An AGREEMENT_CASE must agree on BOTH the normalized reason
            # class and the decisive stage. Differing class or stage is a
            # divergence and must not be declared as agreement.
            py_rec = expected[schema.CONTRACT_LANE_KEY[schema.LANE_PYTHON]]
            rust_rec = expected[schema.CONTRACT_LANE_KEY[schema.LANE_RUST]]
            if py_rec["reason_class"] != rust_rec["reason_class"]:
                raise ComparisonContractInvalid(
                    "agreement case with differing reason classes")
            if py_rec["stage"] != rust_rec["stage"]:
                raise ComparisonContractInvalid(
                    "agreement case with differing stages")
            # both lanes already validated as consistent with the single
            # declared normalized_outcome above, so their outcomes match
        else:
            # a single-implementation case must not carry divergence data
            if "expected_divergence" in case:
                raise ComparisonContractInvalid(
                    "non-divergence case carries expected_divergence")
        by_id[cid] = case
    if not by_id:
        raise ComparisonContractInvalid("contract declares no cases")
    return by_id


def _expected_lane(case, lane_key, scope_key):
    """Return (expected_dict_or_None, in_scope_bool) for a lane from a
    frozen case. Out-of-scope lanes may store the observed values under
    '<lane>_observed'; in-scope lanes under '<lane>'."""
    scope = case.get(scope_key)
    in_scope = scope == "in_scope"
    expected = case["expected"]
    if lane_key in expected:
        return expected[lane_key], in_scope
    observed_key = lane_key + "_observed"
    if observed_key in expected:
        return expected[observed_key], in_scope
    return None, in_scope


def _lane_matches_expected(lane_record, expected):
    """True iff a completed verdict record exactly matches the adopted
    expected verdict, reason class, stage and exit code."""
    if lane_record.get("record_type") != schema.RECORD_VERDICT:
        return False
    if expected is None:
        return False
    return (lane_record.get("verdict") == expected.get("verdict")
            and lane_record.get("reason_code") == expected.get("reason_class")
            and lane_record.get("stage") == expected.get("stage")
            and lane_record.get("exit_code") == expected.get("exit_code"))


def _do_compare(opts):
    input_path = opts.get("input")
    reason_map_path = opts.get("reason_map")
    python_bin = opts.get("python_bin")
    python_entry = opts.get("python_entry")
    rust_bin = opts.get("rust_bin")
    case_id = opts.get("case_id")
    contract_path = opts.get("comparison_contract")
    if input_path is None or not os.path.isabs(input_path):
        raise ValueError("--input must be an absolute path")
    if not os.path.isdir(input_path):
        raise ValueError("--input must be an existing directory")
    if case_id is None:
        raise ValueError("--case-id is required for compare")
    if contract_path is None:
        raise ValueError("--comparison-contract is required for compare")
    _require_abs_executable(python_bin, "--python-bin")
    _require_abs_readable_file(python_entry, "--python-entry")
    _require_abs_executable(rust_bin, "--rust-bin")
    reason_map = load_reason_map(reason_map_path)
    timeout = opts["timeout"]

    # Frozen comparison authority. An invalid contract or an unknown case
    # id is an adapter-layer measurement error about the COMPARE operation
    # itself -- emitted as one top-level measurement_error record, never as
    # a comparison record with both lanes null. The input directory has
    # already been validated above, so its type IS honestly established
    # and is preserved on the record.
    try:
        contract = load_comparison_contract(
            contract_path, schema.CONTRACT_BUNDLE_LANE)
    except ComparisonContractInvalid:
        emit(measurement_error_record(
            schema.ERR_COMPARISON_CONTRACT_INVALID,
            operation=schema.OP_COMPARE,
            input_type=schema.INPUT_BUNDLE_DIR))
        return schema.MEASUREMENT_ERROR_EXIT
    if case_id not in contract:
        emit(measurement_error_record(
            schema.ERR_UNKNOWN_CASE_ID, operation=schema.OP_COMPARE,
            input_type=schema.INPUT_BUNDLE_DIR))
        return schema.MEASUREMENT_ERROR_EXIT
    case = contract[case_id]

    py_expected, py_in_scope = _expected_lane(case, "python", "python_scope")
    rust_expected, rust_in_scope = _expected_lane(case, "rust", "rust_scope")

    # Run each in-scope lane; out-of-scope lanes are not applicable.
    py_version = resolve_python_verifier_version(python_entry)
    if py_in_scope:
        python_lane = _lane_or_error(
            lambda: evaluate_python_bundle(
                python_bin, python_entry, input_path, reason_map, timeout,
                py_version),
            schema.LANE_PYTHON, schema.OP_VERIFY_BUNDLE,
            schema.INPUT_BUNDLE_DIR)
    else:
        python_lane = None
    if rust_in_scope:
        rust_lane = _lane_or_error(
            lambda: evaluate_rust_bundle(
                rust_bin, input_path, reason_map, timeout),
            schema.LANE_RUST, schema.OP_VERIFY_BUNDLE,
            schema.INPUT_BUNDLE_DIR)
    else:
        rust_lane = None

    status = _authoritative_comparison_status(
        case, python_lane, rust_lane, py_expected, rust_expected,
        py_in_scope, rust_in_scope)

    rec = schema.envelope(schema.RECORD_COMPARISON)
    rec["case_id"] = case_id
    rec["python_lane"] = python_lane
    rec["rust_lane"] = rust_lane
    rec["comparison_status"] = status
    emit(rec)
    return schema.COMPARISON_EXIT[status]


def _authoritative_comparison_status(case, python_lane, rust_lane,
                                     py_expected, rust_expected,
                                     py_in_scope, rust_in_scope):
    """Derive the comparison status from the frozen case contract and the
    actual lane records. Never labels PASS/FAIL/INCONCLUSIVE."""
    # measurement error on any ATTEMPTED (in-scope) lane
    if py_in_scope and python_lane is not None \
            and python_lane.get("record_type") == schema.RECORD_MEASUREMENT_ERROR:
        return schema.CMP_MEASUREMENT_ERROR
    if rust_in_scope and rust_lane is not None \
            and rust_lane.get("record_type") == schema.RECORD_MEASUREMENT_ERROR:
        return schema.CMP_MEASUREMENT_ERROR

    category = case.get("category")

    # SINGLE_IMPLEMENTATION_CASE: exactly one lane is out of scope. The
    # in-scope lane must match its adopted expected outcome; the
    # out-of-scope lane is genuinely not applicable.
    if not py_in_scope or not rust_in_scope:
        if not py_in_scope and not rust_in_scope:
            return schema.CMP_UNEXPECTED_DIVERGENCE
        if py_in_scope:
            ok = _lane_matches_expected(python_lane, py_expected)
        else:
            ok = _lane_matches_expected(rust_lane, rust_expected)
        return (schema.CMP_LANE_NOT_APPLICABLE if ok
                else schema.CMP_UNEXPECTED_DIVERGENCE)

    # both lanes in scope: both must match their adopted expected outcomes
    both_match = (_lane_matches_expected(python_lane, py_expected)
                  and _lane_matches_expected(rust_lane, rust_expected))
    if not both_match:
        return schema.CMP_UNEXPECTED_DIVERGENCE
    if category == "KNOWN_DIVERGENCE_CASE":
        return schema.CMP_DECLARED_DIVERGENCE
    if category == "AGREEMENT_CASE":
        return schema.CMP_AGREEMENT
    # any other category with both lanes in scope is not a declared
    # agreement or divergence -> unexpected
    return schema.CMP_UNEXPECTED_DIVERGENCE


def _lane_or_error(thunk, lane, operation, input_type):
    try:
        return thunk()
    except AdapterMeasurementError as exc:
        return measurement_error_record(
            exc.code, lane=lane, operation=operation,
            input_type=input_type, exit_code=exc.exit_code,
            detail=exc.detail)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    try:
        sub, opts = _parse_args(argv)
    except ValueError as exc:
        return _usage_error(str(exc))
    try:
        if sub == "verdict":
            return _do_verdict(opts)
        return _do_compare(opts)
    except ValueError as exc:
        # adapter CLI misuse (bad/missing paths) -> usage exit, no record
        return _usage_error(str(exc))


if __name__ == "__main__":
    sys.exit(main())
