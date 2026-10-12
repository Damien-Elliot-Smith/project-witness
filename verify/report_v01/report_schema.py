#!/usr/bin/env python3
"""Move 83 — `witness-report/1` validator.

This module VALIDATES reports produced by the Rust verifier's new
`report-bundle` / `report-archive` invocations. It does not generate them
and it does not reimplement the verifier: the producer is the adopted
binary, and this checker's job is to refuse anything that misrepresents
what the verifier actually did.

Two properties matter most and both are enforced here:

* **Execution honesty.** A check recorded as `NOT_RUN` must carry a reason
  and must have no `reason_code`. A `NOT_RUN` check may never be followed
  by an executed one, because the adopted verifier short-circuits: once it
  stops, everything after it is unreachable. A report claiming otherwise
  would be describing an evaluation that did not happen.
* **Canonical bytes.** Semantic comparison would admit non-canonical
  formatting, so the raw bytes are compared against the canonical
  re-serialisation.
"""

import argparse
import json
import os
import stat
import sys

SCHEMA_VERSION = "witness-report/1"
RECORD_TYPE_CORE = "verification_report_core"
RECORD_TYPE = "verification_report"
PRODUCER = "witness-verify-report"
PRODUCER_VERSION = "0.0.1-step83-report"
VERIFIER = "witness-verify"
VERIFIER_VERSION = "0.0.8-step79-diagnostics"

STATUS_PASSED = "PASSED"
STATUS_FAILED = "FAILED"
STATUS_NOT_RUN = "NOT_RUN"
STATUSES = (STATUS_PASSED, STATUS_FAILED, STATUS_NOT_RUN)

# The adopted verdicts the Rust verifier can actually reach. PASS is
# deliberately absent: no Rust PASS path exists.
REACHABLE_VERDICTS = ("FAIL", "INCONCLUSIVE")
VERDICT_EXIT = {"FAIL": 1, "INCONCLUSIVE": 3}

OPERATIONS = {
    "verify_bundle": "bundle_dir",
    "inspect_archive": "archive_zip",
}

BUNDLE_CHECKS = (
    "bundle_path_exists",
    "bundle_path_is_directory",
    "manifest_structure",
    "declared_top_level_hashes",
    "receipt_chain",
    "nested_integrity",
)
# The adopted evaluate_archive performs exactly one check. v01 invented an
# archive_path_readable check and then reported a second executed result
# after evaluation had stopped; both are gone.
ARCHIVE_CHECKS = ("archive_safety",)

CORE_FIELDS = frozenset((
    "checks", "exit_code", "final_reason_code", "final_verdict",
    "input_digest", "input_type", "limitations", "operation", "producer",
    "producer_version", "record_type", "schema_version", "verifier",
    "verifier_version",
))
# The classified record adds exactly two fields, both looked up from the
# ADOPTED reason_map.json authority. Nothing restates those mappings.
CLASSIFIED_FIELDS = CORE_FIELDS | frozenset(
    ("final_reason_class", "final_stage"))

DIGEST_MEASURED = "MEASURED"
DIGEST_UNMEASURABLE = "UNMEASURABLE"
DIGEST_STATES = (DIGEST_MEASURED, DIGEST_UNMEASURABLE)
CHECK_FIELDS = frozenset(
    ("name", "not_run_reason", "observed", "reason_code", "status"))
DIGEST_FIELDS = frozenset(
    ("algorithm", "file_count", "non_regular_entry_count", "scope",
     "state", "value"))

# Fields that would make this a Move 81 verdict record or a Move 82
# provenance record rather than a report.
FORBIDDEN_FIELDS = (
    "capability_scope", "implementation_lane", "stage", "detail",
    "binary_sha256", "build_argv", "target_triple", "transcript_name",
)


class ReportError(Exception):
    """Deterministic, message-only validation failure."""


def _is_hex64(value):
    return (isinstance(value, str) and len(value) == 64
            and all(c in "0123456789abcdef" for c in value))


def canonical_bytes(record):
    return (json.dumps(record, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False) + "\n").encode("utf-8")


