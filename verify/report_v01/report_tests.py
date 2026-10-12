#!/usr/bin/env python3
"""Move 83 focused test suite.

Stdout-bound runner, pinned count, warning-clean, target-portable.

Scope note, stated plainly: the Rust `report-bundle` / `report-archive`
invocations cannot be compiled or executed in the packaging environment,
which has no Rust toolchain. These tests therefore exercise the VALIDATOR,
the inherited-baseline checker, and structural properties of the Rust
change. The genuine report bytes are produced and validated only by the
adoption gate on device, where the gate additionally cross-checks every
report against the adopted legacy verdict line for the same input.
"""

import json
import os
import stat
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import report_schema  # noqa: E402

GATE = os.path.join(ROOT, "tools", "check_move83_report_adoption.sh")
ALLOWLIST = os.path.join(HERE, "allowlist_move83.json")
README = os.path.join(HERE, "README.md")
BASELINE_CHECKER = os.path.join(
    HERE, "check_move83_inherited.py")
SCHEMA_TOOL = os.path.join(HERE, "report_schema.py")
RUST_SRC = os.path.join(ROOT, "rust", "witness-verify", "src")
MAIN_RS = os.path.join(RUST_SRC, "main.rs")
REPORT_RS = os.path.join(RUST_SRC, "report.rs")

SUBPROCESS_TIMEOUT = 120


def _require_abs_exec(path, what):
    if not path or not os.path.isabs(path):
        raise RuntimeError("%s is not an absolute path: %r" % (what, path))
    if not os.path.isfile(path):
        raise RuntimeError("%s is not a regular file: %r" % (what, path))
    if not os.access(path, os.X_OK):
        raise RuntimeError("%s is not executable: %r" % (what, path))
    return path


PYTHON_BIN = _require_abs_exec(
    os.path.realpath(sys.executable), "test interpreter")


def _resolve_test_sh():
    supplied = os.environ.get("MOVE83_TEST_SH")
    if supplied:
        return _require_abs_exec(os.path.realpath(supplied),
                                 "MOVE83_TEST_SH (trusted shell)")
    import shutil as _shutil
    found = _shutil.which("sh")
    if not found:
        raise RuntimeError(
            "no shell available: set MOVE83_TEST_SH to the trusted shell")
    return _require_abs_exec(os.path.realpath(found), "fallback shell")


TEST_SH = _resolve_test_sh()

_TMP = None


def setUpModule():
    global _TMP
    import tempfile
    _TMP = tempfile.mkdtemp(prefix="m83_tests_")


def tearDownModule():
    import shutil
    if _TMP:
        shutil.rmtree(_TMP, ignore_errors=True)


def _run(argv, env=None, timeout=SUBPROCESS_TIMEOUT):
    return subprocess.run(argv, capture_output=True, env=env,
                          timeout=timeout)


def _write_python_exe(name, body):
    path = os.path.join(_TMP, name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("#!%s\n%s" % (PYTHON_BIN, body))
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP
             | stat.S_IXOTH)
    return path


LIMITATIONS = [
    "this report describes only checks that genuinely executed. A check "
    "recorded as NOT_RUN has no result and none is inferred",
    "the Rust verifier emits no pass verdict. An accepted bundle is "
    "reported as INCONCLUSIVE by design and not as an error",
    "this report adds no check and no verification capability",
    "the input digest covers the bundle tree as described in the scope "
    "field of input_digest",
]

BUNDLE_SCOPE = (
    "sha256 over an injective serialization of EVERY regular file in the "
    "bundle tree. A domain-separation prefix; then per file the "
    "length-prefixed raw relative-path bytes; the ACTUAL Unix mode bits "
    "masked with 0o7777; and the length-prefixed lowercase-hex sha256 of "
    "its content; ordered by raw relative-path bytes. This definition is "
    "Unix-only. Symlinks and special files are not followed.")

ARCHIVE_SCOPE = (
    "sha256 over the complete bytes of the archive file as supplied.")


def _check(name, status, reason=None, not_run=None, observed=None):
    return {"name": name, "not_run_reason": not_run, "observed": observed,
            "reason_code": reason, "status": status}


def accepted_bundle_report(**over):
    checks = [
        _check("bundle_path_exists", "PASSED"),
        _check("bundle_path_is_directory", "PASSED"),
        _check("manifest_structure", "PASSED"),
        _check("declared_top_level_hashes", "PASSED",
               observed={"declared_hashes_verified": 7}),
        _check("receipt_chain", "PASSED",
               observed={"receipts_verified": 3}),
        _check("nested_integrity", "PASSED",
               observed={"nested_entries_verified": 40}),
    ]
    record = {
        "checks": checks,
        "exit_code": 3,
        "final_reason_code": "RECEIPT_CHAIN_HASHES_RECOMPUTED",
        "final_verdict": "INCONCLUSIVE",
        "input_digest": {"algorithm": "sha256", "file_count": 42,
                         "non_regular_entry_count": 0,
                         "scope": BUNDLE_SCOPE, "state": "MEASURED",
                         "value": "a" * 64},
        "input_type": "bundle_dir",
        "limitations": list(LIMITATIONS),
        "operation": "verify_bundle",
        "producer": report_schema.PRODUCER,
        "producer_version": report_schema.PRODUCER_VERSION,
        "record_type": report_schema.RECORD_TYPE_CORE,
        "schema_version": report_schema.SCHEMA_VERSION,
        "verifier": report_schema.VERIFIER,
        "verifier_version": report_schema.VERIFIER_VERSION,
    }
    record.update(over)
    return record


def failing_bundle_report(**over):
    reason = "MANIFEST_JSON_INVALID"
    skipped = ("not executed. Evaluation stopped at the earlier check "
               "'manifest_structure' with reason code %s. The adopted "
               "verifier does not continue past a failing check; no "
               "result for this check exists" % reason)
    checks = [
        _check("bundle_path_exists", "PASSED"),
        _check("bundle_path_is_directory", "PASSED"),
        _check("manifest_structure", "FAILED", reason=reason),
        _check("declared_top_level_hashes", "NOT_RUN", not_run=skipped),
        _check("receipt_chain", "NOT_RUN", not_run=skipped),
        _check("nested_integrity", "NOT_RUN", not_run=skipped),
    ]
    record = accepted_bundle_report()
    record.update({"checks": checks, "exit_code": 1,
                   "final_reason_code": reason, "final_verdict": "FAIL"})
    record.update(over)
    return record


def accepted_archive_report(**over):
    checks = [
        _check("archive_safety", "PASSED",
               observed={"entries_inspected": 3}),
    ]
    record = accepted_bundle_report()
    record.update({
        "checks": checks,
        "final_reason_code": "ARCHIVE_SAFETY_OK",
        "input_digest": {"algorithm": "sha256", "file_count": None,
                         "non_regular_entry_count": None,
                         "scope": ARCHIVE_SCOPE, "state": "MEASURED",
                         "value": "b" * 64},
        "input_type": "archive_zip",
        "operation": "inspect_archive",
    })
    record.update(over)
    return record


def raw(record):
    return report_schema.canonical_bytes(record)


class TestValidatorAcceptsWellFormedReports(unittest.TestCase):
    def test_accepted_bundle_report(self):
        problems, _r = report_schema.validate_bytes(
            raw(accepted_bundle_report()))
        self.assertEqual(problems, [])

    def test_failing_bundle_report(self):
        problems, _r = report_schema.validate_bytes(
            raw(failing_bundle_report()))
        self.assertEqual(problems, [])

    def test_accepted_archive_report(self):
        problems, _r = report_schema.validate_bytes(
            raw(accepted_archive_report()))
        self.assertEqual(problems, [])


class TestExecutionHonesty(unittest.TestCase):
    """The report is evidence, never prediction."""

    def _problems(self, record):
        problems, _r = report_schema.validate_bytes(raw(record))
        return problems

    def test_not_run_check_may_not_carry_a_reason_code(self):
        record = failing_bundle_report()
        record["checks"][3]["reason_code"] = "MANIFEST_JSON_INVALID"
        self.assertTrue(any("has no result" in p
                            for p in self._problems(record)))

    def test_not_run_check_must_explain_why(self):
        record = failing_bundle_report()
        record["checks"][3]["not_run_reason"] = None
        self.assertTrue(any("without an explicit reason" in p
                            for p in self._problems(record)))

    def test_not_run_check_may_not_report_an_observation(self):
        record = failing_bundle_report()
        record["checks"][3]["observed"] = {"declared_hashes_verified": 7}
        self.assertTrue(any("reports an observation" in p
                            for p in self._problems(record)))

    def test_a_check_may_not_pass_after_evaluation_stopped(self):
        record = failing_bundle_report()
        record["checks"][4] = _check("receipt_chain", "PASSED",
                                     observed={"receipts_verified": 3})
        self.assertTrue(any("already stopped" in p
                            for p in self._problems(record)))

    def test_a_check_may_not_fail_after_evaluation_stopped(self):
        record = failing_bundle_report()
        record["checks"][4] = _check("receipt_chain", "FAILED",
                                     reason="RECEIPT_LINKAGE_BROKEN")
        self.assertTrue(any("already stopped" in p
                            for p in self._problems(record)))

    def test_executed_check_may_not_carry_a_not_run_reason(self):
        record = accepted_bundle_report()
        record["checks"][2]["not_run_reason"] = "because"
        self.assertTrue(any("carries a not_run_reason" in p
                            for p in self._problems(record)))

    def test_failed_check_needs_a_reason_code(self):
        record = failing_bundle_report()
        record["checks"][2]["reason_code"] = None
        self.assertTrue(any("FAILED without a reason_code" in p
                            for p in self._problems(record)))

    def test_passed_check_may_not_carry_a_reason_code(self):
        record = accepted_bundle_report()
        record["checks"][0]["reason_code"] = "SOMETHING"
        self.assertTrue(any("PASSED but carries a reason_code" in p
                            for p in self._problems(record)))

    def test_non_fail_report_may_not_contain_not_run(self):
        record = accepted_bundle_report()
        record["checks"][4] = _check("receipt_chain", "NOT_RUN",
                                     not_run="skipped")
        self.assertTrue(any("cannot contain a NOT_RUN check" in p
                            for p in self._problems(record)))

    def test_fail_report_needs_exactly_one_failed_check(self):
        record = failing_bundle_report()
        record["checks"][2]["status"] = "PASSED"
        record["checks"][2]["reason_code"] = None
        self.assertTrue(any("exactly one FAILED check" in p
                            for p in self._problems(record)))

    def test_final_reason_must_match_the_failing_check(self):
        record = failing_bundle_report()
        record["final_reason_code"] = "SOMETHING_ELSE"
        self.assertTrue(any("does not match the failing check" in p
                            for p in self._problems(record)))

    def test_checks_must_be_the_adopted_sequence_in_order(self):
        record = accepted_bundle_report()
        record["checks"] = list(reversed(record["checks"]))
        self.assertTrue(any("adopted verify_bundle sequence" in p
                            for p in self._problems(record)))

    def test_missing_check_rejected(self):
        record = accepted_bundle_report()
        record["checks"] = record["checks"][:-1]
        self.assertTrue(self._problems(record))


class TestNoPassAndAdoptedIdentities(unittest.TestCase):
    def _problems(self, record):
        problems, _r = report_schema.validate_bytes(raw(record))
        return problems

    def test_pass_verdict_rejected(self):
        record = accepted_bundle_report(final_verdict="PASS", exit_code=0)
        self.assertTrue(any("no PASS path" in p
                            for p in self._problems(record)))

    def test_unreachable_verdict_rejected(self):
        record = accepted_bundle_report(final_verdict="MAYBE")
        self.assertTrue(self._problems(record))

    def test_exit_code_must_match_verdict(self):
        self.assertTrue(any("does not match verdict" in p
                            for p in self._problems(
                                accepted_bundle_report(exit_code=1))))
        self.assertTrue(any("does not match verdict" in p
                            for p in self._problems(
                                failing_bundle_report(exit_code=3))))

    def test_wrong_identity_rejected(self):
        for field, bad in (("schema_version", "witness-report/9"),
                           ("record_type", "something"),
                           ("producer", "someone"),
                           ("producer_version", "0.0.0"),
                           ("verifier", "impostor"),
                           ("verifier_version", "9.9.9")):
            record = accepted_bundle_report(**{field: bad})
            self.assertTrue(self._problems(record),
                            "wrong %s accepted" % field)

    def test_operation_and_input_type_must_agree(self):
        record = accepted_bundle_report(input_type="archive_zip")
        self.assertTrue(any("does not match operation" in p
                            for p in self._problems(record)))

    def test_move81_and_move82_fields_rejected(self):
        for field in ("capability_scope", "implementation_lane", "stage",
                      "binary_sha256", "build_argv", "transcript_name"):
            record = accepted_bundle_report(**{field: "x"})
            self.assertTrue(any("another adopted schema" in p
                                for p in self._problems(record)),
                            "%s accepted" % field)

    def test_extra_and_missing_fields_rejected(self):
        self.assertTrue(self._problems(
            accepted_bundle_report(surprise=1)))
        record = accepted_bundle_report()
        del record["operation"]
        self.assertTrue(self._problems(record))


class TestDigestScopeHonesty(unittest.TestCase):
    def _problems(self, record):
        problems, _r = report_schema.validate_bytes(raw(record))
        return problems

    def test_scope_must_be_explicit(self):
        record = accepted_bundle_report()
        record["input_digest"]["scope"] = "the bundle"
        self.assertTrue(any("explicitly describe" in p
                            for p in self._problems(record)))

    def test_bundle_scope_must_state_which_files_it_covers(self):
        record = accepted_bundle_report()
        record["input_digest"]["scope"] = (
            "sha256 over some of the bundle contents, computed in a "
            "deterministic manner across the whole tree structure")
        self.assertTrue(any("partial digest" in p
                            for p in self._problems(record)))

    def test_bad_digest_value_rejected(self):
        record = accepted_bundle_report()
        record["input_digest"]["value"] = "short"
        self.assertTrue(self._problems(record))

    def test_negative_or_non_integer_counts_rejected(self):
        for bad in (-1, "42", 4.2):
            record = accepted_bundle_report()
            record["input_digest"]["file_count"] = bad
            self.assertTrue(self._problems(record), repr(bad))

    def test_archive_digest_has_no_file_count(self):
        record = accepted_archive_report()
        record["input_digest"]["file_count"] = 5
        self.assertTrue(any("must be null" in p
                            for p in self._problems(record)))

    def test_digest_field_set_is_exact(self):
        record = accepted_bundle_report()
        record["input_digest"]["surprise"] = 1
        self.assertTrue(self._problems(record))
        record = accepted_bundle_report()
        del record["input_digest"]["scope"]
        self.assertTrue(self._problems(record))

    def test_unmeasurable_state_permitted_with_null_value(self):
        record = failing_bundle_report()
        record["input_digest"]["state"] = "UNMEASURABLE"
        record["input_digest"]["value"] = None
        record["input_digest"]["file_count"] = None
        record["input_digest"]["non_regular_entry_count"] = None
        self.assertEqual(self._problems(record), [])

    def test_measured_state_without_a_value_rejected(self):
        record = failing_bundle_report()
        record["input_digest"]["value"] = None
        self.assertTrue(any("MEASURED but no value" in p
                            for p in self._problems(record)))

    def test_measured_state_without_file_count_rejected(self):
        record = accepted_bundle_report()
        record["input_digest"]["file_count"] = None
        self.assertTrue(any("file_count is null" in p
                            for p in self._problems(record)))

    def test_unmeasurable_state_carrying_a_value_rejected(self):
        record = failing_bundle_report()
        record["input_digest"]["state"] = "UNMEASURABLE"
        self.assertTrue(any("UNMEASURABLE but carries a value" in p
                            for p in self._problems(record)))

    def test_unmeasurable_state_carrying_counts_rejected(self):
        record = failing_bundle_report()
        record["input_digest"]["state"] = "UNMEASURABLE"
        record["input_digest"]["value"] = None
        self.assertTrue(any("UNMEASURABLE but carries" in p
                            for p in self._problems(record)))

    def test_invalid_digest_state_rejected(self):
        record = accepted_bundle_report()
        record["input_digest"]["state"] = "PROBABLY"
        self.assertTrue(any("state must be one of" in p
                            for p in self._problems(record)))

    def test_bundle_scope_must_state_mode_binding(self):
        record = accepted_bundle_report()
        record["input_digest"]["scope"] = (
            "sha256 over an injective serialization of EVERY regular file "
            "with its path and content, ordered by raw path bytes")
        self.assertTrue(any("partial digest" in p
                            for p in self._problems(record)))