def check_canonical_bytes(raw):
    """The bytes themselves must be canonical: one object, one trailing
    newline, sorted keys, compact separators, no duplicate keys."""
    problems = []
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return ["report is not UTF-8"], None
    if text == "":
        return ["report is empty"], None
    if not text.endswith("\n"):
        problems.append("report has no trailing newline")
    if text.endswith("\n\n"):
        problems.append("report has more than one trailing newline")
    if text.count("\n") != 1:
        problems.append("report is not exactly one line")
    body = text[:-1] if text.endswith("\n") else text
    if body != body.strip():
        problems.append("report has leading or trailing whitespace")

    seen = []

    def _pairs(pairs):
        seen.append([k for k, _v in pairs])
        return dict(pairs)

    try:
        record = json.loads(body, object_pairs_hook=_pairs)
    except ValueError:
        problems.append("report is not valid JSON")
        return problems, None
    for keys in seen:
        if len(keys) != len(set(keys)):
            problems.append("report contains duplicate keys")
            break
    if not isinstance(record, dict):
        problems.append("report is not a JSON object")
        return problems, None
    if text != canonical_bytes(record).decode("utf-8"):
        problems.append(
            "report is not canonical JSON bytes (key order, separators or "
            "spacing differ from the canonical form)")
    return problems, record


def validate_record(record, classified=False):
    """Validate a parsed report. `classified` requires the two fields the
    adopted reason-map authority supplies."""
    problems = []
    if not isinstance(record, dict):
        return ["report is not an object"]

    allowed = CLASSIFIED_FIELDS if classified else CORE_FIELDS
    want_type = RECORD_TYPE if classified else RECORD_TYPE_CORE
    present = set(record)
    missing = sorted(allowed - present)
    if missing:
        problems.append("missing field(s): %s" % ", ".join(missing))
    extra = sorted(present - allowed)
    if extra:
        problems.append("unexpected field(s): %s" % ", ".join(extra))
    if record.get("record_type") != want_type:
        problems.append("record_type is %r, expected %r"
                        % (record.get("record_type"), want_type))
    if classified:
        for field in ("final_reason_class", "final_stage"):
            value = record.get(field)
            if not isinstance(value, str) or not value.strip():
                problems.append("%s must be a non-empty string" % field)
    for field in FORBIDDEN_FIELDS:
        if field in record:
            problems.append(
                "field %s belongs to another adopted schema, not to a "
                "report" % field)

    for field, want in (("schema_version", SCHEMA_VERSION),
                        ("producer", PRODUCER),
                        ("producer_version", PRODUCER_VERSION),
                        ("verifier", VERIFIER),
                        ("verifier_version", VERIFIER_VERSION)):
        if record.get(field) != want:
            problems.append("%s is %r, the adopted value is %r"
                            % (field, record.get(field), want))

    operation = record.get("operation")
    if operation not in OPERATIONS:
        problems.append("operation is %r, not an adopted operation"
                        % operation)
    elif record.get("input_type") != OPERATIONS[operation]:
        problems.append("input_type %r does not match operation %r"
                        % (record.get("input_type"), operation))

    verdict = record.get("final_verdict")
    if verdict == "PASS":
        problems.append(
            "final_verdict is PASS; the Rust verifier has no PASS path")
    elif verdict not in REACHABLE_VERDICTS:
        problems.append("final_verdict is %r, not a reachable verdict"
                        % verdict)
    exit_code = record.get("exit_code")
    if verdict in VERDICT_EXIT and exit_code != VERDICT_EXIT[verdict]:
        problems.append("exit_code %r does not match verdict %r"
                        % (exit_code, verdict))

    reason = record.get("final_reason_code")
    if not isinstance(reason, str) or reason.strip() == "":
        problems.append("final_reason_code must be a non-empty string")

    problems.extend(_validate_digest(record.get("input_digest"), operation))
    problems.extend(_validate_checks(record.get("checks"), operation,
                                     verdict, reason))

    limitations = record.get("limitations")
    if not isinstance(limitations, list) or not limitations:
        problems.append("limitations must be a non-empty array")
    elif not all(isinstance(x, str) and x.strip() for x in limitations):
        problems.append("limitations entries must be non-empty strings")
    else:
        joined = " ".join(limitations).lower()
        if "not_run" not in joined:
            problems.append(
                "limitations must state that a NOT_RUN check has no result")
        if "pass" not in joined:
            problems.append(
                "limitations must state that no PASS verdict is emitted")
    return problems


def _validate_digest(digest, operation):
    problems = []
    if not isinstance(digest, dict):
        return ["input_digest must be an object"]
    present = set(digest)
    missing = sorted(DIGEST_FIELDS - present)
    if missing:
        problems.append("input_digest missing %s" % ", ".join(missing))
    extra = sorted(present - DIGEST_FIELDS)
    if extra:
        problems.append("input_digest has unexpected %s" % ", ".join(extra))
    if digest.get("algorithm") != "sha256":
        problems.append("input_digest algorithm must be sha256")
    state = digest.get("state")
    if state not in DIGEST_STATES:
        problems.append("input_digest state must be one of %s"
                        % ", ".join(DIGEST_STATES))
    value = digest.get("value")
    if value is not None and not _is_hex64(value):
        problems.append("input_digest value must be null or a 64-char "
                        "lowercase hex digest")
    # the state and the measurement must not contradict each other
    if state == DIGEST_MEASURED:
        if value is None:
            problems.append(
                "input_digest state is MEASURED but no value is present")
        if operation == "verify_bundle" \
                and digest.get("file_count") is None:
            problems.append(
                "input_digest state is MEASURED but file_count is null")
    elif state == DIGEST_UNMEASURABLE:
        if value is not None:
            problems.append(
                "input_digest state is UNMEASURABLE but carries a value")
        for field in ("file_count", "non_regular_entry_count"):
            if digest.get(field) is not None:
                problems.append(
                    "input_digest state is UNMEASURABLE but carries %s"
                    % field)
    scope = digest.get("scope")
    if not isinstance(scope, str) or len(scope.strip()) < 40:
        problems.append(
            "input_digest scope must explicitly describe what is covered")
    elif operation == "verify_bundle" and ("regular file" not in scope
                                           or "mode bits" not in scope):
        problems.append(
            "a bundle digest must state which files it covers; a partial "
            "digest must never be described as covering the whole bundle")
    for field in ("file_count", "non_regular_entry_count"):
        count = digest.get(field)
        if count is None:
            continue
        if isinstance(count, bool) or not isinstance(count, int) \
                or count < 0:
            problems.append("input_digest %s must be null or a "
                            "non-negative integer" % field)
    if operation == "inspect_archive":
        if digest.get("file_count") is not None:
            problems.append(
                "an archive digest covers the file bytes, so file_count "
                "must be null")
    return problems