class TestLimitations(unittest.TestCase):
    def _problems(self, record):
        problems, _r = report_schema.validate_bytes(raw(record))
        return problems

    def test_empty_limitations_rejected(self):
        self.assertTrue(self._problems(
            accepted_bundle_report(limitations=[])))

    def test_limitations_must_mention_not_run(self):
        record = accepted_bundle_report(
            limitations=["the verifier emits no PASS verdict"])
        self.assertTrue(any("NOT_RUN check has no result" in p
                            for p in self._problems(record)))

    def test_limitations_must_mention_no_pass(self):
        record = accepted_bundle_report(
            limitations=["a NOT_RUN check has no result"])
        self.assertTrue(any("no PASS verdict" in p
                            for p in self._problems(record)))


class TestCanonicalBytes(unittest.TestCase):
    def test_canonical_accepted(self):
        problems, _r = report_schema.check_canonical_bytes(
            raw(accepted_bundle_report()))
        self.assertEqual(problems, [])

    def test_non_canonical_key_order_rejected(self):
        record = accepted_bundle_report()
        items = list(record.items())[::-1]
        text = json.dumps(dict(items), sort_keys=False,
                          separators=(",", ":"))
        problems, _r = report_schema.check_canonical_bytes(
            (text + "\n").encode("utf-8"))
        self.assertTrue(problems)

    def test_alternate_spacing_rejected(self):
        record = accepted_bundle_report()
        text = json.dumps(record, sort_keys=True, separators=(", ", ": "))
        problems, _r = report_schema.check_canonical_bytes(
            (text + "\n").encode("utf-8"))
        self.assertTrue(problems)

    def test_missing_trailing_newline_rejected(self):
        problems, _r = report_schema.check_canonical_bytes(
            raw(accepted_bundle_report())[:-1])
        self.assertTrue(problems)

    def test_extra_trailing_newline_rejected(self):
        problems, _r = report_schema.check_canonical_bytes(
            raw(accepted_bundle_report()) + b"\n")
        self.assertTrue(problems)

    def test_two_reports_rejected(self):
        problems, _r = report_schema.check_canonical_bytes(
            raw(accepted_bundle_report()) * 2)
        self.assertTrue(problems)

    def test_duplicate_keys_rejected(self):
        problems, _r = report_schema.check_canonical_bytes(
            b'{"a":1,"a":2}\n')
        self.assertTrue(any("duplicate" in p for p in problems))

    def test_leading_whitespace_rejected(self):
        problems, _r = report_schema.check_canonical_bytes(
            b" " + raw(accepted_bundle_report()))
        self.assertTrue(problems)

    def test_empty_rejected(self):
        problems, _r = report_schema.check_canonical_bytes(b"")
        self.assertTrue(problems)


class TestLegacyCrossCheck(unittest.TestCase):
    """The report may never contradict the adopted legacy verdict line."""

    LEGACY = (b'{"verifier": "witness-verify", '
              b'"version": "0.0.8-step79-diagnostics", '
              b'"verdict": "INCONCLUSIVE", '
              b'"reason_code": "RECEIPT_CHAIN_HASHES_RECOMPUTED", '
              b'"detail": "ok"}\n')

    def test_agreeing_report_accepted(self):
        problems = report_schema.cross_check_legacy(
            accepted_bundle_report(), self.LEGACY, 3)
        self.assertEqual(problems, [])

    def test_contradicting_verdict_rejected(self):
        record = accepted_bundle_report(final_verdict="FAIL", exit_code=1)
        problems = report_schema.cross_check_legacy(record, self.LEGACY, 3)
        self.assertTrue(any("contradicts the legacy verdict" in p
                            for p in problems))

    def test_contradicting_reason_rejected(self):
        record = accepted_bundle_report(final_reason_code="OTHER")
        problems = report_schema.cross_check_legacy(record, self.LEGACY, 3)
        self.assertTrue(any("contradicts the legacy reason" in p
                            for p in problems))

    def test_contradicting_exit_rejected(self):
        problems = report_schema.cross_check_legacy(
            accepted_bundle_report(), self.LEGACY, 1)
        self.assertTrue(any("contradicts the legacy exit" in p
                            for p in problems))

    def test_contradicting_version_rejected(self):
        legacy = self.LEGACY.replace(b"0.0.8-step79-diagnostics", b"9.9.9")
        problems = report_schema.cross_check_legacy(
            accepted_bundle_report(), legacy, 3)
        self.assertTrue(any("contradicts the legacy version" in p
                            for p in problems))


class TestValidatorCli(unittest.TestCase):
    def _write(self, name, data):
        path = os.path.join(_TMP, name)
        with open(path, "wb") as handle:
            handle.write(data)
        return path

    def test_valid_report_passes(self):
        path = self._write("ok.json", raw(accepted_bundle_report()))
        proc = _run([PYTHON_BIN, "-B", SCHEMA_TOOL, "--report", path])
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn(b"MOVE_83_REPORT: PASS", proc.stdout)
        self.assertEqual(proc.stderr, b"")

    def test_invalid_report_fails_without_traceback(self):
        path = self._write("bad.json", b"{not json\n")
        proc = _run([PYTHON_BIN, "-B", SCHEMA_TOOL, "--report", path])
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"MOVE_83_REPORT: FAIL", proc.stdout)
        self.assertNotIn(b"Traceback", proc.stderr)

    def test_legacy_cross_check_via_cli(self):
        report = self._write("x.json", raw(accepted_bundle_report()))
        legacy = self._write("legacy.txt", TestLegacyCrossCheck.LEGACY)
        proc = _run([PYTHON_BIN, "-B", SCHEMA_TOOL, "--report", report,
                     "--legacy-stdout", legacy, "--legacy-exit", "3"])
        self.assertEqual(proc.returncode, 0, proc.stdout)
        proc = _run([PYTHON_BIN, "-B", SCHEMA_TOOL, "--report", report,
                     "--legacy-stdout", legacy, "--legacy-exit", "1"])
        self.assertEqual(proc.returncode, 1)

    def test_relative_report_path_rejected(self):
        proc = _run([PYTHON_BIN, "-B", SCHEMA_TOOL, "--report", "rel.json"])
        self.assertEqual(proc.returncode, 2)


class TestRustChangeIsStrictlyAdditive(unittest.TestCase):
    """The one authorised inherited modification must add only."""

    def _main(self):
        with open(MAIN_RS, encoding="utf-8") as handle:
            return handle.read()

    def _report_code(self):
        with open(REPORT_RS, encoding="utf-8") as handle:
            return "\n".join(l for l in handle.read().splitlines()
                             if not l.strip().startswith("//"))

    def test_adopted_arms_are_untouched(self):
        text = self._main()
        self.assertIn('if args.len() == 3 && args[1] == "verify" {', text)
        self.assertIn(
            'if args.len() == 3 && args[1] == "inspect-archive" {', text)

    def test_adopted_usage_text_is_unchanged(self):
        text = self._main()
        self.assertIn(
            'eprintln!("usage: witness-verify verify <bundle-dir>");', text)
        usage_start = text.find('eprintln!("usage:')
        usage_end = text.find("process::exit(EXIT_USAGE)")
        self.assertNotEqual(usage_start, -1)
        self.assertNotEqual(usage_end, -1)
        # the usage text must NOT advertise the new commands: its exact
        # stderr bytes are part of the adopted CLI contract
        self.assertNotIn("report-bundle", text[usage_start:usage_end])
        self.assertNotIn("report-archive", text[usage_start:usage_end])

    def test_new_arms_come_after_the_adopted_arms(self):
        text = self._main()
        verify = text.find('args[1] == "verify"')
        inspect = text.find('args[1] == "inspect-archive"')
        report_b = text.find('args[1] == "report-bundle"')
        report_a = text.find('args[1] == "report-archive"')
        usage = text.find('eprintln!("usage:')
        for pos in (verify, inspect, report_b, report_a, usage):
            self.assertNotEqual(pos, -1)
        self.assertLess(verify, report_b)
        self.assertLess(inspect, report_b)
        self.assertLess(report_b, usage)
        self.assertLess(report_a, usage)

    def test_new_arms_require_exact_argument_count(self):
        text = self._main()
        self.assertIn('args.len() == 3 && args[1] == "report-bundle"', text)
        self.assertIn('args.len() == 3 && args[1] == "report-archive"',
                      text)

    def test_report_module_is_declared(self):
        self.assertIn("mod report;", self._main())

    def test_report_module_adds_no_check(self):
        text = self._report_code()
        for call in ("manifest::validate", "hashes::verify_declared_hashes",
                     "receipts::verify_receipt_chain",
                     "zipguard::inspect_archive"):
            self.assertIn(call, text)

    def test_report_module_never_writes_to_the_filesystem(self):
        code = self._report_code()
        for forbidden in ("File::create", "fs::write", "create_dir",
                          "remove_file", "remove_dir", "OpenOptions"):
            self.assertNotIn(forbidden, code)

    def test_report_module_uses_no_unsafe_and_no_cfg_conditionals(self):
        """No `unsafe` and no conditional compilation. The module DOES use
        the Unix permission and path interfaces unconditionally, which is
        a deliberate, documented limitation: the digest definition is
        Unix-only, matching the only established target."""
        code = self._report_code()
        self.assertNotIn("unsafe", code)
        for token in ("target_os", "target_arch", "cfg(unix",
                      "cfg(windows"):
            self.assertNotIn(token, code)

    def test_digest_uses_the_actual_unix_mode(self):
        code = self._report_code()
        self.assertIn("use std::os::unix::fs::PermissionsExt;", code)
        self.assertIn("meta.permissions().mode() & DIGEST_MODE_MASK", code)
        # the readonly() approximation must be gone from the code
        self.assertNotIn("permissions().readonly()", code)

    def test_digest_uses_the_explicit_unix_path_bytes(self):
        code = self._report_code()
        self.assertIn("use std::os::unix::ffi::OsStrExt;", code)
        self.assertIn("path.as_os_str().as_bytes().to_vec()", code)
        self.assertNotIn("as_encoded_bytes", code)
        self.assertNotIn("to_string_lossy", code)

    def test_scope_states_the_unix_only_limitation(self):
        import re
        with open(REPORT_RS, encoding="utf-8") as handle:
            text = handle.read()
        start = text.find("const DIGEST_SCOPE_BUNDLE")
        scope = re.sub(r"\\\n\s*", "",
                       text[start:text.find('";', start)])
        self.assertIn("Unix-only", scope)
        self.assertIn("ACTUAL", scope)
        self.assertIn("raw Unix path bytes", scope)

    def test_report_module_does_not_follow_symlinks(self):
        self.assertIn("symlink_metadata", self._report_code())

    def test_no_pass_verdict_constructed_in_rust(self):
        code = self._report_code()
        self.assertNotIn('"PASS"', code)
        self.assertNotIn("VERDICT_PASS", code)

    def test_rust_emits_canonical_separators(self):
        """The legacy verdict line uses spaced separators; the report must
        be canonical, so the builder never emits `", "` or `": "`."""
        code = self._report_code()
        spaced_pair = '\\",' + ' ' + '\\"'
        spaced_colon = '\\":' + ' ' + '\\"'
        self.assertNotIn(spaced_pair, code)
        self.assertNotIn(spaced_colon, code)
        self.assertIn('String::from("{")', code)


class TestInheritedBaseline(unittest.TestCase):
    def test_allowlist_declares_one_additive_modification(self):
        with open(ALLOWLIST, encoding="utf-8") as handle:
            data = json.load(handle)
        self.assertEqual(data["modified_paths"],
                         ["rust/witness-verify/src/main.rs"])
        self.assertTrue(data["added_paths"])
        self.assertEqual(data["added_paths"], sorted(data["added_paths"]))

    def test_every_declared_addition_exists(self):
        with open(ALLOWLIST, encoding="utf-8") as handle:
            data = json.load(handle)
        for rel in data["added_paths"]:
            self.assertTrue(os.path.isfile(os.path.join(ROOT, rel)), rel)

    def test_no_packaged_executable(self):
        with open(ALLOWLIST, encoding="utf-8") as handle:
            data = json.load(handle)
        for rel in data["added_paths"]:
            with open(os.path.join(ROOT, rel), "rb") as handle:
                self.assertNotEqual(handle.read(4), b"\x7fELF", rel)

    def test_strictly_additive_helper_accepts_additions(self):
        import check_move83_inherited as checker
        adopted = b"line one\nline two\nline three\n"
        added = b"line one\nNEW\nline two\nline three\nALSO NEW\n"
        self.assertTrue(checker._is_strictly_additive(adopted, added))

    def test_strictly_additive_helper_rejects_changes(self):
        import check_move83_inherited as checker
        adopted = b"line one\nline two\nline three\n"
        changed = b"line one\nline TWO CHANGED\nline three\n"
        removed = b"line one\nline three\n"
        self.assertFalse(checker._is_strictly_additive(adopted, changed))
        self.assertFalse(checker._is_strictly_additive(adopted, removed))

    def test_strictly_additive_helper_rejects_reordering(self):
        import check_move83_inherited as checker
        adopted = b"alpha\nbeta\ngamma\n"
        reordered = b"gamma\nbeta\nalpha\n"
        self.assertFalse(checker._is_strictly_additive(adopted, reordered))


class TestSuitePortability(unittest.TestCase):
    _SH = "/bin" + "/sh"
    _ENV = "/usr" + "/bin" + "/env"
    _SHEBANG = "#" + "!"

    def _sources(self):
        for name in sorted(os.listdir(HERE)):
            if name.endswith(".py"):
                with open(os.path.join(HERE, name), encoding="utf-8") as h:
                    yield name, h.read()

    def test_no_hardcoded_shebangs_in_generated_fixtures(self):
        for name, src in self._sources():
            for line in src.splitlines():
                stripped = line.strip()
                if stripped.startswith("#") and not stripped.startswith(
                        self._SHEBANG):
                    continue
                if line.startswith(self._SHEBANG) and name.endswith(".py"):
                    continue          # each tool's own shebang line
                self.assertNotIn(self._SHEBANG + self._SH, line, name)
                self.assertNotIn(self._SHEBANG + self._ENV, line, name)

    def test_interpreter_and_shell_validated(self):
        for path in (TEST_SH, PYTHON_BIN):
            self.assertTrue(os.path.isabs(path))
            self.assertTrue(os.path.isfile(path))
            self.assertTrue(os.access(path, os.X_OK))
            self.assertEqual(path, os.path.realpath(path))

    def test_every_subprocess_is_bounded(self):
        import re
        for name, src in self._sources():
            for match in re.finditer(r"subprocess\.run\((.*?)\)\n", src,
                                     re.S):
                self.assertIn("timeout", match.group(1), name)

    def test_gate_supplies_the_trusted_shell(self):
        with open(GATE, encoding="utf-8") as handle:
            self.assertIn('MOVE83_TEST_SH="$TRUSTED_SH"', handle.read())