def _validate_checks(checks, operation, verdict, final_reason):
    problems = []
    if not isinstance(checks, list) or not checks:
        return ["checks must be a non-empty array"]

    expected = (BUNDLE_CHECKS if operation == "verify_bundle"
                else ARCHIVE_CHECKS)
    names = []
    for entry in checks:
        if not isinstance(entry, dict):
            problems.append("each check must be an object")
            return problems
        present = set(entry)
        missing = sorted(CHECK_FIELDS - present)
        if missing:
            problems.append("check missing %s" % ", ".join(missing))
        extra = sorted(present - CHECK_FIELDS)
        if extra:
            problems.append("check has unexpected %s" % ", ".join(extra))
        names.append(entry.get("name"))

        status = entry.get("status")
        if status not in STATUSES:
            problems.append("check %r has invalid status %r"
                            % (entry.get("name"), status))
            continue
        reason = entry.get("reason_code")
        not_run_reason = entry.get("not_run_reason")

        if status == STATUS_NOT_RUN:
            # EXECUTION HONESTY: a check that never ran has no result.
            if reason is not None:
                problems.append(
                    "check %r is NOT_RUN but carries a reason_code; a check "
                    "that never ran has no result" % entry.get("name"))
            if not isinstance(not_run_reason, str) \
                    or not not_run_reason.strip():
                problems.append(
                    "check %r is NOT_RUN without an explicit reason"
                    % entry.get("name"))
            if entry.get("observed") is not None:
                problems.append(
                    "check %r is NOT_RUN but reports an observation"
                    % entry.get("name"))
        else:
            if not_run_reason is not None:
                problems.append(
                    "check %r executed but carries a not_run_reason"
                    % entry.get("name"))
            if status == STATUS_FAILED:
                if not isinstance(reason, str) or not reason.strip():
                    problems.append(
                        "check %r FAILED without a reason_code"
                        % entry.get("name"))
            elif reason is not None:
                problems.append(
                    "check %r PASSED but carries a reason_code"
                    % entry.get("name"))

    if names != list(expected):
        problems.append(
            "checks must list exactly the adopted %s sequence in order: "
            "got %r" % (operation, names))

    statuses = [c.get("status") for c in checks
                if isinstance(c, dict)]
    # The adopted verifier short-circuits, so nothing executes after a
    # NOT_RUN, and nothing executes after a FAILED.
    seen_stop = False
    for name, status in zip(names, statuses):
        if seen_stop and status != STATUS_NOT_RUN:
            problems.append(
                "check %r reports status %r after evaluation had already "
                "stopped; the adopted verifier cannot continue past a "
                "failing check" % (name, status))
        if status in (STATUS_FAILED, STATUS_NOT_RUN):
            seen_stop = True

    failed = [c for c in checks
              if isinstance(c, dict) and c.get("status") == STATUS_FAILED]
    if verdict == "FAIL":
        if len(failed) != 1:
            problems.append(
                "a FAIL report must record exactly one FAILED check, got %d"
                % len(failed))
        elif failed[0].get("reason_code") != final_reason:
            problems.append(
                "final_reason_code %r does not match the failing check's "
                "reason_code %r" % (final_reason,
                                    failed[0].get("reason_code")))
    else:
        if failed:
            problems.append(
                "a non-FAIL report must record no FAILED check")
        if any(s == STATUS_NOT_RUN for s in statuses):
            problems.append(
                "a non-FAIL report cannot contain a NOT_RUN check: "
                "evaluation ran to completion")
    return problems


def classify(record, reason_map_bytes):
    """Add final_reason_class and final_stage by LOOKING THEM UP in the
    adopted reason_map.json bytes. No mapping is restated here."""
    try:
        reason_map = json.loads(reason_map_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise ReportError("reason map is not readable JSON")
    lane = ("archive" if record.get("operation") == "inspect_archive"
            else "rust_bundle")
    entries = reason_map.get(lane)
    if not isinstance(entries, list) or not entries:
        raise ReportError("reason map has no %s lane" % lane)
    raw_reason = record.get("final_reason_code")
    found = None
    for entry in entries:
        if entry.get("match_type") == "exact" \
                and entry.get("value") == raw_reason:
            found = entry
            break
    if found is None:
        import re as _re
        for entry in entries:
            if entry.get("match_type") == "regex":
                try:
                    if _re.search(entry["value"], raw_reason or ""):
                        found = entry
                        break
                except _re.error:
                    continue
    if found is None:
        raise ReportError(
            "reason %r is not present in the adopted reason map for lane "
            "%s" % (raw_reason, lane))
    completed = dict(record)
    completed["record_type"] = RECORD_TYPE
    completed["final_reason_class"] = found.get("class")
    completed["final_stage"] = found.get("stage")
    return completed


def validate_bytes(raw, classified=False):
    """Full validation from raw bytes. Returns (problems, record)."""
    problems, record = check_canonical_bytes(raw)
    if record is None:
        return problems, None
    problems = list(problems) + validate_record(record, classified)
    return problems, record


def cross_check_legacy(record, legacy_stdout, legacy_exit):
    """The report must agree with the ADOPTED legacy verdict line for the
    same input. The legacy line is the authority; the report describes the
    same evaluation and may never contradict it."""
    problems = []
    try:
        legacy = json.loads(legacy_stdout.decode("utf-8").strip())
    except (ValueError, UnicodeDecodeError):
        return ["legacy verdict line is not readable JSON"]
    if record.get("final_verdict") != legacy.get("verdict"):
        problems.append(
            "report verdict %r contradicts the legacy verdict %r"
            % (record.get("final_verdict"), legacy.get("verdict")))
    if record.get("final_reason_code") != legacy.get("reason_code"):
        problems.append(
            "report reason %r contradicts the legacy reason %r"
            % (record.get("final_reason_code"), legacy.get("reason_code")))
    if record.get("exit_code") != legacy_exit:
        problems.append(
            "report exit_code %r contradicts the legacy exit %r"
            % (record.get("exit_code"), legacy_exit))
    if record.get("verifier_version") != legacy.get("version"):
        problems.append(
            "report verifier_version %r contradicts the legacy version %r"
            % (record.get("verifier_version"), legacy.get("version")))
    return problems


# ----------------------------------------------------------------------
# Differential digest fixtures.
#
# The digest contract claims the digest binds exact path, ACTUAL mode bits
# and content. Proving that requires running the real binary over trees
# that differ in exactly one of those, so this builder constructs the
# trees and records what must differ. The gate runs the compiled binary
# over them; a Python model of the serialization is supplementary only and
# is never the production authority.
# ----------------------------------------------------------------------

DIGEST_CASES = (
    # (case_id, relative path, content, mode A, mode B, must differ)
    ("mode_0644_vs_0755", "payload.txt", b"same bytes\n", 0o644, 0o755,
     True),
    ("mode_0600_vs_0644", "payload.txt", b"same bytes\n", 0o600, 0o644,
     True),
    ("mode_empty_file", "empty.bin", b"", 0o644, 0o755, True),
    ("mode_nested_path", "nested/deep/file.txt", b"nested\n", 0o644,
     0o755, True),
    ("content_differs", "payload.txt", None, 0o644, 0o644, True),
    ("identical_control", "payload.txt", b"same bytes\n", 0o644, 0o644,
     False),
)

# Structural cases. Each pair differs ONLY in tree structure -- the same
# regular files with the same bytes and modes on both sides -- so a digest
# that covered regular files alone would produce identical values.
STRUCTURE_CASES = (
    "empty_dir_added",
    "empty_dir_removed",
    "empty_dir_renamed",
    "nested_empty_dir",
    "file_vs_directory",
    "symlink_target_differs",
    "symlink_vs_file",
)

# Names exercising the raw-path-byte property. Built only where the
# platform genuinely accepts them; each is recorded with what it proves.
PATH_CASES = (
    ("path_newline", b"a\nb.txt"),
    ("path_invalid_utf8_a", b"bad\xff.txt"),
    ("path_invalid_utf8_b", b"bad\xfe.txt"),
    ("path_nested", b"deep/inner\nname.txt"),
)


def make_digest_fixtures(outdir):
    """Build paired trees differing in exactly one bound property."""
    import shutil
    os.makedirs(outdir, exist_ok=True)
    built = []
    for case_id, rel, content, mode_a, mode_b, must_differ in DIGEST_CASES:
        pair = []
        for side, mode in (("a", mode_a), ("b", mode_b)):
            root = os.path.join(outdir, "%s_%s" % (case_id, side))
            if os.path.isdir(root):
                shutil.rmtree(root)
            target = os.path.join(root, rel)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            body = content
            if body is None:
                body = b"side a\n" if side == "a" else b"side b\n"
            with open(target, "wb") as handle:
                handle.write(body)
            os.chmod(target, mode)
            # verify the ACTUAL filesystem mode before the binary runs
            actual = stat.S_IMODE(os.lstat(target).st_mode)
            if actual != mode:
                raise ReportError(
                    "could not set mode %04o on %s (got %04o)"
                    % (mode, target, actual))
            pair.append({"side": side, "root": root, "path": rel,
                         "requested_mode": mode, "actual_mode": actual,
                         "content_sha256": _sha256_bytes(body)})
        built.append({"case_id": case_id, "must_differ": must_differ,
                      "sides": pair})
    return built


NORMALISED_MODE = 0o644
NORMALISED_DIR_MODE = 0o755


def set_mode(path, mode):
    """Set a mode explicitly and VERIFY it with lstat.

    Creation defaults, the process umask, Python defaults and kernel or
    platform behaviour must never be relied on to make two entries share a
    mode. A genuine Termux run created a FIFO at 0600 and a socket at 0644
    from calls that requested the same mode, so a test claiming the pair
    differed only in type was comparing entries that also differed in mode.
    This sets the mode and refuses to continue if the filesystem did not
    take it."""
    os.chmod(path, mode)
    actual = stat.S_IMODE(os.lstat(path).st_mode)
    if actual != mode:
        raise ReportError(
            "could not normalise %s to mode %04o (filesystem reports "
            "%04o)" % (path, mode, actual))
    return actual


def make_structure_fixtures(outdir):
    """Paired trees differing ONLY in structure, not in file content."""
    import shutil
    os.makedirs(outdir, exist_ok=True)
    built = []

    def _pair(case_id):
        roots = []
        for side in ("a", "b"):
            root = os.path.join(outdir, "%s_%s" % (case_id, side))
            if os.path.isdir(root):
                shutil.rmtree(root)
            os.makedirs(root)
            set_mode(root, NORMALISED_DIR_MODE)
            target = os.path.join(root, "file.txt")
            with open(target, "wb") as handle:
                handle.write(b"identical bytes\n")
            set_mode(target, NORMALISED_MODE)
            roots.append(root)
        return roots

    def _observed(root):
        """Verified mode of the special entry, or None for a symlink,
        whose mode cannot be set portably."""
        target = os.path.join(root, "special")
        if not os.path.lexists(target):
            return None
        info = os.lstat(target)
        if stat.S_ISLNK(info.st_mode):
            return None
        return stat.S_IMODE(info.st_mode)

    def _record(case_id, roots, supported=True, note=""):
        built.append({"case_id": case_id, "must_differ": True,
                      "supported": supported, "note": note,
                      "sides": [{"side": "a", "root": roots[0],
                                 "special_mode": _observed(roots[0])},
                                {"side": "b", "root": roots[1],
                                 "special_mode": _observed(roots[1])}]})

    def _mkdir_norm(path):
        os.makedirs(path)
        set_mode(path, NORMALISED_DIR_MODE)

    a, b = _pair("empty_dir_added")
    _mkdir_norm(os.path.join(b, "empty_directory"))
    _record("empty_dir_added", (a, b),
            note="side b holds one additional empty directory")

    a, b = _pair("empty_dir_removed")
    _mkdir_norm(os.path.join(a, "empty_directory"))
    _record("empty_dir_removed", (a, b),
            note="side a holds an empty directory that side b lacks")

    a, b = _pair("empty_dir_renamed")
    _mkdir_norm(os.path.join(a, "alpha_dir"))
    _mkdir_norm(os.path.join(b, "beta_dir"))
    _record("empty_dir_renamed", (a, b),
            note="the same empty directory under two different names")

    a, b = _pair("nested_empty_dir")
    _mkdir_norm(os.path.join(a, "outer"))
    _mkdir_norm(os.path.join(a, "outer", "inner"))
    _mkdir_norm(os.path.join(b, "outer"))
    _record("nested_empty_dir", (a, b),
            note="a nested empty directory present on one side only")

    a, b = _pair("file_vs_directory")
    with open(os.path.join(a, "ambiguous"), "wb") as handle:
        handle.write(b"")
    set_mode(os.path.join(a, "ambiguous"), NORMALISED_MODE)
    os.makedirs(os.path.join(b, "ambiguous"))
    set_mode(os.path.join(b, "ambiguous"), NORMALISED_MODE)
    _record("file_vs_directory", (a, b),
            note="the same name as an empty file and as a directory")

    supported = True
    try:
        a, b = _pair("symlink_target_differs")
        os.symlink("target_one", os.path.join(a, "link"))
        os.symlink("target_two", os.path.join(b, "link"))
    except (OSError, NotImplementedError):
        supported = False
        a = b = None
    _record("symlink_target_differs", (a, b), supported,
            note="two symlinks with equal counts but different targets")

    supported = True
    try:
        a, b = _pair("symlink_vs_file")
        os.symlink("file.txt", os.path.join(a, "other"))
        with open(os.path.join(b, "other"), "wb") as handle:
            handle.write(b"")
        set_mode(os.path.join(b, "other"), NORMALISED_MODE)
    except (OSError, NotImplementedError):
        supported = False
        a = b = None
    _record("symlink_vs_file", (a, b), supported,
            note="the same name as a symlink and as a regular file")

    # ---- special entry types --------------------------------------
    # Each pair is attempted honestly. Where the environment does not
    # permit creating the entry type, the case is recorded as
    # supported=False with the reason, and NOTHING claims it was tested.
    def _special(case_id, make_a, make_b, note):
        try:
            a, b = _pair(case_id)
            make_a(a)
            make_b(b)
        except (OSError, AttributeError, NotImplementedError,
                ReportError) as exc:
            for side in ("a", "b"):
                shutil.rmtree(
                    os.path.join(outdir, "%s_%s" % (case_id, side)),
                    ignore_errors=True)
            built.append({"case_id": case_id, "must_differ": True,
                          "supported": False,
                          "unsupported_reason": "%s" % exc,
                          "note": note, "sides": []})
            return
        _record(case_id, (a, b), True, note)

    def _mkfifo(root):
        target = os.path.join(root, "special")
        # the requested mode is masked by umask, so it is set explicitly
        # afterwards and verified
        os.mkfifo(target)
        set_mode(target, NORMALISED_MODE)

    def _mksocket(root):
        import socket as _socket
        sock = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
        target = os.path.join(root, "special")
        try:
            sock.bind(target)
        finally:
            sock.close()
        set_mode(target, NORMALISED_MODE)

    def _mkfile(root):
        target = os.path.join(root, "special")
        with open(target, "wb") as handle:
            handle.write(b"")
        set_mode(target, NORMALISED_MODE)

    def _mkdir(root):
        target = os.path.join(root, "special")
        os.makedirs(target)
        # a directory is normalised to the SAME mode as the other side so
        # only the entry type differs
        set_mode(target, NORMALISED_MODE)

    def _mklink(root):
        os.symlink("file.txt", os.path.join(root, "special"))

    def _mknod(mode, major, minor):
        def _make(root):
            target = os.path.join(root, "special")
            os.mknod(target, mode, os.makedev(major, minor))
            set_mode(target, NORMALISED_MODE)
        return _make

    _special("fifo_vs_file", _mkfifo, _mkfile,
             "a FIFO and a regular file at the same path")
    _special("fifo_vs_socket", _mkfifo, _mksocket,
             "a FIFO and a socket at the same path with the same mode")
    _special("socket_vs_file", _mksocket, _mkfile,
             "a socket and a regular file at the same path")
    _special("fifo_vs_directory", _mkfifo, _mkdir,
             "a FIFO and a directory at the same path")
    _special("fifo_vs_symlink", _mkfifo, _mklink,
             "a FIFO and a symbolic link at the same path")
    import stat as _stat
    _special("chardev_rdev_differs",
             _mknod(_stat.S_IFCHR, 1, 3), _mknod(_stat.S_IFCHR, 1, 5),
             "two character devices differing only in device identity")
    _special("blockdev_vs_chardev",
             _mknod(_stat.S_IFBLK, 7, 0), _mknod(_stat.S_IFCHR, 7, 0),
             "a block and a character device with the same rdev")

    return built


def make_path_fixtures(outdir):
    """One tree per hostile name, where the platform accepts it."""
    import shutil
    os.makedirs(outdir, exist_ok=True)
    built = []
    for case_id, raw_name in PATH_CASES:
        root = os.path.join(outdir, case_id)
        if os.path.isdir(root):
            shutil.rmtree(root)
        os.makedirs(root, exist_ok=True)
        try:
            parts = raw_name.split(b"/")
            here = root.encode("utf-8", "surrogateescape")
            for part in parts[:-1]:
                here = here + b"/" + part
                os.makedirs(here, exist_ok=True)
            target = here + b"/" + parts[-1]
            with open(target, "wb") as handle:
                handle.write(b"x\n")
            os.chmod(target, 0o644)
        except (OSError, ValueError):
            shutil.rmtree(root, ignore_errors=True)
            built.append({"case_id": case_id, "supported": False,
                          "root": None})
            continue
        built.append({"case_id": case_id, "supported": True,
                      "root": root,
                      "raw_name": raw_name.decode("utf-8",
                                                  "backslashreplace")})
    return built


def _sha256_bytes(data):
    import hashlib
    return hashlib.sha256(data).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Move 83 report validator")
    parser.add_argument("--report", default=None,
                        help="absolute path to a report file")
    parser.add_argument("--make-digest-fixtures", default=None,
                        help="absolute dir to build differential digest "
                             "fixtures into")
    parser.add_argument("--make-path-fixtures", default=None,
                        help="absolute dir to build hostile-name fixtures "
                             "into")
    parser.add_argument("--fixtures-out", default=None)
    parser.add_argument("--legacy-stdout", default=None,
                        help="absolute path to the legacy verdict line for "
                             "the same input")
    parser.add_argument("--legacy-exit", type=int, default=None)
    parser.add_argument("--reason-map", default=None,
                        help="absolute path to the ADOPTED reason_map.json")
    parser.add_argument("--classify-out", default=None,
                        help="absolute path to write the classified report")
    parser.add_argument("--classified", action="store_true",
                        help="validate a classified report")
    args = parser.parse_args(argv)

    if args.make_digest_fixtures or args.make_path_fixtures:
        payload = {}
        try:
            if args.make_digest_fixtures:
                if not os.path.isabs(args.make_digest_fixtures):
                    print("usage error: --make-digest-fixtures must be "
                          "absolute")
                    return 2
                payload["digest_cases"] = make_digest_fixtures(
                    args.make_digest_fixtures)
            if args.make_digest_fixtures:
                payload["structure_cases"] = make_structure_fixtures(
                    os.path.join(args.make_digest_fixtures, "structure"))
            if args.make_path_fixtures:
                if not os.path.isabs(args.make_path_fixtures):
                    print("usage error: --make-path-fixtures must be "
                          "absolute")
                    return 2
                payload["path_cases"] = make_path_fixtures(
                    args.make_path_fixtures)
        except ReportError as exc:
            print("FIXTURES: FAIL (%s)" % exc)
            return 1
        if args.fixtures_out:
            if not os.path.isabs(args.fixtures_out):
                print("usage error: --fixtures-out must be absolute")
                return 2
            with open(args.fixtures_out, "wb") as handle:
                handle.write(canonical_bytes(payload))
        print("FIXTURES: PASS (%d digest case(s), %d structure case(s), "
              "%d path case(s))"
              % (len(payload.get("digest_cases", [])),
                 len(payload.get("structure_cases", [])),
                 len(payload.get("path_cases", []))))
        return 0

    if not args.report:
        print("usage error: --report is required")
        return 2
    if not os.path.isabs(args.report) or not os.path.isfile(args.report):
        print("usage error: --report must be an absolute regular file")
        return 2
    with open(args.report, "rb") as handle:
        raw = handle.read()
    problems, record = validate_bytes(raw, classified=args.classified)

    if record is not None and not problems and args.classify_out:
        if not args.reason_map or not os.path.isabs(args.reason_map):
            print("usage error: --classify-out needs an absolute "
                  "--reason-map")
            return 2
        if not os.path.isabs(args.classify_out):
            print("usage error: --classify-out must be absolute")
            return 2
        try:
            with open(args.reason_map, "rb") as handle:
                completed = classify(record, handle.read())
        except ReportError as exc:
            print("REPORT_PROBLEM: %s" % exc)
            print("MOVE_83_REPORT: FAIL (1 problem(s))")
            return 1
        follow = validate_record(completed, classified=True)
        if follow:
            for problem in sorted(set(follow)):
                print("REPORT_PROBLEM: %s" % problem)
            print("MOVE_83_REPORT: FAIL (%d problem(s))" % len(set(follow)))
            return 1
        with open(args.classify_out, "wb") as handle:
            handle.write(canonical_bytes(completed))
        record = completed
    if record is not None and args.legacy_stdout is not None:
        if not os.path.isabs(args.legacy_stdout):
            print("usage error: --legacy-stdout must be absolute")
            return 2
        with open(args.legacy_stdout, "rb") as handle:
            legacy = handle.read()
        if args.legacy_exit is None:
            print("usage error: --legacy-exit is required with "
                  "--legacy-stdout")
            return 2
        problems = list(problems) + cross_check_legacy(
            record, legacy, args.legacy_exit)
    for problem in sorted(set(problems)):
        print("REPORT_PROBLEM: %s" % problem)
    if problems:
        print("MOVE_83_REPORT: FAIL (%d problem(s))" % len(set(problems)))
        return 1
    print("MOVE_83_REPORT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