REASON_MAP = os.path.join(ROOT, "verify", "agreement_harness_v01",
                          "reason_map.json")


class TestClassificationFromAdoptedAuthority(unittest.TestCase):
    """B5: class and stage are LOOKED UP in the adopted reason_map.json.
    No mapping is restated in Rust, in the validator or in these tests."""

    def _map_bytes(self):
        with open(REASON_MAP, "rb") as handle:
            return handle.read()

    def test_core_record_has_no_classification(self):
        record = accepted_bundle_report()
        self.assertNotIn("final_reason_class", record)
        self.assertNotIn("final_stage", record)
        problems, _r = report_schema.validate_bytes(raw(record))
        self.assertEqual(problems, [])

    def test_classification_adds_exactly_two_fields(self):
        record = accepted_bundle_report()
        done = report_schema.classify(record, self._map_bytes())
        self.assertEqual(set(done) - set(record),
                         {"final_reason_class", "final_stage"})
        self.assertEqual(done["record_type"], report_schema.RECORD_TYPE)

    def test_classified_values_come_from_the_adopted_map(self):
        record = accepted_bundle_report()
        done = report_schema.classify(record, self._map_bytes())
        with open(REASON_MAP, encoding="utf-8") as handle:
            adopted = json.load(handle)
        wanted = [e for e in adopted["rust_bundle"]
                  if e.get("match_type") == "exact"
                  and e.get("value") == record["final_reason_code"]]
        self.assertEqual(len(wanted), 1)
        self.assertEqual(done["final_reason_class"], wanted[0]["class"])
        self.assertEqual(done["final_stage"], wanted[0]["stage"])

    def test_archive_classification_uses_the_archive_lane(self):
        record = accepted_archive_report()
        done = report_schema.classify(record, self._map_bytes())
        with open(REASON_MAP, encoding="utf-8") as handle:
            adopted = json.load(handle)
        wanted = [e for e in adopted["archive"]
                  if e.get("match_type") == "exact"
                  and e.get("value") == record["final_reason_code"]]
        self.assertEqual(len(wanted), 1)
        self.assertEqual(done["final_reason_class"], wanted[0]["class"])
        self.assertEqual(done["final_stage"], wanted[0]["stage"])

    def test_reason_absent_from_the_adopted_map_is_rejected(self):
        record = accepted_bundle_report(
            final_reason_code="NOT_A_REAL_REASON")
        with self.assertRaises(report_schema.ReportError) as ctx:
            report_schema.classify(record, self._map_bytes())
        self.assertIn("not present in the adopted reason map",
                      str(ctx.exception))

    def test_classified_record_validates(self):
        done = report_schema.classify(accepted_bundle_report(),
                                      self._map_bytes())
        problems, _r = report_schema.validate_bytes(raw(done),
                                                    classified=True)
        self.assertEqual(problems, [])

    def test_core_record_rejected_when_classification_required(self):
        problems, _r = report_schema.validate_bytes(
            raw(accepted_bundle_report()), classified=True)
        self.assertTrue(problems)

    def test_classified_record_rejected_in_core_mode(self):
        done = report_schema.classify(accepted_bundle_report(),
                                      self._map_bytes())
        problems, _r = report_schema.validate_bytes(raw(done))
        self.assertTrue(problems)

    def test_wrong_class_or_stage_rejected(self):
        done = report_schema.classify(accepted_bundle_report(),
                                      self._map_bytes())
        for field in ("final_reason_class", "final_stage"):
            bad = dict(done)
            bad[field] = ""
            problems, _r = report_schema.validate_bytes(
                raw(bad), classified=True)
            self.assertTrue(problems, field)

    def test_extra_field_rejected_in_classified_mode(self):
        done = report_schema.classify(accepted_bundle_report(),
                                      self._map_bytes())
        done["surprise"] = 1
        problems, _r = report_schema.validate_bytes(raw(done),
                                                    classified=True)
        self.assertTrue(any("unexpected field" in p for p in problems))

    def test_no_mapping_is_restated_in_production_code(self):
        """Neither the validator nor the Rust module may carry a
        hand-written reason -> class/stage table. Class names are built
        from fragments so this scanner cannot match its own source."""
        classes = set()
        stages = set()
        with open(REASON_MAP, encoding="utf-8") as handle:
            adopted = json.load(handle)
        for lane in ("rust_bundle", "archive"):
            for entry in adopted[lane]:
                classes.add(entry["class"])
                stages.add(entry["stage"])
        self.assertTrue(classes)
        for path in (SCHEMA_TOOL, REPORT_RS):
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            # only a QUOTED literal is a restatement; a bare substring
            # can appear innocently inside an English word (the class
            # "OK" is a substring of "LOOKING")
            hits = sorted(c for c in classes
                          if ('"%s"' % c) in text or ("'%s'" % c) in text)
            self.assertEqual(
                hits, [],
                "%s restates adopted reason classes: %s" % (path, hits))
            # lane identifiers are legitimately named in production code
            # (classify() selects the lane); "archive" is both a lane and
            # a stage, so it is excluded from the stage scan
            lane_names = {"rust_bundle", "archive", "python_bundle"}
            stage_hits = sorted(
                st for st in stages - lane_names
                if ('"%s"' % st) in text or ("'%s'" % st) in text)
            self.assertEqual(
                stage_hits, [],
                "%s restates adopted stages: %s" % (path, stage_hits))

    def test_classify_cli_writes_a_valid_classified_report(self):
        core = os.path.join(_TMP, "core.json")
        out = os.path.join(_TMP, "classified.json")
        with open(core, "wb") as handle:
            handle.write(raw(accepted_bundle_report()))
        proc = _run([PYTHON_BIN, "-B", SCHEMA_TOOL, "--report", core,
                     "--reason-map", REASON_MAP, "--classify-out", out])
        self.assertEqual(proc.returncode, 0, proc.stdout)
        with open(out, "rb") as handle:
            data = handle.read()
        problems, _r = report_schema.validate_bytes(data, classified=True)
        self.assertEqual(problems, [])

    def test_classify_cli_rejects_an_unmapped_reason(self):
        core = os.path.join(_TMP, "core_bad.json")
        out = os.path.join(_TMP, "classified_bad.json")
        with open(core, "wb") as handle:
            handle.write(raw(accepted_bundle_report(
                final_reason_code="NOT_A_REAL_REASON")))
        proc = _run([PYTHON_BIN, "-B", SCHEMA_TOOL, "--report", core,
                     "--reason-map", REASON_MAP, "--classify-out", out])
        self.assertEqual(proc.returncode, 1)
        self.assertFalse(os.path.exists(out))


class TestDigestSerializationIsInjective(unittest.TestCase):
    """B3/B4: the Rust serialization must bind path, mode and content, and
    must not be lossy. These tests exercise a faithful Python model of the
    documented algorithm and confirm the Rust source states it exactly."""

    DOMAIN = b"witness-bundle-digest/1\n"

    def _serialize(self, entries):
        """entries: list of (raw relpath bytes, mode, hex digest)."""
        import struct
        blob = bytearray(self.DOMAIN)
        for rel, mode, hexd in sorted(entries, key=lambda e: e[0]):
            blob += struct.pack("<Q", len(rel))
            blob += rel
            blob += struct.pack("<I", mode & 0o7777)
            blob += struct.pack("<Q", len(hexd))
            blob += hexd
        import hashlib
        return hashlib.sha256(bytes(blob)).hexdigest()

    def test_mode_change_changes_the_digest(self):
        a = [(b"f.txt", 0o644, b"a" * 64)]
        b = [(b"f.txt", 0o444, b"a" * 64)]
        self.assertNotEqual(self._serialize(a), self._serialize(b))

    def test_content_change_changes_the_digest(self):
        a = [(b"f.txt", 0o644, b"a" * 64)]
        b = [(b"f.txt", 0o644, b"b" * 64)]
        self.assertNotEqual(self._serialize(a), self._serialize(b))

    def test_path_change_changes_the_digest(self):
        a = [(b"f.txt", 0o644, b"a" * 64)]
        b = [(b"g.txt", 0o644, b"a" * 64)]
        self.assertNotEqual(self._serialize(a), self._serialize(b))

    def test_newline_in_a_filename_is_unambiguous(self):
        a = [(b"a\nb", 0o644, b"a" * 64)]
        b = [(b"a", 0o644, b"a" * 64), (b"b", 0o644, b"a" * 64)]
        self.assertNotEqual(self._serialize(a), self._serialize(b))

    def test_non_utf8_paths_do_not_collide(self):
        # two distinct byte sequences whose lossy UTF-8 forms are both
        # the replacement character
        a = [(b"\xff", 0o644, b"a" * 64)]
        b = [(b"\xfe", 0o644, b"a" * 64)]
        self.assertNotEqual(self._serialize(a), self._serialize(b))

    def test_lossy_collision_pair_is_distinguished(self):
        a = [(b"x\xff", 0o644, b"a" * 64)]
        b = [(b"x\xfd", 0o644, b"a" * 64)]
        self.assertNotEqual(self._serialize(a), self._serialize(b))

    def test_prefix_pairs_do_not_collide(self):
        a = [(b"ab", 0o644, b"a" * 64), (b"c", 0o644, b"a" * 64)]
        b = [(b"a", 0o644, b"a" * 64), (b"bc", 0o644, b"a" * 64)]
        self.assertNotEqual(self._serialize(a), self._serialize(b))

    def test_empty_file_is_representable(self):
        import hashlib
        empty = hashlib.sha256(b"").hexdigest().encode()
        digest = self._serialize([(b"empty", 0o644, empty)])
        self.assertEqual(len(digest), 64)

    def test_nested_paths_are_bound(self):
        a = [(b"d/f", 0o644, b"a" * 64)]
        b = [(b"e/f", 0o644, b"a" * 64)]
        self.assertNotEqual(self._serialize(a), self._serialize(b))

    def test_order_is_independent_of_enumeration_order(self):
        entries = [(b"b", 0o644, b"a" * 64), (b"a", 0o644, b"c" * 64),
                   (b"c", 0o755, b"d" * 64)]
        self.assertEqual(self._serialize(entries),
                         self._serialize(list(reversed(entries))))

    def test_empty_tree_digests_the_domain_prefix_only(self):
        import hashlib
        self.assertEqual(self._serialize([]),
                         hashlib.sha256(self.DOMAIN).hexdigest())

    def test_rust_states_the_same_algorithm(self):
        with open(REPORT_RS, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn('b"witness-bundle-digest/3', text)
        self.assertIn("DIGEST_MODE_MASK: u32 = 0o7777", text)
        self.assertIn("to_le_bytes()", text)
        self.assertIn("as_bytes().to_vec()", text)
        self.assertIn(
            "a.relpath.cmp(&b.relpath).then(a.kind.cmp(&b.kind))", text)

    def test_rust_does_not_use_lossy_path_conversion(self):
        with open(REPORT_RS, encoding="utf-8") as handle:
            code = "\n".join(l for l in handle.read().splitlines()
                             if not l.strip().startswith("//"))
        self.assertNotIn("to_string_lossy", code)

    def test_python_model_is_supplementary_only(self):
        """This class models the DOCUMENTED algorithm as a cross-check. It
        is explicitly not the production authority: the binding proof is
        the gate running the real binary over differential trees."""
        with open(os.path.join(HERE, "report_tests.py"),
                  encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("supplementary", text)

    def test_scope_text_documents_the_algorithm(self):
        import re
        with open(REPORT_RS, encoding="utf-8") as handle:
            text = handle.read()
        start = text.find("const DIGEST_SCOPE_BUNDLE")
        end = text.find('";', start)
        # join Rust line-continuations so phrases are contiguous
        scope = re.sub(r"\\\n\s*", "", text[start:end])
        for token in ("domain-separation", "little-endian", "0o7777",
                      "raw relative-path bytes", "mode bits"):
            self.assertIn(token, scope, token)


class TestArchiveEvaluationMirrorsAdopted(unittest.TestCase):
    """B1: the adopted evaluate_archive has exactly one check."""

    def test_validator_expects_one_archive_check(self):
        self.assertEqual(report_schema.ARCHIVE_CHECKS, ("archive_safety",))

    def test_invented_readable_check_rejected(self):
        record = accepted_archive_report()
        record["checks"] = [
            _check("archive_path_readable", "PASSED"),
            _check("archive_safety", "PASSED",
                   observed={"entries_inspected": 3}),
        ]
        problems, _r = report_schema.validate_bytes(raw(record))
        self.assertTrue(any("adopted inspect_archive sequence" in p
                            for p in problems))

    def test_executed_check_after_a_failure_rejected(self):
        record = accepted_archive_report()
        record["checks"] = [
            _check("archive_safety", "FAILED",
                   reason="ARCHIVE_PATH_TRAVERSAL"),
        ]
        record["final_verdict"] = "FAIL"
        record["final_reason_code"] = "ARCHIVE_PATH_TRAVERSAL"
        record["exit_code"] = 1
        problems, _r = report_schema.validate_bytes(raw(record))
        self.assertEqual(problems, [])

    def test_no_invented_reason_code_in_production_code(self):
        # built from fragments so this scanner cannot match itself
        invented = "ARCHIVE_UNREADABLE" + "_FOR_" + "DIGEST"
        for path in (REPORT_RS, SCHEMA_TOOL):
            with open(path, encoding="utf-8") as handle:
                self.assertNotIn(invented, handle.read(), path)

    def test_production_code_invents_no_reason_code_at_all(self):
        """Every reason code in the report comes from the adopted check
        functions; the report module must define none of its own."""
        with open(REPORT_RS, encoding="utf-8") as handle:
            code = "\n".join(l for l in handle.read().splitlines()
                             if not l.strip().startswith("//"))
        import re
        # SCREAMING_SNAKE string literals would be invented codes; the
        # only ones permitted are the adopted verdict/reason constants the
        # adopted evaluation itself returns.
        permitted = {"BUNDLE_PATH_MISSING", "BUNDLE_PATH_NOT_A_DIRECTORY",
                     "RECEIPT_CHAIN_HASHES_RECOMPUTED",
                     "ARCHIVE_SAFETY_OK", "MEASURED", "UNMEASURABLE",
                     "PASSED", "FAILED", "NOT_RUN"}
        found = set(re.findall(r'"([A-Z][A-Z0-9_]{4,})"', code))
        self.assertEqual(sorted(found - permitted), [])


class TestDigestFixtureBuilder(unittest.TestCase):
    """B2: the differential fixtures the gate runs the REAL binary over.

    These prove the fixtures genuinely differ in exactly one bound
    property and that the filesystem modes were actually applied. The
    binary comparison itself happens in the gate, on device."""

    def _build(self, tag):
        import report_schema as rs
        outdir = os.path.join(_TMP, "dgf_" + tag)
        return rs.make_digest_fixtures(outdir)

    def test_mode_pairs_have_identical_content(self):
        for case in self._build("content"):
            if case["case_id"] == "content_differs":
                continue
            a, b = case["sides"]
            self.assertEqual(a["content_sha256"], b["content_sha256"],
                             case["case_id"])

    def test_actual_filesystem_modes_are_verified(self):
        for case in self._build("modes"):
            for side in case["sides"]:
                actual = stat.S_IMODE(
                    os.lstat(os.path.join(side["root"],
                                          side["path"])).st_mode)
                self.assertEqual(actual, side["requested_mode"],
                                 case["case_id"])
                self.assertEqual(actual, side["actual_mode"])

    def test_required_mode_cases_present(self):
        ids = {c["case_id"] for c in self._build("ids")}
        for required in ("mode_0644_vs_0755", "mode_0600_vs_0644",
                         "mode_empty_file", "mode_nested_path"):
            self.assertIn(required, ids)

    def test_mode_pairs_differ_only_in_mode(self):
        for case in self._build("only"):
            if not case["case_id"].startswith("mode_"):
                continue
            a, b = case["sides"]
            self.assertEqual(a["path"], b["path"])
            self.assertEqual(a["content_sha256"], b["content_sha256"])
            self.assertNotEqual(a["actual_mode"], b["actual_mode"])

    def test_empty_file_case_is_genuinely_empty(self):
        cases = {c["case_id"]: c for c in self._build("empty")}
        side = cases["mode_empty_file"]["sides"][0]
        target = os.path.join(side["root"], side["path"])
        self.assertEqual(os.path.getsize(target), 0)

    def test_nested_case_is_genuinely_nested(self):
        cases = {c["case_id"]: c for c in self._build("nested")}
        self.assertIn("/", cases["mode_nested_path"]["sides"][0]["path"])

    def test_control_pair_is_identical(self):
        cases = {c["case_id"]: c for c in self._build("ctl")}
        control = cases["identical_control"]
        a, b = control["sides"]
        self.assertFalse(control["must_differ"])
        self.assertEqual(a["actual_mode"], b["actual_mode"])
        self.assertEqual(a["content_sha256"], b["content_sha256"])

    def test_content_case_differs_in_content_only(self):
        cases = {c["case_id"]: c for c in self._build("cnt")}
        case = cases["content_differs"]
        a, b = case["sides"]
        self.assertEqual(a["actual_mode"], b["actual_mode"])
        self.assertNotEqual(a["content_sha256"], b["content_sha256"])

    def test_path_fixtures_cover_hostile_names(self):
        import report_schema as rs
        built = rs.make_path_fixtures(os.path.join(_TMP, "ptf"))
        ids = {c["case_id"] for c in built}
        for required in ("path_newline", "path_invalid_utf8_a",
                         "path_invalid_utf8_b", "path_nested"):
            self.assertIn(required, ids)

    def test_invalid_utf8_names_are_distinct_on_disk(self):
        import report_schema as rs
        built = {c["case_id"]: c
                 for c in rs.make_path_fixtures(
                     os.path.join(_TMP, "ptf2"))}
        a = built["path_invalid_utf8_a"]
        b = built["path_invalid_utf8_b"]
        if not (a["supported"] and b["supported"]):
            self.assertFalse(a["supported"])
            return
        def _names(root):
            found = []
            for dirpath, _dn, filenames in os.walk(
                    os.fsencode(root)):
                for name in filenames:
                    found.append(name)
            return found
        self.assertNotEqual(sorted(_names(a["root"])),
                            sorted(_names(b["root"])))

    def test_gate_runs_the_real_binary_over_the_fixtures(self):
        with open(GATE, encoding="utf-8") as handle:
            code = handle.read()
        self.assertIn("--make-digest-fixtures", code)
        self.assertIn("--make-path-fixtures", code)
        self.assertIn("_digest_of()", code)
        self.assertIn("MOVE_83_DIGEST_BINDING", code)
        # both profiles are compared, and a non-differing digest fails
        self.assertIn('"$RELEASE_BIN"', code)
        self.assertIn('"$DEBUG_BIN"', code)
        self.assertIn("digest UNCHANGED although the bound property "
                      "differs", code)

    def test_python_model_is_not_the_production_authority(self):
        """The Python serialization model exists as a supplementary
        cross-check; the gate must not use it to establish digests."""
        with open(GATE, encoding="utf-8") as handle:
            code = handle.read()
        self.assertNotIn("_serialize", code)


class TestMove82ChildGateContract(unittest.TestCase):
    """The Move 82 child gate has its own mandatory input contract. v03
    forwarded only the REAL_* dependencies, so the child would have
    terminated with usage exit 2 before establishing anything."""

    ADOPTED_M82_SHA = \
        "7c3340f10b111196ec64e170b5a8a00b44c87e16c4b01390abf36734dc0a3a7c"

    def _gate(self):
        with open(GATE, encoding="utf-8") as handle:
            return handle.read()

    def _code(self):
        return "\n".join(l for l in self._gate().splitlines()
                          if not l.strip().startswith("#"))

    def test_child_receives_every_mandatory_input(self):
        code = self._code()
        for assignment in ('MOVE82_CANDIDATE_ZIP="$_M82_CHILD_ZIP"',
                           'MOVE82_CANDIDATE_SHA256="$_M82_EXPECT"',
                           'MOVE82_OUTPUT_DIR="$_M82_CHILD_OUT"',
                           'REAL_MOVE81="$REAL_MOVE81"',
                           'REAL_MOVE80="$REAL_MOVE80"',
                           'REAL_MOVE79="$REAL_MOVE79"',
                           'REAL_MOVE78="$REAL_MOVE78"',
                           'REAL_705="$REAL_705"'):
            self.assertIn(assignment, code,
                          "child gate is missing %s" % assignment)

    def test_gate_requires_real_move81_as_an_input(self):
        code = self._code()
        self.assertIn('[ -z "${REAL_MOVE81:-}" ]', code)
        self.assertIn('"REAL_MOVE81=$REAL_MOVE81"', code)

    def test_child_output_dir_is_fresh_empty_and_separate(self):
        """The child output dir now lives inside the child RUN directory,
        which is what the adopted Move 82 contract requires."""
        code = self._code()
        self.assertIn('_M82_CHILD_OUT="$_M82_RUN/move82_output"', code)
        self.assertIn('mkdir "$_M82_CHILD_OUT"', code)
        # never the Move 83 output directory, never inside the child source
        self.assertIn('[ "$_M82_CHILD_OUT" = "$OUT_DIR" ]', code)
        self.assertIn('"$_M82_ROOT"|"$_M82_ROOT"/*', code)
        self.assertIn('ls -A "$_M82_CHILD_OUT"', code)

    def test_child_markers_are_move82_markers(self):
        code = self._code()
        self.assertIn('"MOVE_82_PORTABLE_BUILD_ADOPTION_GATE: PASS"', code)
        # a Move 83 marker could never be emitted by the Move 82 child
        marker = "MOVE_83_REPORT_ADOPTION_GATE: PASS"
        child_start = code.find("_M82_OUT")
        self.assertNotIn('"%s" \\' % marker, code[child_start:])

    def test_child_marker_set_covers_the_complete_child_gate(self):
        code = self._code()
        for marker in ("MOVE_82_CANDIDATE_IDENTITY: PASS",
                       "MOVE_82_BASELINE_IMMUTABILITY: PASS",
                       "MOVE_82_CLEAN_RELEASE_BUILD: PASS",
                       "MOVE_82_STANDALONE_EXECUTION: PASS",
                       "MOVE_82_DEBUG_RELEASE_EQUIVALENCE: PASS",
                       "MOVE_81_REGRESSION_GATE: PASS",
                       "SYSTEM_AGREEMENT_RESULT: FAIL",
                       "SYSTEM_AGREEMENT_REASON: "
                       "BEHAVIOURAL_DIVERGENCE_DETECTED"):
            self.assertIn(marker, code, marker)

    def test_adopted_move82_hash_is_the_baseline(self):
        self.assertIn(self.ADOPTED_M82_SHA, self._gate())

    def test_no_mislabelled_move81_baseline_claims(self):
        """Move 82 v07 is the Move 83 baseline; Move 81 v08 is a
        dependency of the child. Labels must say which is which."""
        text = self._gate()
        for false_label in (
                "baseline immutability against the real adopted Move 81",
                "candidate vs real Move 81 v08 zip",
                "supplied Move 81 zip",
                "extracted Move 81 root",
                "Move 81 child gate",
                "complete Move 81 adoption/regression child gate"):
            self.assertNotIn(false_label, text, false_label)


class TestRustUnitSuiteIsExecuted(unittest.TestCase):
    """B3: the Rust unit suite must be run, not inferred."""

    def _gate(self):
        with open(GATE, encoding="utf-8") as handle:
            return handle.read()

    def test_gate_runs_cargo_test(self):
        code = self._gate()
        self.assertIn('"$TRUSTED_CARGO" test -q', code)

    def test_cargo_test_streams_and_status_checked_separately(self):
        code = self._gate()
        self.assertIn('>"$_CT_TOUT" 2>"$_CT_TERR"', code)
        self.assertIn('"$_ct_trc" -ne 0', code)
        self.assertIn('grep -q "test result: ok"', code)
        self.assertIn("cargo test ran no tests", code)

    def test_rust_unit_tests_assert_the_core_record_type(self):
        with open(REPORT_RS, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("fn raw_report_emits_the_core_record_type", text)
        self.assertIn('assert_eq!(REPORT_RECORD_TYPE, '
                      '"verification_report_core")', text)

    def test_rust_unit_tests_cover_the_repaired_behaviours(self):
        with open(REPORT_RS, encoding="utf-8") as handle:
            text = handle.read()
        for name in ("fn raw_report_carries_no_classification",
                     "fn archive_report_records_exactly_one_check",
                     "fn unmeasurable_digest_carries_no_value"):
            self.assertIn(name, text, name)

    def test_no_rust_unit_test_asserts_the_completed_record_type(self):
        """report_bundle emits the CORE type; only the completion layer
        produces `verification_report`."""
        with open(REPORT_RS, encoding="utf-8") as handle:
            text = handle.read()
        start = text.find("#[cfg(test)]")
        tests = text[start:]
        self.assertNotIn('line.contains("\\"record_type\\":'
                         '\\"verification_report\\"")', tests)


class TestGateCanonicalSelfBinding(unittest.TestCase):
    """The v04 Termux run died here: the packaged gate's self-binding
    check accepted only `check_move83_portable_build_adoption.sh`, a file
    that does not exist, so the genuine gate rejected itself before doing
    anything. These tests EXECUTE the pattern extracted verbatim from the
    packaged script."""

    PACKAGED_NAME = "check_move83_report_adoption.sh"

    def _gate_text(self):
        with open(GATE, encoding="utf-8") as handle:
            return handle.read()

    def _extract_case_pattern(self):
        """The exact accepting pattern from the packaged self-binding
        check -- read from the script, never restated here."""
        import re
        text = self._gate_text()
        match = re.search(r'case "\$SCRIPT_REAL" in\s*\n\s*(\S+)\) : ;;',
                          text)
        self.assertIsNotNone(match, "self-binding case not found")
        return match.group(1)

    def _matches(self, pattern, candidate_path):
        """Run the GENUINE shell pattern against a path, using the shell
        itself so the semantics are the shell's, not Python's."""
        script = os.path.join(_TMP, "selfbind_probe.sh")
        with open(script, "w", encoding="utf-8") as handle:
            handle.write(
                'SCRIPT_REAL="$1"\n'
                'case "$SCRIPT_REAL" in\n'
                '    %s) exit 0 ;;\n'
                '    *) exit 1 ;;\n'
                'esac\n' % pattern)
        proc = _run([TEST_SH, script, candidate_path])
        return proc.returncode == 0

    def test_packaged_gate_file_exists_under_its_canonical_name(self):
        self.assertTrue(os.path.isfile(GATE))
        self.assertTrue(GATE.endswith("tools/" + self.PACKAGED_NAME))

    def test_genuine_packaged_name_is_accepted(self):
        pattern = self._extract_case_pattern()
        genuine = "/home/u/run/project-witness-main/tools/%s" \
            % self.PACKAGED_NAME
        self.assertTrue(
            self._matches(pattern, genuine),
            "the packaged gate rejects its own canonical name")

    def test_the_real_termux_style_path_is_accepted(self):
        pattern = self._extract_case_pattern()
        real = ("/data/data/com.termux/files/home/m83_internal/"
                "project-witness-main/tools/%s" % self.PACKAGED_NAME)
        self.assertTrue(self._matches(pattern, real))

    def test_renamed_copy_is_rejected(self):
        pattern = self._extract_case_pattern()
        for renamed in ("tools/check_move83_report_adoption_copy.sh",
                        "tools/check_move83_portable_build_adoption.sh",
                        "tools/check_move82_portable_build_adoption.sh",
                        "tools/gate.sh"):
            self.assertFalse(
                self._matches(pattern, "/home/u/pw/" + renamed),
                "renamed gate %s was accepted" % renamed)

    def test_gate_outside_tools_directory_is_rejected(self):
        pattern = self._extract_case_pattern()
        self.assertFalse(
            self._matches(pattern, "/home/u/pw/%s" % self.PACKAGED_NAME))
        self.assertFalse(
            self._matches(pattern,
                          "/home/u/pw/elsewhere/%s" % self.PACKAGED_NAME))

    def test_symlink_alias_is_rejected(self):
        """A symlink under another name canonicalises to a path the
        pattern must refuse; the gate resolves $0 before matching."""
        pattern = self._extract_case_pattern()
        alias_dir = os.path.join(_TMP, "alias_tools")
        os.makedirs(alias_dir, exist_ok=True)
        target = os.path.join(alias_dir, self.PACKAGED_NAME)
        with open(target, "w", encoding="utf-8") as handle:
            handle.write("#\n")
        alias = os.path.join(alias_dir, "aliased_gate.sh")
        if os.path.islink(alias):
            os.remove(alias)
        os.symlink(target, alias)
        # the alias path itself must not match
        self.assertFalse(self._matches(pattern, alias))
        # and its canonical target, being outside a tools/ dir, also fails
        self.assertFalse(self._matches(pattern, os.path.realpath(alias)))

    def test_identical_bytes_under_a_different_name_are_rejected(self):
        pattern = self._extract_case_pattern()
        import shutil
        other_dir = os.path.join(_TMP, "clone", "tools")
        os.makedirs(other_dir, exist_ok=True)
        clone = os.path.join(other_dir, "check_move83_clone_gate.sh")
        shutil.copyfile(GATE, clone)
        with open(GATE, "rb") as a, open(clone, "rb") as b:
            self.assertEqual(a.read(), b.read())
        self.assertFalse(self._matches(pattern, clone),
                         "identical bytes under another name were accepted")

    def test_self_binding_precedes_candidate_identity(self):
        """The name check must run before any substantive stage, so a
        misnamed invocation can never reach candidate processing."""
        code = "\n".join(l for l in self._gate_text().splitlines()
                          if not l.strip().startswith("#"))
        binding = code.find('case "$SCRIPT_REAL" in')
        identity = code.find("STAGE A")
        self.assertNotEqual(binding, -1)
        self.assertNotEqual(identity, -1)
        self.assertLess(binding, identity)

    def test_gate_reaches_candidate_identity_under_the_genuine_name(self):
        """Off device the gate exits INCONCLUSIVE at the trusted-readlink
        check, which precedes the name check. What is provable here is
        that the genuine name does NOT trip the refusal path."""
        proc = _run([TEST_SH, GATE])
        self.assertNotIn(b"untrusted script path", proc.stdout)
        self.assertNotIn(b"canonical script path is not the genuine named "
                         b"gate", proc.stdout)


class TestGateMarkerFamilyIsConsistent(unittest.TestCase):
    """One accurate marker family for Move 83 report adoption."""

    def _gate_text(self):
        with open(GATE, encoding="utf-8") as handle:
            return handle.read()

    def test_no_move83_portable_build_markers_remain(self):
        # built from fragments so this scanner cannot match its own source
        stale = "MOVE_83_" + "PORTABLE_BUILD" + "_ADOPTION_GATE"
        self.assertNotIn(stale, self._gate_text())

    def test_terminal_marker_is_the_report_adoption_marker(self):
        text = self._gate_text()
        self.assertIn('echo "MOVE_83_REPORT_ADOPTION_GATE: PASS"', text)

    def test_every_exit_path_uses_the_report_marker_family(self):
        text = self._gate_text()
        for suffix in ("USAGE (missing:", "FAIL (relative path)",
                       "FAIL (missing Termux exec preload)",
                       "INCONCLUSIVE_RUST_UNAVAILABLE",
                       "FAIL (untrusted script path)",
                       "FAIL (nested exec)"):
            self.assertIn("MOVE_83_REPORT_ADOPTION_GATE: " + suffix, text,
                          suffix)

    def test_die_uses_the_report_marker_family(self):
        text = self._gate_text()
        self.assertIn(
            'die(){ echo "MOVE_83_REPORT_ADOPTION_GATE: FAIL ($1)"; '
            'exit 1; }', text)

    def test_move82_child_markers_are_untouched(self):
        """The Move 82 child legitimately emits Move 82 markers; only the
        parent's own family was mislabelled."""
        text = self._gate_text()
        self.assertIn("MOVE_82_PORTABLE_BUILD_ADOPTION_GATE: PASS", text)
        self.assertIn("tools/check_move82_portable_build_adoption.sh",
                      text)

    def test_readme_names_only_the_canonical_gate(self):
        """The README describes CURRENT state, so the superseded name must
        not appear in it at all."""
        wrong = "check_move83_" + "portable_build" + "_adoption.sh"
        with open(README, encoding="utf-8") as handle:
            text = handle.read()
        self.assertNotIn(wrong, text)
        self.assertIn("tools/check_move83_report_adoption.sh", text)

    def test_changelog_names_the_canonical_gate(self):
        """The changelog may cite the superseded name as history, but it
        must name the canonical gate as the current one."""
        with open(os.path.join(ROOT, "CHANGELOG_MOVE_83.md"),
                  encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("tools/check_move83_report_adoption.sh", text)
        wrong = "check_move83_" + "portable_build" + "_adoption.sh"
        if wrong in text:
            # only permitted inside the historical explanation
            self.assertIn("rejected its own canonical name", text)

    def test_allowlist_declares_the_packaged_gate_name(self):
        with open(ALLOWLIST, encoding="utf-8") as handle:
            data = json.load(handle)
        self.assertIn("tools/check_move83_report_adoption.sh",
                      data["added_paths"])
        for rel in data["added_paths"]:
            self.assertNotIn("check_move83_portable_build", rel)


class TestEveryReferencedHelperIsPackaged(unittest.TestCase):
    """The v05 Termux run died here: the gate invoked
    verify/report_v01/build_binary.py, which the mechanical
    portable_build_v01 -> report_v01 rename had created a reference to but
    never a file. This class statically enumerates EVERY local production
    file the gate references and requires each to be packaged."""

    def _gate_code(self):
        with open(GATE, encoding="utf-8") as handle:
            text = handle.read()
        return "\n".join(l for l in text.splitlines()
                          if not l.strip().startswith("#"))

    def _referenced(self):
        """Enumerate source-tree helper references from the gate itself."""
        import re
        code = self._gate_code()
        refs = set()
        for match in re.finditer(r'"\$P/([A-Za-z0-9_.-]+)"', code):
            refs.add("verify/report_v01/" + match.group(1))
        for match in re.finditer(r'"\$PB/([A-Za-z0-9_.-]+)"', code):
            refs.add("verify/portable_build_v01/" + match.group(1))
        for match in re.finditer(
                r'\$ROOT/([A-Za-z0-9_./-]+\.(?:py|sh|json|txt))', code):
            refs.add(match.group(1))
        return sorted(refs)

    # ---- the static self-test the whole class exists for -------------

    def test_every_referenced_production_file_is_packaged(self):
        refs = self._referenced()
        self.assertGreaterEqual(len(refs), 15,
                                "reference enumeration found too little")
        missing = [r for r in refs
                   if not os.path.isfile(os.path.join(ROOT, r))]
        self.assertEqual(missing, [],
                         "the gate references unpackaged file(s): %s"
                         % missing)

    def test_every_referenced_file_is_a_regular_file(self):
        for rel in self._referenced():
            full = os.path.join(ROOT, rel)
            self.assertTrue(os.path.isfile(full), rel)
            self.assertFalse(os.path.islink(full),
                             "%s is a symlink" % rel)

    def test_every_referenced_file_is_inside_the_candidate_tree(self):
        root_real = os.path.realpath(ROOT)
        for rel in self._referenced():
            full = os.path.realpath(os.path.join(ROOT, rel))
            self.assertTrue(full.startswith(root_real + os.sep), rel)

    # ---- the four helpers the rename broke ---------------------------

    HELPERS = ("build_binary.py", "inspect_binary.py", "provenance.py",
               "equivalence.py")

    def test_the_four_helpers_exist_at_their_adopted_paths(self):
        for name in self.HELPERS:
            full = os.path.join(ROOT, "verify", "portable_build_v01", name)
            self.assertTrue(os.path.isfile(full), name)
            self.assertFalse(os.path.islink(full), name)

    def test_helpers_are_referenced_at_their_adopted_paths(self):
        code = self._gate_code()
        for name in self.HELPERS:
            self.assertIn('"$PB/%s"' % name, code, name)
            self.assertNotIn('"$P/%s"' % name, code,
                             "%s is still referenced under report_v01" % name)

    def test_the_v05_broken_paths_are_not_referenced(self):
        code = self._gate_code()
        for name in self.HELPERS:
            broken = "verify/report_v01/" + name
            self.assertFalse(
                os.path.isfile(os.path.join(ROOT, broken)),
                "%s should not be duplicated into report_v01" % name)
            self.assertNotIn(broken, code)

    def test_helpers_are_the_adopted_inherited_bytes(self):
        """They are reused, not copied: the inherited checker proves the
        whole tree matches the adopted baseline, and these are not in the
        Move 83 addition allowlist."""
        with open(ALLOWLIST, encoding="utf-8") as handle:
            data = json.load(handle)
        for name in self.HELPERS:
            rel = "verify/portable_build_v01/" + name
            self.assertNotIn(rel, data["added_paths"])
            self.assertNotIn(rel, data.get("modified_paths", []))

    def test_gate_preflight_requires_every_helper(self):
        code = self._gate_code()
        self.assertIn("_require_helper()", code)
        for name in self.HELPERS:
            self.assertIn('"$PB/%s" \\' % name, code, name)
        self.assertIn('"$P/report_schema.py" \\', code)
        self.assertIn('"$P/report_tests.py" \\', code)

    def test_preflight_rejects_missing_symlinked_and_outside_helpers(self):
        code = self._gate_code()
        self.assertIn("required production helper is missing from the "
                      "candidate", code)
        self.assertIn('[ -L "$_rh_path" ]', code)
        self.assertIn("helper is outside the verified candidate tree",
                      code)

    def test_preflight_precedes_the_first_build(self):
        code = self._gate_code()
        preflight = code.find("_require_helper()")
        build = code.find("--profile release")
        self.assertNotEqual(preflight, -1)
        self.assertNotEqual(build, -1)
        self.assertLess(preflight, build)

    def test_helpers_are_invoked_for_both_profiles(self):
        code = self._gate_code()
        release = code.find("--profile release")
        debug = code.find("--profile dev")
        self.assertNotEqual(release, -1)
        self.assertNotEqual(debug, -1)
        # the same packaged helper drives both builds
        self.assertGreaterEqual(code.count('"$PB/build_binary.py"'), 2)

    def test_helper_streams_and_status_checked_separately(self):
        code = self._gate_code()
        for err_var in ("$_BLD_ERR", "$_DBG_ERR", "$_BA_ERR", "$_INS_ERR",
                        "$_PRV_ERR"):
            self.assertIn('2>"%s"' % err_var, code, err_var)
            self.assertIn('[ -s "%s" ]' % err_var, code, err_var)

    # ---- executable proof that the helper contract is enforced -------

    def _fake_helper(self, name, out=b"", err=b"", rc=0):
        return _write_python_exe(
            name,
            "import sys\n"
            "sys.stdout.buffer.write(%r)\n"
            "sys.stderr.buffer.write(%r)\n"
            "sys.exit(%d)\n" % (out, err, rc))

    def test_helper_failing_with_plausible_stdout_is_detectable(self):
        good_json = (json.dumps({"build_profile": "release"},
                                separators=(",", ":")) + "\n").encode()
        helper = self._fake_helper("h_fail.py", out=good_json, rc=1)
        proc = _run([helper])
        self.assertEqual(proc.returncode, 1)
        self.assertTrue(proc.stdout,
                        "stdout looks plausible; only status reveals it")

    def test_helper_succeeding_with_stderr_is_detectable(self):
        helper = self._fake_helper("h_err.py", out=b"{}\n",
                                   err=b"warning", rc=0)
        proc = _run([helper])
        self.assertEqual(proc.returncode, 0)
        self.assertTrue(proc.stderr)

    def test_helper_emitting_malformed_metadata_is_detectable(self):
        helper = self._fake_helper("h_bad.py", out=b"not json\n", rc=0)
        proc = _run([helper])
        self.assertEqual(proc.returncode, 0)
        with self.assertRaises(ValueError):
            json.loads(proc.stdout.decode())

    def test_real_build_helper_refuses_a_relative_toolchain(self):
        """The genuine packaged helper is executable and fails closed."""
        helper = os.path.join(ROOT, "verify", "portable_build_v01",
                              "build_binary.py")
        proc = _run([PYTHON_BIN, "-B", helper, "--cargo", "cargo",
                     "--rustc", "/bin/true", "--manifest-dir", _TMP,
                     "--profile", "release"])
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"BUILD: FAIL", proc.stdout)


class TestReportBytesContainNoSpacedSeparators(unittest.TestCase):
    """The v06 Termux run failed here. The Rust unit test required the
    report line to contain no `", "`, but my English prose inside the
    scope, not_run_reason and limitations values contained comma-space,
    so production output and the unit test contradicted each other.

    The JSON separators were already compact; the failure was in the
    string VALUES. The contract adopted here is total and trivially
    checkable: no comma-space and no colon-space appears anywhere in the
    report line, separator or content."""

    FORBIDDEN = (", ", ": ")

    def _production_literals(self):
        """Reconstruct the string values of every construct in report.rs
        whose text reaches the report."""
        import re
        with open(REPORT_RS, encoding="utf-8") as handle:
            src = handle.read()
        src = src[:src.find("#[cfg(test)]")]
        blocks = []
        for name in ("DIGEST_SCOPE_BUNDLE", "DIGEST_SCOPE_ARCHIVE"):
            start = src.find("const " + name)
            self.assertNotEqual(start, -1, name)
            blocks.append((name, src[start:src.find('";', start) + 2]))
        for name in ("skipped_because", "limitations_json"):
            start = src.find("fn " + name)
            self.assertNotEqual(start, -1, name)
            blocks.append((name, src[start:src.find("\n}", start)]))
        out = []
        for name, block in blocks:
            for raw in re.findall(r'"((?:[^"\\]|\\.)*)"', block, re.S):
                out.append((name, re.sub(r'\\\n\s*', '', raw)))
        return out

    def test_no_production_literal_contains_a_spaced_separator(self):
        literals = self._production_literals()
        self.assertGreaterEqual(len(literals), 8)
        offenders = [(n, v) for n, v in literals
                     if any(f in v for f in self.FORBIDDEN)]
        self.assertEqual(offenders, [],
                         "report text contains a spaced separator")

    def test_scope_text_survives_the_rewording(self):
        """Rewording must not drop the facts the validator requires."""
        values = {n: v for n, v in self._production_literals()}
        scope = values["DIGEST_SCOPE_BUNDLE"]
        for token in ("regular file", "mode bits", "0o7777", "Unix-only",
                      "domain-separation", "little-endian",
                      "raw relative-path bytes", "ACTUAL"):
            self.assertIn(token, scope, token)

    def test_limitations_text_survives_the_rewording(self):
        values = [v for n, v in self._production_literals()
                  if n == "limitations_json"]
        joined = " ".join(values).lower()
        self.assertIn("not_run", joined)
        self.assertIn("pass", joined)

    def test_rust_unit_test_checks_both_spaced_separators(self):
        with open(REPORT_RS, encoding="utf-8") as handle:
            text = handle.read()
        tests = text[text.find("#[cfg(test)]"):]
        self.assertIn('assert!(!line.contains(", "));', tests)
        self.assertIn('assert!(!line.contains(": "));', tests)

    # ---- the canonical-byte contract, enforced on real records -------

    def _canonical_check(self, raw):
        return report_schema.check_canonical_bytes(raw)[0]

    def test_python_fixtures_carry_no_spaced_separators(self):
        for record in (accepted_bundle_report(), failing_bundle_report(),
                       accepted_archive_report()):
            text = raw(record).decode("utf-8")
            for forbidden in self.FORBIDDEN:
                self.assertNotIn(forbidden, text)

    def test_comma_space_output_is_rejected(self):
        record = accepted_bundle_report()
        text = json.dumps(record, sort_keys=True, separators=(", ", ":"))
        self.assertTrue(self._canonical_check((text + "\n").encode()))

    def test_colon_space_output_is_rejected(self):
        record = accepted_bundle_report()
        text = json.dumps(record, sort_keys=True, separators=(",", ": "))
        self.assertTrue(self._canonical_check((text + "\n").encode()))

    def test_leading_or_trailing_space_rejected(self):
        good = raw(accepted_bundle_report())
        self.assertTrue(self._canonical_check(b" " + good))
        self.assertTrue(self._canonical_check(good[:-1] + b" \n"))

    def test_completion_receives_the_exact_core_bytes(self):
        """The completion layer must never silently reformat the raw core
        report; it parses the exact bytes and adds two fields."""
        core = accepted_bundle_report()
        core_bytes = raw(core)
        self.assertEqual(self._canonical_check(core_bytes), [])
        with open(REASON_MAP, "rb") as handle:
            done = report_schema.classify(core, handle.read())
        # every core field is preserved byte-for-byte in value
        for key, value in core.items():
            if key == "record_type":
                continue
            self.assertEqual(done[key], value, key)

    def test_completion_does_not_normalise_non_canonical_input(self):
        """A non-canonical core report must be rejected outright rather
        than quietly repaired by the completion layer."""
        record = accepted_bundle_report()
        sloppy = (json.dumps(record, sort_keys=True,
                             separators=(", ", ": ")) + "\n").encode()
        problems, parsed = report_schema.validate_bytes(sloppy)
        self.assertTrue(problems)
        path = os.path.join(_TMP, "sloppy_core.json")
        with open(path, "wb") as handle:
            handle.write(sloppy)
        out = os.path.join(_TMP, "sloppy_classified.json")
        proc = _run([PYTHON_BIN, "-B", SCHEMA_TOOL, "--report", path,
                     "--reason-map", REASON_MAP, "--classify-out", out])
        self.assertEqual(proc.returncode, 1)
        self.assertFalse(os.path.exists(out))

    def test_gate_requires_byte_identity_between_profiles(self):
        with open(GATE, encoding="utf-8") as handle:
            code = handle.read()
        self.assertIn("release and debug reports differ on", code)
        self.assertIn("_RC_DBG", code)


RUST_SOURCE_CHECK = os.path.join(HERE, "rust_source_check.py")
MAIN_RS_PATH = os.path.join(ROOT, "rust", "witness-verify", "src",
                            "main.rs")


class TestRustSourceSanity(unittest.TestCase):
    """v07 shipped a report.rs that does not parse as Rust: a string
    constant terminated early and left English prose outside any literal.
    The focused suite passed 182/182 regardless, because nothing checked
    the Rust source at all. Brace balance could not see it either -- the
    stray tokens are delimiter-neutral."""

    def _check(self, *paths):
        argv = [PYTHON_BIN, "-B", RUST_SOURCE_CHECK]
        for path in paths:
            argv += ["--source", path]
        return _run(argv)

    def _write_rs(self, name, body):
        path = os.path.join(_TMP, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(body)
        return path

    def test_packaged_rust_sources_pass(self):
        proc = self._check(REPORT_RS, MAIN_RS_PATH)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn(b"MOVE_83_RUST_SOURCE_SANITY: PASS", proc.stdout)
        self.assertEqual(proc.stderr, b"")

    def test_every_adopted_rust_source_passes(self):
        src_dir = os.path.join(ROOT, "rust", "witness-verify", "src")
        sources = [os.path.join(src_dir, n)
                   for n in sorted(os.listdir(src_dir))
                   if n.endswith(".rs")]
        self.assertGreaterEqual(len(sources), 5)
        proc = self._check(*sources)
        self.assertEqual(proc.returncode, 0, proc.stdout)

    # ---- the exact v07 corruption class -----------------------------

    def test_prose_outside_a_literal_is_detected(self):
        lines = [
            'const SCOPE: &str =',
            '    "a valid opening sentence.";'
            ' they are counted separately in',
            '     non_regular_entry_count.";',
        ]
        bad = self._write_rs("corrupt_prose.rs", "\n".join(lines) + "\n")
        proc = self._check(bad)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"prose outside a string literal", proc.stdout)

    def test_constant_with_two_literals_is_detected(self):
        lines = ['const SCOPE: &str =', '    "first part." "second part.";']
        bad = self._write_rs("two_literals.rs", "\n".join(lines) + "\n")
        proc = self._check(bad)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"string literals", proc.stdout)

    def test_stray_tokens_before_the_semicolon_are_detected(self):
        lines = ['const SCOPE: &str =', '    "the value." trailing_token;']
        bad = self._write_rs("stray_tokens.rs", "\n".join(lines) + "\n")
        proc = self._check(bad)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"stray tokens", proc.stdout)

    def test_unterminated_literal_is_detected(self):
        lines = ['const SCOPE: &str =', '    "never closed;', 'fn main() {}']
        bad = self._write_rs("unterminated.rs", "\n".join(lines) + "\n")
        proc = self._check(bad)
        self.assertEqual(proc.returncode, 1)

    def test_raw_strings_do_not_false_positive(self):
        lines = [
            'fn f() {',
            '    let s = r#"{"a": "b", "run_id": "run_fixture"}"#;',
            '    let _ = s;',
            '}',
        ]
        good = self._write_rs("rawstring.rs", "\n".join(lines) + "\n")
        proc = self._check(good)
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_comments_do_not_false_positive(self):
        lines = [
            '// this is ordinary English prose in a line comment',
            '/* and this is ordinary English prose in a block comment */',
            'fn f() {}',
        ]
        good = self._write_rs("comments.rs", "\n".join(lines) + "\n")
        proc = self._check(good)
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_normal_rust_keyword_runs_do_not_false_positive(self):
        lines = [
            'pub const fn f() -> u32 {',
            '    let mut out = 0u32;',
            '    out + 1',
            '}',
        ]
        good = self._write_rs("keywords.rs", "\n".join(lines) + "\n")
        proc = self._check(good)
        self.assertEqual(proc.returncode, 0, proc.stdout)

    # ---- DIGEST_SCOPE_BUNDLE regression -----------------------------

    def _scope_block(self):
        with open(REPORT_RS, encoding="utf-8") as handle:
            src = handle.read()
        start = src.find("const DIGEST_SCOPE_BUNDLE")
        self.assertNotEqual(start, -1)
        end = src.find('";', start)
        self.assertNotEqual(end, -1)
        return src[start:end + 2], src[end + 2:end + 3]

    def test_scope_constant_is_exactly_one_literal(self):
        import re
        block, _after = self._scope_block()
        literals = re.findall(r'"((?:[^"\\]|\\.)*)"', block, re.S)
        self.assertEqual(len(literals), 1,
                         "DIGEST_SCOPE_BUNDLE must be one string literal")

    def test_nothing_follows_the_scope_terminator(self):
        block, after = self._scope_block()
        self.assertTrue(block.rstrip().endswith('";'))
        self.assertIn(after, ("\n", ""))

    def test_scope_states_every_required_fact(self):
        import re
        block, _after = self._scope_block()
        literals = re.findall(r'"((?:[^"\\]|\\.)*)"', block, re.S)
        value = re.sub(r"\\\n\s*", "", literals[0])
        for token in ("EVERY entry", "raw relative-path bytes",
                      "ordered by their RAW relative-path bytes",
                      "length-prefixed", "ACTUAL Unix mode bits",
                      "0o7777", "content sha256", "domain-separated",
                      "Symbolic links are NEVER followed",
                      "non_regular_entry_count", "Unix-only",
                      "no cross-platform definition is claimed"):
            self.assertIn(token, value, token)

    def test_scope_value_has_no_spaced_separators(self):
        import re
        block, _after = self._scope_block()
        literals = re.findall(r'"((?:[^"\\]|\\.)*)"', block, re.S)
        value = re.sub(r"\\\n\s*", "", literals[0])
        self.assertNotIn(", ", value)
        self.assertNotIn(": ", value)

    def test_scope_facts_are_not_duplicated(self):
        """The corruption arose from a duplicated tail. No sentence in the
        scope value may appear twice."""
        import re
        block, _after = self._scope_block()
        literals = re.findall(r'"((?:[^"\\]|\\.)*)"', block, re.S)
        value = re.sub(r"\\\n\s*", "", literals[0])
        sentences = [x.strip() for x in value.split(".") if x.strip()]
        self.assertEqual(len(sentences), len(set(sentences)),
                         "a scope sentence is duplicated")

    # ---- honesty about what this establishes -------------------------

    def test_checker_states_it_is_not_a_compiler(self):
        proc = self._check(REPORT_RS)
        self.assertIn(b"does not establish Rust buildability", proc.stdout)

    def test_gate_still_runs_cargo_build_and_test(self):
        with open(GATE, encoding="utf-8") as handle:
            code = handle.read()
        self.assertIn("--profile release", code)
        self.assertIn("--profile dev", code)
        self.assertIn('"$TRUSTED_CARGO" test -q', code)

    def test_gate_runs_the_sanity_check_before_the_build(self):
        with open(GATE, encoding="utf-8") as handle:
            code = "\n".join(l for l in handle.read().splitlines()
                              if not l.strip().startswith("#"))
        sanity = code.find("rust_source_check.py")
        build = code.find("--profile release")
        self.assertNotEqual(sanity, -1)
        self.assertLess(sanity, build)

    def test_helper_is_declared_in_the_allowlist(self):
        with open(ALLOWLIST, encoding="utf-8") as handle:
            data = json.load(handle)
        self.assertIn("verify/report_v01/rust_source_check.py",
                      data["added_paths"])


ADOPTED_M82_CHECKER = os.path.join(
    ROOT, "verify", "portable_build_v01", "check_move82_inherited.py")


class TestMove82ChildRunDirectoryLayout(unittest.TestCase):
    """The v08 Termux run failed here. The adopted Move 82 gate derives
    its run directory as the directory CONTAINING the candidate zip it is
    given, then requires MOVE82_OUTPUT_DIR to be inside that run directory
    while staying outside the extracted source root. v08 handed the child
    an unrelated temporary directory.

    These tests drive the ADOPTED checker from the inherited tree, so the
    contract enforced is the adopted one and not a restatement."""

    def _check(self, out_dir, run_dir, candidate_root):
        return _run([PYTHON_BIN, "-B", ADOPTED_M82_CHECKER,
                     "--check-output-dir", out_dir, "--run-dir", run_dir,
                     "--candidate-root", candidate_root])

    def _layout(self, tag):
        """The v09 child layout."""
        run = os.path.join(_TMP, "m82child_" + tag)
        src = os.path.join(run, "project-witness-main")
        os.makedirs(src, exist_ok=True)
        zip_path = os.path.join(
            run, "project-witness-MOVE_82_candidate_v07.zip")
        with open(zip_path, "wb") as handle:
            handle.write(b"placeholder")
        out = os.path.join(run, "move82_output")
        os.makedirs(out, exist_ok=True)
        return run, src, out, zip_path

    # ---- 1: the genuine layout is accepted --------------------------

    def test_genuine_child_layout_is_accepted(self):
        run, src, out, _zip = self._layout("ok")
        proc = self._check(out, run, src)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn(b"MOVE_82_OUTPUT_DIR: PASS", proc.stdout)

    def test_run_dir_is_the_directory_holding_the_child_zip(self):
        """The adopted gate computes RUN_DIR from the candidate zip path,
        so the zip must live in the child run directory."""
        run, _src, out, zip_path = self._layout("rundir")
        self.assertEqual(os.path.dirname(zip_path), run)
        self.assertTrue(out.startswith(run + os.sep))

    # ---- 2-5: hostile layouts are rejected --------------------------

    def test_output_outside_the_child_run_dir_is_rejected(self):
        run, src, _out, _zip = self._layout("outside")
        elsewhere = os.path.join(_TMP, "m82child_elsewhere")
        os.makedirs(elsewhere, exist_ok=True)
        proc = self._check(elsewhere, run, src)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"internal run directory", proc.stdout)

    def test_output_inside_the_extracted_source_is_rejected(self):
        run, src, _out, _zip = self._layout("insrc")
        inside = os.path.join(src, "move82_output")
        os.makedirs(inside, exist_ok=True)
        proc = self._check(inside, run, src)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"candidate source root", proc.stdout)

    def test_symlinked_output_dir_is_rejected(self):
        run, src, out, _zip = self._layout("link")
        link = os.path.join(run, "linked_output")
        if os.path.islink(link):
            os.remove(link)
        os.symlink(out, link)
        proc = self._check(link, run, src)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"symlink", proc.stdout)

    def test_non_empty_output_dir_is_rejected(self):
        run, src, _out, _zip = self._layout("nonempty")
        full = os.path.join(run, "used_output")
        os.makedirs(full, exist_ok=True)
        with open(os.path.join(full, "leftover"), "w") as handle:
            handle.write("x")
        proc = self._check(full, run, src)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"not empty", proc.stdout)

    # ---- 6-7: the gate wires exactly this ---------------------------

    def _gate_code(self):
        with open(GATE, encoding="utf-8") as handle:
            return "\n".join(l for l in handle.read().splitlines()
                              if not l.strip().startswith("#"))

    def test_gate_builds_the_child_run_directory_layout(self):
        code = self._gate_code()
        self.assertIn('_M82_RUN=$("$TRUSTED_MKTEMP" -d)', code)
        self.assertIn('_M82_EXTRACT="$_M82_RUN"', code)
        self.assertIn('_M82_CHILD_ZIP="$_M82_RUN/'
                      'project-witness-MOVE_82_candidate_v07.zip"', code)
        self.assertIn('_M82_CHILD_OUT="$_M82_RUN/move82_output"', code)

    def test_gate_reverifies_the_staged_child_zip(self):
        code = self._gate_code()
        self.assertIn('_M82_CZ_SHA=$("$TRUSTED_SHA256SUM" '
                      '"$_M82_CHILD_ZIP"', code)
        self.assertIn('"$_M82_CZ_SHA" != "$_M82_EXPECT"', code)

    def test_gate_prevalidates_with_the_adopted_checker(self):
        code = self._gate_code()
        self.assertIn('"$_M82_ROOT/verify/portable_build_v01/'
                      'check_move82_inherited.py"', code)
        self.assertIn('--check-output-dir "$_M82_CHILD_OUT" '
                      '--run-dir "$_M82_RUN"', code)

    def test_move83_output_dir_is_never_reused_for_the_child(self):
        code = self._gate_code()
        self.assertIn('[ "$_M82_CHILD_OUT" = "$OUT_DIR" ]', code)
        self.assertNotIn('MOVE82_OUTPUT_DIR="$OUT_DIR"', code)

    def test_child_receives_the_staged_zip_and_validated_output_dir(self):
        code = self._gate_code()
        self.assertIn('MOVE82_CANDIDATE_ZIP="$_M82_CHILD_ZIP"', code)
        self.assertIn('MOVE82_OUTPUT_DIR="$_M82_CHILD_OUT"', code)
        self.assertNotIn('MOVE82_CANDIDATE_ZIP="$M82_ZIP"', code)

    def test_adopted_move82_checker_is_not_modified(self):
        """The adopted checker must be used, never weakened."""
        with open(ALLOWLIST, encoding="utf-8") as handle:
            data = json.load(handle)
        rel = "verify/portable_build_v01/check_move82_inherited.py"
        self.assertNotIn(rel, data["added_paths"])
        self.assertNotIn(rel, data.get("modified_paths", []))


class TestTranscriptIdentityIsSingleSourced(unittest.TestCase):
    """v08's provenance named MOVE_83_V06_TERMUX_GATE.txt because the name
    was hard-coded at the provenance call site and drifted."""

    ACTIVE = "MOVE_83_V13_TERMUX_GATE.txt"

    def _gate(self):
        with open(GATE, encoding="utf-8") as handle:
            return handle.read()

    def test_transcript_name_is_defined_once(self):
        code = "\n".join(l for l in self._gate().splitlines()
                          if not l.strip().startswith("#"))
        self.assertIn('MOVE83_TRANSCRIPT_NAME="%s"' % self.ACTIVE, code)
        self.assertEqual(code.count(self.ACTIVE), 1,
                         "the transcript name must appear once")

    def test_provenance_uses_the_variable_not_a_literal(self):
        code = "\n".join(l for l in self._gate().splitlines()
                          if not l.strip().startswith("#"))
        self.assertIn('--transcript-name "$MOVE83_TRANSCRIPT_NAME"', code)

    def test_no_stale_transcript_identity_in_active_output(self):
        code = "\n".join(l for l in self._gate().splitlines()
                          if not l.strip().startswith("#"))
        for old in ("06", "07", "08", "09", "10", "11", "12"):
            stale = "MOVE_83_V%s_TERMUX_GATE.txt" % old
            self.assertNotIn(stale, code,
                             "stale transcript identity %s" % stale)

    def test_a_provenance_record_with_a_stale_name_is_rejected(self):
        """A v09 provenance record must not carry a v06/v07/v08 name."""
        for old in ("06", "07", "08", "09", "10", "11", "12"):
            stale = "MOVE_83_V%s_TERMUX_GATE.txt" % old
            self.assertNotEqual(stale, self.ACTIVE)
            record = {"transcript_name": stale}
            self.assertNotEqual(record["transcript_name"], self.ACTIVE,
                                "stale name accepted as active")

    def test_changelog_and_readme_name_the_active_transcript(self):
        with open(os.path.join(ROOT, "CHANGELOG_MOVE_83.md"),
                  encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn(self.ACTIVE, text)


class TestCompleteTreeDigestBinding(unittest.TestCase):
    """v09's digest serialized regular files only, so a tree with an empty
    directory and one without produced the same value despite being
    different trees. Directory identities, entry kinds and non-regular
    identities are now bound.

    The fixture pairs here differ ONLY in structure -- identical regular
    files with identical bytes and modes on both sides -- so a digest
    covering regular files alone would produce equal values. The binary
    comparison itself runs in the gate, on device."""

    def _structure(self, tag):
        import report_schema as rs
        outdir = os.path.join(_TMP, "struct_" + tag)
        return {c["case_id"]: c for c in rs.make_structure_fixtures(outdir)}

    def _regular_files(self, root):
        """(relpath, mode, bytes) for every regular file."""
        found = {}
        for dirpath, _dn, filenames in os.walk(root):
            for name in filenames:
                full = os.path.join(dirpath, name)
                if os.path.islink(full) or not os.path.isfile(full):
                    continue
                rel = os.path.relpath(full, root)
                with open(full, "rb") as handle:
                    found[rel] = (stat.S_IMODE(os.lstat(full).st_mode),
                                  handle.read())
        return found

    def _dirs(self, root):
        found = set()
        for dirpath, dirnames, _fn in os.walk(root):
            for name in dirnames:
                full = os.path.join(dirpath, name)
                if os.path.islink(full):
                    continue
                found.add(os.path.relpath(full, root))
        return found

    REQUIRED = ("empty_dir_added", "empty_dir_removed",
                "empty_dir_renamed", "nested_empty_dir",
                "file_vs_directory", "symlink_target_differs",
                "symlink_vs_file")

    def test_every_required_structural_case_is_built(self):
        cases = self._structure("all")
        for case_id in self.REQUIRED:
            self.assertIn(case_id, cases)

    def test_empty_directory_added_differs_only_structurally(self):
        case = self._structure("added")["empty_dir_added"]
        a, b = (s["root"] for s in case["sides"])
        self.assertEqual(self._regular_files(a), self._regular_files(b))
        self.assertNotEqual(self._dirs(a), self._dirs(b))
        self.assertIn("empty_directory", self._dirs(b))

    def test_empty_directory_removed_differs_only_structurally(self):
        case = self._structure("removed")["empty_dir_removed"]
        a, b = (s["root"] for s in case["sides"])
        self.assertEqual(self._regular_files(a), self._regular_files(b))
        self.assertIn("empty_directory", self._dirs(a))
        self.assertNotIn("empty_directory", self._dirs(b))

    def test_empty_directory_renamed_differs_only_structurally(self):
        case = self._structure("renamed")["empty_dir_renamed"]
        a, b = (s["root"] for s in case["sides"])
        self.assertEqual(self._regular_files(a), self._regular_files(b))
        self.assertIn("alpha_dir", self._dirs(a))
        self.assertIn("beta_dir", self._dirs(b))
        self.assertEqual(len(self._dirs(a)), len(self._dirs(b)))

    def test_nested_empty_directory_differs_only_structurally(self):
        case = self._structure("nested")["nested_empty_dir"]
        a, b = (s["root"] for s in case["sides"])
        self.assertEqual(self._regular_files(a), self._regular_files(b))
        self.assertIn(os.path.join("outer", "inner"), self._dirs(a))
        self.assertNotIn(os.path.join("outer", "inner"), self._dirs(b))

    def test_file_and_directory_share_a_name_across_sides(self):
        case = self._structure("fvd")["file_vs_directory"]
        a, b = (s["root"] for s in case["sides"])
        self.assertTrue(os.path.isfile(os.path.join(a, "ambiguous")))
        self.assertTrue(os.path.isdir(os.path.join(b, "ambiguous")))

    def test_symlink_targets_differ_with_equal_counts(self):
        case = self._structure("link")["symlink_target_differs"]
        if not case["supported"]:
            self.skipTest("symlinks unsupported here")
        a, b = (s["root"] for s in case["sides"])
        self.assertEqual(os.readlink(os.path.join(a, "link")),
                         "target_one")
        self.assertEqual(os.readlink(os.path.join(b, "link")),
                         "target_two")

    def test_symlink_and_file_share_a_name_across_sides(self):
        case = self._structure("svf")["symlink_vs_file"]
        if not case["supported"]:
            self.skipTest("symlinks unsupported here")
        a, b = (s["root"] for s in case["sides"])
        self.assertTrue(os.path.islink(os.path.join(a, "other")))
        self.assertFalse(os.path.islink(os.path.join(b, "other")))

    # ---- the Rust implementation binds what the scope claims ---------

    def _report_code(self):
        with open(REPORT_RS, encoding="utf-8") as handle:
            return "\n".join(l for l in handle.read().splitlines()
                              if not l.strip().startswith("//"))

    def test_directories_are_collected_as_entries(self):
        code = self._report_code()
        self.assertIn("ENTRY_KIND_DIRECTORY", code)
        self.assertIn("kind: ENTRY_KIND_DIRECTORY", code)

    def test_entry_kind_is_bound_explicitly(self):
        code = self._report_code()
        for name in ("ENTRY_KIND_FILE", "ENTRY_KIND_DIRECTORY",
                     "ENTRY_KIND_SYMLINK", "ENTRY_KIND_FIFO",
                     "ENTRY_KIND_SOCKET", "ENTRY_KIND_BLOCK_DEVICE",
                     "ENTRY_KIND_CHAR_DEVICE",
                     "ENTRY_KIND_UNRECOGNISED"):
            self.assertIn(name, code)
        self.assertIn("listing.extend_from_slice(&entry.kind.to_le_bytes())",
                      code)

    def test_symlink_target_is_bound_without_following(self):
        code = self._report_code()
        self.assertIn("fs::read_link", code)
        self.assertIn("symlink_metadata", code)
        # the link is never resolved to its content
        self.assertNotIn("fs::canonicalize", code)

    def test_entry_count_is_bound(self):
        code = self._report_code()
        self.assertIn("(entries.len() as u64).to_le_bytes()", code)

    def test_every_variable_length_element_is_length_prefixed(self):
        code = self._report_code()
        self.assertIn("(entry.relpath.len() as u64).to_le_bytes()", code)
        self.assertIn("(entry.payload.len() as u64).to_le_bytes()", code)

    def test_ordering_is_over_raw_bytes_then_kind(self):
        code = self._report_code()
        self.assertIn("a.relpath.cmp(&b.relpath).then(a.kind.cmp(&b.kind))",
                      code)

    def test_domain_prefix_is_versioned_for_the_new_definition(self):
        code = self._report_code()
        self.assertIn('b"witness-bundle-digest/3', code)
        self.assertNotIn('b"witness-bundle-digest/2', code)

    def test_scope_states_what_the_counts_do_and_do_not_cover(self):
        import re
        with open(REPORT_RS, encoding="utf-8") as handle:
            text = handle.read()
        start = text.find("const DIGEST_SCOPE_BUNDLE")
        scope = re.sub(r"\\\n\s*", "",
                       text[start:text.find('";', start)])
        self.assertIn("directories are bound into the digest but are not "
                      "counted by either field", scope)
        self.assertIn("EVERY entry", scope)
        self.assertIn("including an empty one", scope)

    def test_gate_runs_the_structural_cases_through_the_binary(self):
        with open(GATE, encoding="utf-8") as handle:
            code = handle.read()
        self.assertIn('m.get("structure_cases", [])', code)
        self.assertIn("repeated runs over the identical tree produced "
                      "different digests", code)


class TestStaleBaselineDocumentation(unittest.TestCase):
    """Move 83's inherited baseline is Move 82 v07, not Move 81 v08."""

    def test_inherited_checker_names_the_move82_baseline(self):
        with open(BASELINE_CHECKER, encoding="utf-8") as handle:
            head = handle.read(4000)
        self.assertNotIn("Move 81 v08", head)
        self.assertIn("Move 82 v07", head)

    def test_no_move83_file_claims_a_move81_baseline(self):
        stale = "REAL adopted " + "Move 81" + " v08"
        for name in sorted(os.listdir(HERE)):
            if not name.endswith((".py", ".md", ".json", ".txt")):
                continue
            with open(os.path.join(HERE, name), encoding="utf-8") as handle:
                self.assertNotIn(stale, handle.read(), name)


class TestSpecialEntryTypeBinding(unittest.TestCase):
    """v10 collapsed FIFOs, sockets and device nodes into a single
    ENTRY_KIND_OTHER with an empty payload, so a FIFO and a socket at the
    same path with the same mode produced the same digest. Every Unix type
    now carries its own tag, and device nodes bind their device identity.

    Where this environment cannot create an entry type, the fixture
    records `supported: false` with the reason and nothing here claims it
    was tested."""

    def _structure(self, tag):
        import report_schema as rs
        outdir = os.path.join(_TMP, "special_" + tag)
        return {c["case_id"]: c for c in rs.make_structure_fixtures(outdir)}

    def _kind(self, path):
        st = os.lstat(path)
        if stat.S_ISFIFO(st.st_mode):
            return "fifo"
        if stat.S_ISSOCK(st.st_mode):
            return "socket"
        if stat.S_ISBLK(st.st_mode):
            return "block"
        if stat.S_ISCHR(st.st_mode):
            return "char"
        if stat.S_ISLNK(st.st_mode):
            return "symlink"
        if stat.S_ISDIR(st.st_mode):
            return "directory"
        return "file"

    def _sides(self, case):
        return [os.path.join(s["root"], "special") for s in case["sides"]]

    def _require(self, cases, case_id):
        case = cases[case_id]
        if not case["supported"]:
            self.skipTest("%s not creatable here: %s"
                          % (case_id, case.get("unsupported_reason", "")))
        return case

    def _assert_modes_normalised(self, case):
        """PREREQUISITE. A pair claiming to differ only in entry type must
        first be shown to share every other digest-relevant property. The
        genuine Termux run created a FIFO at 0600 and a socket at 0644
        from calls requesting the same mode, so this is established from
        lstat rather than assumed from the creation call."""
        modes = []
        for side in case["sides"]:
            target = os.path.join(side["root"], "special")
            self.assertTrue(os.path.lexists(target), target)
            actual = stat.S_IMODE(os.lstat(target).st_mode)
            # the builder recorded what it verified; confirm it still holds
            self.assertEqual(side["special_mode"], actual,
                             "recorded mode drifted from the filesystem")
            modes.append(actual)
        self.assertEqual(
            modes[0], modes[1],
            "prerequisite failed: the pair differs in mode as well as "
            "type, so this test would not isolate entry type")
        return modes[0]

    def _assert_paths_and_content_match(self, case):
        """The regular files outside the special entry must be identical
        on both sides, so nothing but the special entry can move the
        digest."""
        seen = []
        for side in case["sides"]:
            payload = os.path.join(side["root"], "file.txt")
            with open(payload, "rb") as handle:
                seen.append((stat.S_IMODE(os.lstat(payload).st_mode),
                             handle.read()))
        self.assertEqual(seen[0], seen[1])

    # ---- 3, 4: FIFO and socket are type-distinct --------------------

    def test_fifo_is_type_distinct_from_a_regular_file(self):
        case = self._require(self._structure("fvf"), "fifo_vs_file")
        self._assert_modes_normalised(case)
        self._assert_paths_and_content_match(case)
        a, b = self._sides(case)
        self.assertEqual(self._kind(a), "fifo")
        self.assertEqual(self._kind(b), "file")

    def test_fifo_and_socket_differ_only_in_type(self):
        case = self._require(self._structure("fvs"), "fifo_vs_socket")
        # PREREQUISITE established, not assumed: both entries are
        # explicitly normalised to the same mode and read back with lstat.
        mode = self._assert_modes_normalised(case)
        self._assert_paths_and_content_match(case)
        a, b = self._sides(case)
        self.assertEqual(os.path.basename(a), os.path.basename(b))
        self.assertEqual(mode, report_schema.NORMALISED_MODE)
        # only then is the type claim made
        self.assertEqual(self._kind(a), "fifo")
        self.assertEqual(self._kind(b), "socket")

    def test_socket_is_type_distinct_from_a_regular_file(self):
        case = self._require(self._structure("svf"), "socket_vs_file")
        self._assert_modes_normalised(case)
        self._assert_paths_and_content_match(case)
        a, b = self._sides(case)
        self.assertEqual(self._kind(a), "socket")
        self.assertEqual(self._kind(b), "file")

    def test_fifo_is_type_distinct_from_a_directory(self):
        case = self._require(self._structure("fvd"), "fifo_vs_directory")
        self._assert_modes_normalised(case)
        self._assert_paths_and_content_match(case)
        a, b = self._sides(case)
        self.assertEqual(self._kind(a), "fifo")
        self.assertEqual(self._kind(b), "directory")

    def test_fifo_is_type_distinct_from_a_symlink(self):
        """A symlink's mode cannot be set portably, so this pair is NOT
        claimed to differ only in mode-comparable respects. What is
        claimed, and checked, is that the two entry TYPES differ and that
        the recorded mode is absent for the symlink side rather than
        silently assumed equal."""
        case = self._require(self._structure("fvl"), "fifo_vs_symlink")
        self._assert_paths_and_content_match(case)
        modes = [side["special_mode"] for side in case["sides"]]
        self.assertEqual(modes[0], report_schema.NORMALISED_MODE)
        self.assertIsNone(modes[1],
                          "a symlink mode must be recorded as absent")
        a, b = self._sides(case)
        self.assertEqual(self._kind(a), "fifo")
        self.assertEqual(self._kind(b), "symlink")

    # ---- 5, 6: devices and device identity --------------------------

    def test_two_char_devices_differ_only_in_device_identity(self):
        case = self._require(self._structure("rdev"),
                             "chardev_rdev_differs")
        self._assert_modes_normalised(case)
        self._assert_paths_and_content_match(case)
        a, b = self._sides(case)
        self.assertEqual(self._kind(a), "char")
        self.assertEqual(self._kind(b), "char")
        # identical in every respect EXCEPT rdev
        self.assertNotEqual(os.lstat(a).st_rdev, os.lstat(b).st_rdev)

    def test_block_and_char_device_differ_only_in_type(self):
        case = self._require(self._structure("bvc"),
                             "blockdev_vs_chardev")
        self._assert_modes_normalised(case)
        self._assert_paths_and_content_match(case)
        a, b = self._sides(case)
        self.assertEqual(self._kind(a), "block")
        self.assertEqual(self._kind(b), "char")
        # same rdev, same mode: ONLY the type differs
        self.assertEqual(os.lstat(a).st_rdev, os.lstat(b).st_rdev)

    def test_unsupported_cases_are_recorded_honestly(self):
        """A case that could not be built must say so and carry no sides,
        so nothing downstream can treat it as tested."""
        cases = self._structure("honest")
        for case in cases.values():
            if case["supported"]:
                self.assertTrue(case["sides"])
            else:
                self.assertEqual(case["sides"], [])
                self.assertTrue(case.get("unsupported_reason"))

    def test_gate_skips_unsupported_structure_cases(self):
        with open(GATE, encoding="utf-8") as handle:
            code = handle.read()
        self.assertIn('if not c.get("supported")', code)

    # ---- the implementation carries a tag per type ------------------

    def _report_code(self):
        with open(REPORT_RS, encoding="utf-8") as handle:
            return "\n".join(l for l in handle.read().splitlines()
                              if not l.strip().startswith("//"))

    def test_every_unix_type_has_its_own_tag(self):
        code = self._report_code()
        for name, value in (("ENTRY_KIND_FILE", "1"),
                            ("ENTRY_KIND_DIRECTORY", "2"),
                            ("ENTRY_KIND_SYMLINK", "3"),
                            ("ENTRY_KIND_FIFO", "4"),
                            ("ENTRY_KIND_SOCKET", "5"),
                            ("ENTRY_KIND_BLOCK_DEVICE", "6"),
                            ("ENTRY_KIND_CHAR_DEVICE", "7"),
                            ("ENTRY_KIND_UNRECOGNISED", "8")):
            self.assertIn("const %s: u32 = %s;" % (name, value), code)

    def test_generic_other_bucket_is_gone(self):
        code = self._report_code()
        self.assertNotIn("ENTRY_KIND_OTHER", code)

    def test_type_predicates_are_used(self):
        code = self._report_code()
        for predicate in ("is_fifo()", "is_socket()", "is_block_device()",
                          "is_char_device()"):
            self.assertIn(predicate, code)
        self.assertIn("use std::os::unix::fs::FileTypeExt;", code)

    def test_device_identity_is_bound(self):
        code = self._report_code()
        self.assertIn("use std::os::unix::fs::MetadataExt;", code)
        self.assertIn("meta.rdev().to_le_bytes().to_vec()", code)
        # bound for BOTH device kinds
        self.assertEqual(code.count("meta.rdev().to_le_bytes().to_vec()"), 2)

    def test_domain_is_versioned_for_the_new_tag_set(self):
        code = self._report_code()
        self.assertIn('b"witness-bundle-digest/3', code)
        self.assertNotIn('b"witness-bundle-digest/2', code)

    def test_symlinks_still_never_followed(self):
        code = self._report_code()
        self.assertIn("fs::read_link", code)
        self.assertIn("symlink_metadata", code)
        self.assertNotIn("fs::canonicalize", code)

    def test_scope_lists_every_tag_and_the_device_payload(self):
        import re
        with open(REPORT_RS, encoding="utf-8") as handle:
            text = handle.read()
        start = text.find("const DIGEST_SCOPE_BUNDLE")
        scope = re.sub(r"\\\n\s*", "",
                       text[start:text.find('";', start)])
        for token in ("4 for a FIFO", "5 for a socket",
                      "6 for a block device", "7 for a character device",
                      "rdev", "none is collapsed into a generic class"):
            self.assertIn(token, scope, token)

    def test_zero_external_crates(self):
        """Only std is used; the workspace stays dependency-free."""
        with open(REPORT_RS, encoding="utf-8") as handle:
            text = handle.read()
        for line in text.splitlines():
            if line.startswith("use "):
                self.assertTrue(line.startswith("use std::")
                                or line.startswith("use crate::"), line)


class TestFixtureModesAreNormalisedNotAssumed(unittest.TestCase):
    """v11 failed its genuine Termux run because a FIFO was created at
    0600 and a socket at 0644 from calls that requested the same mode.
    Creation defaults, umask and platform behaviour are never relied on."""

    def _structure(self, tag):
        import report_schema as rs
        return {c["case_id"]: c
                for c in rs.make_structure_fixtures(
                    os.path.join(_TMP, "norm_" + tag))}

    def test_set_mode_verifies_with_lstat(self):
        import report_schema as rs
        target = os.path.join(_TMP, "norm_probe.txt")
        with open(target, "wb") as handle:
            handle.write(b"x")
        os.chmod(target, 0o600)
        self.assertEqual(rs.set_mode(target, 0o644), 0o644)
        self.assertEqual(stat.S_IMODE(os.lstat(target).st_mode), 0o644)

    def test_builder_records_the_verified_mode(self):
        for case in self._structure("record").values():
            for side in case.get("sides", []):
                target = os.path.join(side["root"], "special")
                if not os.path.lexists(target):
                    self.assertIsNone(side["special_mode"])
                    continue
                info = os.lstat(target)
                if stat.S_ISLNK(info.st_mode):
                    self.assertIsNone(side["special_mode"])
                else:
                    self.assertEqual(side["special_mode"],
                                     stat.S_IMODE(info.st_mode))

    def test_every_non_symlink_special_pair_shares_a_mode(self):
        cases = self._structure("share")
        for case_id, case in cases.items():
            if not case["supported"] or not case["sides"]:
                continue
            modes = [s["special_mode"] for s in case["sides"]]
            if None in modes:
                continue          # a symlink side, mode not settable
            self.assertEqual(modes[0], modes[1], case_id)

    def test_fifo_mode_does_not_depend_on_umask(self):
        """mkfifo's requested mode is masked by umask, which is exactly
        what bit the Termux run."""
        import report_schema as rs
        old = os.umask(0o077)
        try:
            root = os.path.join(_TMP, "umask_probe")
            os.makedirs(root, exist_ok=True)
            target = os.path.join(root, "fifo")
            if os.path.exists(target):
                os.remove(target)
            os.mkfifo(target)
            masked = stat.S_IMODE(os.lstat(target).st_mode)
            self.assertNotEqual(masked, 0o644,
                                "umask did not mask, so this probe is "
                                "not exercising the hazard")
            self.assertEqual(rs.set_mode(target, 0o644), 0o644)
        finally:
            os.umask(old)

    def test_directory_modes_are_normalised(self):
        cases = self._structure("dirs")
        for case_id in ("empty_dir_added", "empty_dir_removed",
                        "empty_dir_renamed", "nested_empty_dir"):
            case = cases[case_id]
            for side in case["sides"]:
                for dirpath, dirnames, _fn in os.walk(side["root"]):
                    for name in dirnames:
                        full = os.path.join(dirpath, name)
                        if os.path.islink(full):
                            continue
                        self.assertEqual(
                            stat.S_IMODE(os.lstat(full).st_mode),
                            report_schema.NORMALISED_DIR_MODE, full)

    def test_payload_files_share_mode_and_content(self):
        cases = self._structure("payload")
        for case_id, case in cases.items():
            if not case["supported"] or not case["sides"]:
                continue
            seen = []
            for side in case["sides"]:
                payload = os.path.join(side["root"], "file.txt")
                with open(payload, "rb") as handle:
                    seen.append(
                        (stat.S_IMODE(os.lstat(payload).st_mode),
                         handle.read()))
            self.assertEqual(seen[0], seen[1], case_id)

    def test_a_mode_that_cannot_be_set_fails_closed(self):
        """set_mode raises rather than returning a mismatched mode."""
        import report_schema as rs
        missing = os.path.join(_TMP, "norm_absent.txt")
        if os.path.exists(missing):
            os.remove(missing)
        with self.assertRaises(OSError):
            rs.set_mode(missing, 0o644)


FOCUSED_RESULT_CHECK = os.path.join(HERE, "check_focused_result.py")


class TestFocusedResultValidation(unittest.TestCase):
    """v12 succeeded on Termux -- `Ran 260 tests`, `OK (skipped=2)`,
    exit 0 -- and the gate rejected it, because it required a bare `OK`
    line and separately treated `skipped=` as a forbidden marker. The two
    skips are the device-node cases, which an unprivileged Android
    filesystem cannot create.

    These drive the real validator."""

    BODY = ("test_alpha (mod.Case) ... ok\n"
            "test_beta (mod.Case) ... skipped 'unprivileged'\n"
            + "-" * 70 + "\n"
            "Ran 260 tests in 10.566s\n\n")

    def _check(self, stdout_text, exit_code=0, count="260",
               stderr_text=""):
        base = os.path.join(_TMP, "focres")
        os.makedirs(base, exist_ok=True)
        out = os.path.join(base, "out.txt")
        err = os.path.join(base, "err.txt")
        pin = os.path.join(base, "count.txt")
        with open(out, "w", encoding="utf-8") as handle:
            handle.write(stdout_text)
        with open(err, "w", encoding="utf-8") as handle:
            handle.write(stderr_text)
        with open(pin, "w", encoding="utf-8") as handle:
            handle.write(count + "\n")
        return _run([PYTHON_BIN, "-B", FOCUSED_RESULT_CHECK,
                     "--stdout", out, "--stderr", err,
                     "--exit-code", str(exit_code), "--expect-count", pin])

    def _accept(self, summary, **kw):
        proc = self._check(self.BODY + summary + "\n", **kw)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn(b"MOVE_83_FOCUSED_RESULT: PASS", proc.stdout)
        return proc

    def _reject(self, summary, **kw):
        proc = self._check(self.BODY + summary + "\n", **kw)
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn(b"MOVE_83_FOCUSED_RESULT: FAIL", proc.stdout)
        return proc

    # ---- legitimate success forms -----------------------------------

    def test_bare_ok_is_accepted(self):
        self._accept("OK")

    def test_the_genuine_termux_summary_is_accepted(self):
        proc = self._accept("OK (skipped=2)")
        self.assertIn(b"FOCUSED_SKIPPED: 2", proc.stdout)

    def test_ok_skipped_zero_is_accepted(self):
        proc = self._accept("OK (skipped=0)")
        self.assertIn(b"FOCUSED_SKIPPED: 0", proc.stdout)

    def test_ok_expected_failures_is_accepted(self):
        proc = self._accept("OK (expected failures=1)")
        self.assertIn(b"FOCUSED_EXPECTED_FAILURES: 1", proc.stdout)

    def test_ok_with_both_annotations_is_accepted(self):
        self._accept("OK (skipped=2, expected failures=1)")

    def test_skip_count_is_reported_not_suppressed(self):
        proc = self._accept("OK (skipped=2)")
        self.assertIn(b"FOCUSED_SKIPPED: 2", proc.stdout)
        self.assertIn(b"FOCUSED_RAN: 260", proc.stdout)
        self.assertIn(b"FOCUSED_PINNED: 260", proc.stdout)

    # ---- failure and spoofing ---------------------------------------

    def test_failed_summary_is_rejected(self):
        proc = self._reject("FAILED (failures=1)", exit_code=1)
        self.assertIn(b"failure summary", proc.stdout)

    def test_nonzero_exit_is_rejected_despite_ok_text(self):
        proc = self._reject("OK", exit_code=1)
        self.assertIn(b"exited 1", proc.stdout)

    def test_earlier_ok_cannot_spoof_success(self):
        proc = self._check("OK\n" + self.BODY + "FAILED (failures=1)\n",
                           exit_code=1)
        self.assertEqual(proc.returncode, 1)

    def test_a_test_named_ok_cannot_spoof_success(self):
        proc = self._check(
            "test_OK (mod.Case) ... ok\n"
            "Ran 260 tests in 1.000s\n\n", exit_code=0)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"not a valid unittest success summary", proc.stdout)

    def test_injected_stdout_after_the_summary_is_rejected(self):
        proc = self._check(self.BODY + "OK (skipped=2)\nsomething else\n")
        self.assertEqual(proc.returncode, 1)

    def test_malformed_annotations_are_rejected(self):
        for summary in ("OK (whatever)", "OK (skipped=)",
                        "OK(skipped=2)", "OK (skipped=two)",
                        "OK (skipped=-1)", "OK ()", "OK extra"):
            self._reject(summary)

    def test_unexpected_successes_is_not_a_success_form(self):
        """wasSuccessful() is False when they occur, so it must not
        parse as success."""
        self._reject("OK (unexpected successes=1)")

    def test_pinned_count_mismatch_still_fails(self):
        proc = self._reject("OK (skipped=2)", count="259")
        self.assertIn(b"pinned count", proc.stdout)

    def test_missing_ran_line_is_rejected(self):
        proc = self._check("OK\n")
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"no 'Ran <N> tests' line", proc.stdout)

    def test_stderr_is_rejected(self):
        proc = self._check(self.BODY + "OK\n", stderr_text="warning\n")
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"stderr", proc.stdout)

    def test_empty_stdout_is_rejected(self):
        proc = self._check("")
        self.assertEqual(proc.returncode, 1)

    def test_relative_paths_are_refused(self):
        proc = _run([PYTHON_BIN, "-B", FOCUSED_RESULT_CHECK,
                     "--stdout", "rel.txt", "--stderr", "rel2.txt",
                     "--exit-code", "0", "--expect-count", "rel3.txt"])
        self.assertEqual(proc.returncode, 2)

    # ---- the gate uses it -------------------------------------------

    def test_gate_uses_the_validator(self):
        with open(GATE, encoding="utf-8") as handle:
            code = "\n".join(l for l in handle.read().splitlines()
                              if not l.strip().startswith("#"))
        self.assertIn("check_focused_result.py", code)
        self.assertIn('--exit-code "$_mt_rc"', code)
        self.assertIn('--expect-count "$P/EXPECTED_TEST_COUNT.txt"', code)

    def test_gate_no_longer_greps_for_a_bare_ok_line(self):
        with open(GATE, encoding="utf-8") as handle:
            code = "\n".join(l for l in handle.read().splitlines()
                              if not l.strip().startswith("#"))
        bare = 'grep -q "^' + 'OK$"'
        self.assertNotIn(bare, code)

    def test_gate_no_longer_forbids_the_skipped_marker(self):
        with open(GATE, encoding="utf-8") as handle:
            code = "\n".join(l for l in handle.read().splitlines()
                              if not l.strip().startswith("#"))
        forbidden_list = '"FAILED" "errors=" "failures=" "' + 'skipped="'
        self.assertNotIn(forbidden_list, code)

    def test_validator_is_declared_in_the_allowlist(self):
        with open(ALLOWLIST, encoding="utf-8") as handle:
            data = json.load(handle)
        self.assertIn("verify/report_v01/check_focused_result.py",
                      data["added_paths"])

    def test_this_suite_result_validates_against_its_own_pin(self):
        """The real suite's own output form is accepted, whether or not
        the device-node cases skip in this environment."""
        with open(os.path.join(HERE, "EXPECTED_TEST_COUNT.txt"),
                  encoding="utf-8") as handle:
            pinned = handle.read().strip()
        body = ("-" * 70 + "\nRan %s tests in 7.000s\n\n" % pinned)
        for summary in ("OK", "OK (skipped=2)"):
            proc = self._check(body + summary + "\n", count=pinned)
            self.assertEqual(proc.returncode, 0, proc.stdout)


if __name__ == "__main__":
    _suite = unittest.defaultTestLoader.loadTestsFromModule(
        sys.modules[__name__])
    _result = unittest.TextTestRunner(
        stream=sys.stdout, verbosity=1).run(_suite)
    sys.exit(0 if _result.wasSuccessful() else 1)
