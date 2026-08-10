"""Move 81 structured-verdict focused test suite.

Stdout-bound runner (unittest writes its summary to stderr by default; the
adoption gate treats focused-suite stderr as a pure warning/error channel,
so the runner streams to stdout). Pinned test count. Warning-clean.

Covers the ratified Move 81 test matrix: every schema field and allowed
value; canonical UTF-8 JSON with sorted keys, fixed separators, one
trailing newline; byte-identical repeated output; no absolute/temp paths,
timestamps, or random IDs; per-lane verdict normalization; Rust PASS
rejected as impossible; reason-map-derived stage; fail-closed conditions;
comparison statuses with both lane records preserved; no false merged
verdict; legacy output byte-for-byte unchanged.
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

import adapter  # noqa: E402
import schema  # noqa: E402

REASON_MAP = os.path.join(
    ROOT, "verify", "agreement_harness_v01", "reason_map.json")
PYTHON_ENTRY = os.path.join(
    ROOT, "src", "12_companion_cli_v031", "companion.py")
CLEAN_BUNDLE = os.path.join(
    ROOT, "freeze_record", "python_behaviour_freeze_v01", "reference_bundle")
ADAPTER = os.path.join(HERE, "adapter.py")


# ----------------------------------------------------------------------
# Target-portable executable resolution.
#
# The adopted Termux environment has no /bin/sh and no /usr/bin/env, so
# the suite must never assume desktop filesystem paths. Both the
# interpreter and the shell are resolved ONCE, HERE, at module import --
# which is strictly before any test installs a hostile PATH -- and are
# validated as absolute, regular, executable files.
#
# The production trust boundary is unchanged: the adoption gate supplies
# the exact trusted shell via MOVE81_TEST_SH (and the exact trusted
# Python, freshly built Rust binary, inherited Python entry, reason map
# and comparison contract to the adapter). Nothing in production code
# searches PATH.
# ----------------------------------------------------------------------

def _require_abs_exec(path, what):
    if not path:
        raise RuntimeError("%s could not be resolved" % what)
    if not os.path.isabs(path):
        raise RuntimeError("%s is not an absolute path: %r" % (what, path))
    if not os.path.isfile(path):
        raise RuntimeError("%s is not a regular file: %r" % (what, path))
    if not os.access(path, os.X_OK):
        raise RuntimeError("%s is not executable: %r" % (what, path))
    return path


# The exact interpreter executing this suite. Fixtures are generated with
# this absolute path as their shebang, so a directly executed fixture
# never searches PATH and never needs /usr/bin/env.
PYTHON_BIN = _require_abs_exec(
    os.path.realpath(sys.executable), "test interpreter (sys.executable)")


def _resolve_test_sh():
    """Resolve the shell used to invoke the real gate in tests.

    Under the adoption gate, MOVE81_TEST_SH carries the EXACT trusted
    shell and is required. Off device (hostile packaged-byte review only)
    a single explicit fallback resolves `sh` from PATH -- done here at
    import time, before any hostile PATH mutation exists -- then
    canonicalizes and validates it as an absolute executable."""
    supplied = os.environ.get("MOVE81_TEST_SH")
    if supplied:
        return _require_abs_exec(
            os.path.realpath(supplied), "MOVE81_TEST_SH (trusted shell)")
    import shutil as _shutil
    found = _shutil.which("sh")
    if not found:
        raise RuntimeError(
            "no shell available: set MOVE81_TEST_SH to the trusted shell")
    return _require_abs_exec(os.path.realpath(found), "fallback shell (sh)")


# Resolved ONCE at import, before any hostile PATH can be installed.
TEST_SH = _resolve_test_sh()

_TMP = None


def setUpModule():
    global _TMP
    import tempfile
    _TMP = tempfile.mkdtemp(prefix="m81_tests_")


def tearDownModule():
    import shutil
    if _TMP:
        shutil.rmtree(_TMP, ignore_errors=True)


def _write_exe(name, body):
    path = os.path.join(_TMP, name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(body)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP
             | stat.S_IXOTH)
    return path


def _write_python_exe(name, body):
    """Create a DIRECTLY EXECUTABLE Python fixture whose shebang is the
    exact resolved interpreter. The single helper every executable Python
    fixture goes through, so no fixture searches PATH or assumes
    /usr/bin/env exists."""
    return _write_exe(name, "#!%s\n%s" % (PYTHON_BIN, body))


def _write_sh_exe(name, body):
    """Create a directly executable shell fixture whose shebang is the
    exact resolved shell."""
    return _write_exe(name, "#!%s\n%s" % (TEST_SH, body))


def _fake_rust(name, stdout, exit_code, stderr=""):
    """A fake Rust-style binary emitting a fixed line and exit code.
    Directly executable via the exact interpreter shebang."""
    body = (
        "import sys\n"
        "sys.stdout.write(%r)\n"
        "sys.stderr.write(%r)\n"
        "sys.exit(%d)\n" % (stdout, stderr, exit_code))
    return _write_python_exe(name, body)


# Every test subprocess is BOUNDED. An unbounded subprocess.run would make
# a single hung child hang the whole one-process suite run, which is
# exactly the failure mode the adoption gate must never hit.
SUBPROCESS_TIMEOUT = 60


def _run_adapter(args, timeout=SUBPROCESS_TIMEOUT):
    """Run the adapter as a subprocess; return (rc, stdout_bytes,
    stderr_bytes). Always bounded by an explicit timeout."""
    proc = subprocess.run(
        [PYTHON_BIN, "-B", ADAPTER] + args, capture_output=True,
        timeout=timeout)
    return proc.returncode, proc.stdout, proc.stderr


# ----------------------------------------------------------------------
# Canonical encoding
# ----------------------------------------------------------------------

class TestCanonicalEncoding(unittest.TestCase):
    def test_sorted_keys_compact_separators_trailing_newline(self):
        obj = {"b": 1, "a": 2}
        raw = adapter.canonical_bytes(obj)
        self.assertEqual(raw, b'{"a":2,"b":1}\n')

    def test_utf8_and_single_object(self):
        rc, out, err = _run_adapter([
            "verdict", "--lane", "python_bundle", "--input", CLEAN_BUNDLE,
            "--reason-map", REASON_MAP, "--python-bin", PYTHON_BIN,
            "--python-entry", PYTHON_ENTRY])
        self.assertEqual(rc, 0)
        self.assertEqual(err, b"")
        # exactly one trailing newline; exactly one JSON object
        self.assertTrue(out.endswith(b"\n"))
        self.assertFalse(out.endswith(b"\n\n"))
        text = out.decode("utf-8")
        self.assertEqual(text.count("\n"), 1)
        obj = json.loads(text)
        self.assertIsInstance(obj, dict)
        # re-serialize canonically and require byte-identity
        self.assertEqual(adapter.canonical_bytes(obj), out)

    def test_repeated_output_byte_identical(self):
        args = ["verdict", "--lane", "python_bundle", "--input",
                CLEAN_BUNDLE, "--reason-map", REASON_MAP, "--python-bin",
                PYTHON_BIN, "--python-entry", PYTHON_ENTRY]
        _, out1, _ = _run_adapter(args)
        _, out2, _ = _run_adapter(args)
        self.assertEqual(out1, out2)

    def test_no_absolute_or_temp_paths_timestamps_random(self):
        _, out, _ = _run_adapter([
            "verdict", "--lane", "python_bundle", "--input", CLEAN_BUNDLE,
            "--reason-map", REASON_MAP, "--python-bin", PYTHON_BIN,
            "--python-entry", PYTHON_ENTRY])
        text = out.decode("utf-8")
        # the canonical record must not leak the input path or tmp
        self.assertNotIn(CLEAN_BUNDLE, text)
        self.assertNotIn("/tmp", text)
        self.assertNotIn(_TMP, text)


# ----------------------------------------------------------------------
# Schema fields / Python lane normalization
# ----------------------------------------------------------------------

class TestPythonLane(unittest.TestCase):
    def test_python_pass_all_fields(self):
        rc, out, err = _run_adapter([
            "verdict", "--lane", "python_bundle", "--input", CLEAN_BUNDLE,
            "--reason-map", REASON_MAP, "--python-bin", PYTHON_BIN,
            "--python-entry", PYTHON_ENTRY])
        self.assertEqual(rc, 0)
        obj = json.loads(out)
        self.assertEqual(obj["record_type"], "verdict")
        self.assertEqual(obj["schema_version"], "witness-verdict/1")
        self.assertEqual(obj["producer"],
                         "witness-structured-verdict-adapter")
        self.assertEqual(obj["producer_version"],
                         "0.0.1-step81-structured-verdict")
        self.assertEqual(obj["implementation_lane"], "python_bundle")
        self.assertEqual(obj["verifier"], "companion")
        self.assertEqual(obj["verifier_version"], "0.3.0")
        self.assertEqual(obj["operation"], "verify_bundle")
        self.assertEqual(obj["input_type"], "bundle_dir")
        self.assertEqual(obj["verdict"], "PASS")
        self.assertEqual(obj["reason_code"], "OK")
        self.assertEqual(obj["stage"], "complete")
        self.assertEqual(obj["capability_scope"],
                         "python_reference_pass_fail")
        self.assertEqual(obj["exit_code"], 0)

    def test_python_version_from_impl_not_bundle(self):
        # verifier_version must equal the implementation constant, and the
        # adapter must read it from the source tree, not the bundle.
        version = adapter.resolve_python_verifier_version(PYTHON_ENTRY)
        self.assertEqual(version, "0.3.0")

    def test_python_fail_normalization(self):
        # A fake python entry that reports verify_ok false with a mapped
        # reason, exit 1.
        fake = _write_exe(
            "fake_py_fail.py",
            "import json,sys\n"
            "print(json.dumps({'verify_ok': False,"
            " 'companion_status':'X',"
            " 'reason':'missing required file: foo'}))\n"
            "sys.exit(1)\n")
        rc, out, err = _run_adapter([
            "verdict", "--lane", "python_bundle", "--input", CLEAN_BUNDLE,
            "--reason-map", REASON_MAP, "--python-bin", PYTHON_BIN,
            "--python-entry", fake])
        self.assertEqual(rc, 1)
        obj = json.loads(out)
        self.assertEqual(obj["verdict"], "FAIL")
        self.assertEqual(obj["reason_code"], "REQUIRED_FILE_MISSING")
        self.assertEqual(obj["stage"], "manifest")
        self.assertEqual(obj["exit_code"], 1)

    def test_python_optional_version_when_absent(self):
        # A fake python entry whose sibling has no companion_lib/versions
        # -> verifier_version omitted, not "unknown", not a failure.
        subdir = os.path.join(_TMP, "noversion")
        os.makedirs(subdir, exist_ok=True)
        fake = os.path.join(subdir, "companion.py")
        with open(fake, "w", encoding="utf-8") as handle:
            handle.write(
                "import json,sys\n"
                "print(json.dumps({'verify_ok': True,"
                " 'companion_status':'COMPLETED',"
                " 'reason':'companion completed'}))\n"
                "sys.exit(0)\n")
        os.chmod(fake, 0o755)
        version = adapter.resolve_python_verifier_version(fake)
        self.assertIsNone(version)
        rc, out, err = _run_adapter([
            "verdict", "--lane", "python_bundle", "--input", CLEAN_BUNDLE,
            "--reason-map", REASON_MAP, "--python-bin", PYTHON_BIN,
            "--python-entry", fake])
        self.assertEqual(rc, 0)
        obj = json.loads(out)
        self.assertNotIn("verifier_version", obj)
        self.assertNotIn("unknown", json.dumps(obj).lower())


# ----------------------------------------------------------------------
# Rust lane / archive normalization
# ----------------------------------------------------------------------

_RUST_INCONCLUSIVE = (
    '{"verifier": "witness-verify", "version": "0.0.8-step79-diagnostics",'
    ' "verdict": "INCONCLUSIVE", "reason_code":'
    ' "RECEIPT_CHAIN_HASHES_RECOMPUTED", "detail": "ok"}')
_RUST_FAIL = (
    '{"verifier": "witness-verify", "version": "0.0.8-step79-diagnostics",'
    ' "verdict": "FAIL", "reason_code":'
    ' "RECEIPT_HASH_RECOMPUTATION_MISMATCH", "detail": "bad"}')
_ARCHIVE_INCONCLUSIVE = (
    '{"verifier": "witness-verify", "version": "0.0.8-step79-diagnostics",'
    ' "verdict": "INCONCLUSIVE", "reason_code": "ARCHIVE_SAFETY_OK",'
    ' "detail": "ok", "entry_count": 3}')
_ARCHIVE_FAIL = (
    '{"verifier": "witness-verify", "version": "0.0.8-step79-diagnostics",'
    ' "verdict": "FAIL", "reason_code": "ARCHIVE_PATH_TRAVERSAL",'
    ' "detail": "traversal"}')


class TestRustLane(unittest.TestCase):
    def _bundle(self):
        d = os.path.join(_TMP, "rbundle")
        os.makedirs(d, exist_ok=True)
        return d

    def test_rust_inconclusive(self):
        rb = _fake_rust("fr_inc.py", _RUST_INCONCLUSIVE + "\n", 3)
        rc, out, err = _run_adapter([
            "verdict", "--lane", "rust_bundle", "--input", self._bundle(),
            "--reason-map", REASON_MAP, "--rust-bin", rb])
        self.assertEqual(rc, 3)
        obj = json.loads(out)
        self.assertEqual(obj["verdict"], "INCONCLUSIVE")
        self.assertEqual(obj["exit_code"], 3)
        self.assertEqual(obj["capability_scope"], "rust_read_only_no_pass")
        self.assertEqual(obj["verifier_version"],
                         "0.0.8-step79-diagnostics")
        self.assertEqual(obj["stage"], "complete")

    def test_rust_fail(self):
        rb = _fake_rust("fr_fail.py", _RUST_FAIL + "\n", 1)
        rc, out, err = _run_adapter([
            "verdict", "--lane", "rust_bundle", "--input", self._bundle(),
            "--reason-map", REASON_MAP, "--rust-bin", rb])
        self.assertEqual(rc, 1)
        obj = json.loads(out)
        self.assertEqual(obj["verdict"], "FAIL")
        self.assertEqual(obj["exit_code"], 1)

    def test_rust_pass_rejected_as_impossible(self):
        pass_line = _RUST_INCONCLUSIVE.replace("INCONCLUSIVE", "PASS")
        rb = _fake_rust("fr_pass.py", pass_line + "\n", 0)
        rc, out, err = _run_adapter([
            "verdict", "--lane", "rust_bundle", "--input", self._bundle(),
            "--reason-map", REASON_MAP, "--rust-bin", rb])
        self.assertEqual(rc, schema.MEASUREMENT_ERROR_EXIT)
        obj = json.loads(out)
        self.assertEqual(obj["record_type"], "measurement_error")
        self.assertEqual(obj["measurement_error_code"],
                         "ADAPTER_IMPOSSIBLE_VERDICT_EXIT_PAIR")
        self.assertNotIn("verdict", obj)

    def test_archive_inconclusive(self):
        rb = _fake_rust("fa_inc.py", _ARCHIVE_INCONCLUSIVE + "\n", 3)
        z = os.path.join(_TMP, "a.zip")
        with open(z, "wb") as h:
            h.write(b"PK\x03\x04")
        rc, out, err = _run_adapter([
            "verdict", "--lane", "archive", "--input", z,
            "--reason-map", REASON_MAP, "--rust-bin", rb])
        self.assertEqual(rc, 3)
        obj = json.loads(out)
        self.assertEqual(obj["verdict"], "INCONCLUSIVE")
        self.assertEqual(obj["operation"], "inspect_archive")
        self.assertEqual(obj["input_type"], "archive_zip")
        self.assertEqual(obj["capability_scope"], "archive_safety_only")

    def test_archive_fail(self):
        rb = _fake_rust("fa_fail.py", _ARCHIVE_FAIL + "\n", 1)
        z = os.path.join(_TMP, "b.zip")
        with open(z, "wb") as h:
            h.write(b"PK\x03\x04")
        rc, out, err = _run_adapter([
            "verdict", "--lane", "archive", "--input", z,
            "--reason-map", REASON_MAP, "--rust-bin", rb])
        self.assertEqual(rc, 1)
        obj = json.loads(out)
        self.assertEqual(obj["verdict"], "FAIL")


# ----------------------------------------------------------------------
# Fail-closed conditions (each -> measurement_error, exit 1, no verdict)
# ----------------------------------------------------------------------

class TestFailClosed(unittest.TestCase):
    def _bundle(self):
        d = os.path.join(_TMP, "fcbundle")
        os.makedirs(d, exist_ok=True)
        return d

    def _expect_measurement_error(self, rust_stdout, exit_code, code,
                                  stderr=""):
        rb = _fake_rust("fc_%s.py" % code, rust_stdout, exit_code, stderr)
        rc, out, err = _run_adapter([
            "verdict", "--lane", "rust_bundle", "--input", self._bundle(),
            "--reason-map", REASON_MAP, "--rust-bin", rb])
        self.assertEqual(rc, schema.MEASUREMENT_ERROR_EXIT)
        obj = json.loads(out)
        self.assertEqual(obj["record_type"], "measurement_error")
        self.assertEqual(obj["measurement_error_code"], code)
        self.assertNotIn("verdict", obj)
        self.assertNotIn("reason_code", obj)
        self.assertNotIn("stage", obj)
        return obj

    def test_malformed_json(self):
        self._expect_measurement_error(
            "{not json\n", 3, "ADAPTER_MALFORMED_JSON")

    def test_multiple_objects(self):
        self._expect_measurement_error(
            _RUST_INCONCLUSIVE + "\n" + _RUST_FAIL + "\n", 3,
            "ADAPTER_MULTIPLE_OBJECTS")

    def test_stdout_prefix_contamination(self):
        self._expect_measurement_error(
            "PROGRESS\n" + _RUST_INCONCLUSIVE + "\n", 3,
            "ADAPTER_STDOUT_CONTAMINATION")

    def test_stdout_suffix_contamination(self):
        # trailing non-JSON text after the object (and its newline) is
        # contamination, not a second object.
        self._expect_measurement_error(
            _RUST_INCONCLUSIVE + "\nTRAILING\n", 3,
            "ADAPTER_STDOUT_CONTAMINATION")

    def test_stdout_second_object(self):
        # a genuine second JSON object is MULTIPLE_OBJECTS.
        self._expect_measurement_error(
            _RUST_INCONCLUSIVE + "\n" + _RUST_FAIL + "\n", 3,
            "ADAPTER_MULTIPLE_OBJECTS")

    def test_unexpected_stderr_python(self):
        # python lane requires empty stderr
        fake = _write_exe(
            "fc_pyerr.py",
            "import json,sys\n"
            "sys.stderr.write('noise')\n"
            "print(json.dumps({'verify_ok': True,"
            " 'companion_status':'C','reason':'companion completed'}))\n"
            "sys.exit(0)\n")
        rc, out, err = _run_adapter([
            "verdict", "--lane", "python_bundle", "--input", CLEAN_BUNDLE,
            "--reason-map", REASON_MAP, "--python-bin", PYTHON_BIN,
            "--python-entry", fake])
        self.assertEqual(rc, schema.MEASUREMENT_ERROR_EXIT)
        obj = json.loads(out)
        self.assertEqual(obj["measurement_error_code"],
                         "ADAPTER_UNEXPECTED_STDERR")

    def test_impossible_verdict_exit_pair(self):
        # FAIL verdict but exit 3 -> impossible pairing
        self._expect_measurement_error(
            _RUST_FAIL + "\n", 3, "ADAPTER_IMPOSSIBLE_VERDICT_EXIT_PAIR")

    def test_exit_2_invocation_error(self):
        self._expect_measurement_error(
            _RUST_INCONCLUSIVE + "\n", 2, "ADAPTER_INVOCATION_ERROR")

    def test_unknown_reason(self):
        line = _RUST_FAIL.replace("RECEIPT_HASH_RECOMPUTATION_MISMATCH",
                                  "NOT_A_REAL_REASON_CODE_XYZ")
        self._expect_measurement_error(
            line + "\n", 1, "ADAPTER_UNKNOWN_REASON")

    def test_incomplete_result_empty_stdout(self):
        self._expect_measurement_error("", 3, "ADAPTER_INCOMPLETE_RESULT")

    def test_timeout(self):
        slow = _write_python_exe(
            "fc_slow.py", "import time\ntime.sleep(2)\n")
        rc, out, err = _run_adapter([
            "verdict", "--lane", "rust_bundle", "--input", self._bundle(),
            "--reason-map", REASON_MAP, "--rust-bin", slow,
            "--timeout", "1"])
        self.assertEqual(rc, schema.MEASUREMENT_ERROR_EXIT)
        obj = json.loads(out)
        self.assertEqual(obj["measurement_error_code"], "ADAPTER_TIMEOUT")

    def test_signal_termination(self):
        killer = _write_python_exe(
            "fc_kill.py",
            "import os,signal\nos.kill(os.getpid(), signal.SIGKILL)\n")
        rc, out, err = _run_adapter([
            "verdict", "--lane", "rust_bundle", "--input", self._bundle(),
            "--reason-map", REASON_MAP, "--rust-bin", killer])
        self.assertEqual(rc, schema.MEASUREMENT_ERROR_EXIT)
        obj = json.loads(out)
        self.assertEqual(obj["measurement_error_code"],
                         "ADAPTER_SIGNAL_TERMINATION")
        # A negative subprocess return code is SIGNAL METADATA, not a
        # normal process exit code: exit_code must be omitted entirely.
        self.assertNotIn("exit_code", obj)

    def test_absent_executable_is_usage_error(self):
        # a nonexistent --rust-bin path is adapter CLI misuse -> exit 2,
        # no record emitted (path validation happens before invocation)
        missing = os.path.join(_TMP, "does_not_exist_bin")
        rc, out, err = _run_adapter([
            "verdict", "--lane", "rust_bundle", "--input", self._bundle(),
            "--reason-map", REASON_MAP, "--rust-bin", missing])
        self.assertEqual(rc, schema.USAGE_EXIT)
        self.assertEqual(out, b"")

    def test_stageless_entry_rejected_at_load_before_any_verifier_runs(self):
        # A stageless entry is now caught by reason-map validation BEFORE
        # any verifier is invoked: adapter usage error, exit 2, no record,
        # no traceback. This is strictly earlier and stricter than the
        # previous runtime-only detection.
        import copy
        with open(REASON_MAP, encoding="utf-8") as h:
            rm = json.load(h)
        rm2 = copy.deepcopy(rm)
        rm2["rust_bundle"].insert(0, {
            "class": "SOME_CLASS", "match_type": "exact",
            "value": "STAGELESS_REASON", "stage": ""})
        rm2_path = os.path.join(_TMP, "rm_nostage.json")
        with open(rm2_path, "w", encoding="utf-8") as h:
            json.dump(rm2, h)
        line = _RUST_FAIL.replace("RECEIPT_HASH_RECOMPUTATION_MISMATCH",
                                  "STAGELESS_REASON")
        rb = _fake_rust("fc_nostage.py", line + "\n", 1)
        rc, out, err = _run_adapter([
            "verdict", "--lane", "rust_bundle", "--input", self._bundle(),
            "--reason-map", rm2_path, "--rust-bin", rb])
        self.assertEqual(rc, schema.USAGE_EXIT)
        self.assertEqual(out, b"")
        self.assertNotIn(b"Traceback", err)

    def test_missing_stage_mapping_guard_still_fails_closed(self):
        # ADAPTER_MISSING_STAGE_MAPPING remains a defensive guard inside
        # the resolver. Exercised directly with an in-memory map, since a
        # map that reaches the resolver has already passed validation.
        crafted = {"rust_bundle": [
            {"class": "SOME_CLASS", "match_type": "exact",
             "value": "STAGELESS_REASON", "stage": ""}]}
        with self.assertRaises(adapter.AdapterMeasurementError) as ctx:
            adapter._resolve_reason_and_stage(
                crafted, "rust_bundle", "STAGELESS_REASON")
        self.assertEqual(ctx.exception.code,
                         "ADAPTER_MISSING_STAGE_MAPPING")

    def test_unknown_reason_guard_still_fails_closed(self):
        crafted = {"rust_bundle": [
            {"class": "SOME_CLASS", "match_type": "exact",
             "value": "KNOWN_ONE", "stage": "manifest"}]}
        with self.assertRaises(adapter.AdapterMeasurementError) as ctx:
            adapter._resolve_reason_and_stage(
                crafted, "rust_bundle", "SOMETHING_ELSE")
        self.assertEqual(ctx.exception.code, "ADAPTER_UNKNOWN_REASON")

    def test_verifier_identity_mismatch(self):
        # a rust line that does not self-identify as witness-verify
        line = _RUST_INCONCLUSIVE.replace('"witness-verify"', '"impostor"')
        self._expect_measurement_error(
            line + "\n", 3, "ADAPTER_VERIFIER_IDENTITY_MISMATCH")

    def test_verifier_identity_absent(self):
        # a rust line with no verifier field at all
        line = ('{"version": "0.0.8-step79-diagnostics",'
                ' "verdict": "INCONCLUSIVE",'
                ' "reason_code": "RECEIPT_CHAIN_HASHES_RECOMPUTED"}')
        self._expect_measurement_error(
            line + "\n", 3, "ADAPTER_VERIFIER_IDENTITY_MISMATCH")


class TestInputTypeValidation(unittest.TestCase):
    def test_bundle_lane_rejects_file_input(self):
        f = os.path.join(_TMP, "afile.txt")
        with open(f, "w") as h:
            h.write("x")
        rb = _fake_rust("itv_r.py", _RUST_INCONCLUSIVE + "\n", 3)
        rc, out, err = _run_adapter([
            "verdict", "--lane", "rust_bundle", "--input", f,
            "--reason-map", REASON_MAP, "--rust-bin", rb])
        self.assertEqual(rc, 2)
        self.assertEqual(out, b"")

    def test_archive_lane_rejects_directory_input(self):
        d = os.path.join(_TMP, "adir")
        os.makedirs(d, exist_ok=True)
        rb = _fake_rust("itv_a.py", _ARCHIVE_INCONCLUSIVE + "\n", 3)
        rc, out, err = _run_adapter([
            "verdict", "--lane", "archive", "--input", d,
            "--reason-map", REASON_MAP, "--rust-bin", rb])
        self.assertEqual(rc, 2)
        self.assertEqual(out, b"")

    def test_python_lane_rejects_file_input(self):
        f = os.path.join(_TMP, "afile2.txt")
        with open(f, "w") as h:
            h.write("x")
        rc, out, err = _run_adapter([
            "verdict", "--lane", "python_bundle", "--input", f,
            "--reason-map", REASON_MAP, "--python-bin", PYTHON_BIN,
            "--python-entry", PYTHON_ENTRY])
        self.assertEqual(rc, 2)
        self.assertEqual(out, b"")


class TestPythonErrorForm(unittest.TestCase):
    def test_python_fail_error_form_normalized(self):
        # A Python FAIL that reports its cause under "error" (not
        # "reason") must normalize via the adopted error-first rule.
        fake = _write_exe(
            "pef_fail.py",
            "import json,sys\n"
            "print(json.dumps({'verify_ok': False,"
            " 'error':'missing required file: foo'}))\n"
            "sys.exit(1)\n")
        rc, out, err = _run_adapter([
            "verdict", "--lane", "python_bundle", "--input", CLEAN_BUNDLE,
            "--reason-map", REASON_MAP, "--python-bin", PYTHON_BIN,
            "--python-entry", fake])
        self.assertEqual(rc, 1)
        obj = json.loads(out)
        self.assertEqual(obj["verdict"], "FAIL")
        self.assertEqual(obj["reason_code"], "REQUIRED_FILE_MISSING")
        self.assertEqual(obj["stage"], "manifest")
        # detail preserves the original text (safe: no path chars? it has
        # a colon and space only -> safe)
        self.assertEqual(obj.get("detail"), "missing required file: foo")

    def test_python_empty_reason_fails_closed(self):
        fake = _write_exe(
            "pef_empty.py",
            "import json,sys\n"
            "print(json.dumps({'verify_ok': False, 'reason':''}))\n"
            "sys.exit(1)\n")
        rc, out, err = _run_adapter([
            "verdict", "--lane", "python_bundle", "--input", CLEAN_BUNDLE,
            "--reason-map", REASON_MAP, "--python-bin", PYTHON_BIN,
            "--python-entry", fake])
        self.assertEqual(rc, schema.MEASUREMENT_ERROR_EXIT)
        obj = json.loads(out)
        self.assertEqual(obj["measurement_error_code"],
                         "ADAPTER_INCOMPLETE_RESULT")


# ----------------------------------------------------------------------
# Adapter CLI misuse (exit 2, no record)
# ----------------------------------------------------------------------

class TestAdapterUsage(unittest.TestCase):
    def test_no_args_exit_2_no_record(self):
        rc, out, err = _run_adapter([])
        self.assertEqual(rc, 2)
        self.assertEqual(out, b"")
        self.assertTrue(err)

    def test_relative_path_rejected(self):
        rc, out, err = _run_adapter([
            "verdict", "--lane", "python_bundle", "--input",
            "relative/bundle", "--reason-map", REASON_MAP,
            "--python-bin", PYTHON_BIN, "--python-entry", PYTHON_ENTRY])
        self.assertEqual(rc, 2)
        self.assertEqual(out, b"")

    def test_unknown_argument_rejected(self):
        rc, out, err = _run_adapter(["verdict", "--bogus", "x"])
        self.assertEqual(rc, 2)
        self.assertEqual(out, b"")

    def test_missing_reason_map_rejected(self):
        rc, out, err = _run_adapter([
            "verdict", "--lane", "python_bundle", "--input", CLEAN_BUNDLE,
            "--python-bin", PYTHON_BIN, "--python-entry", PYTHON_ENTRY])
        self.assertEqual(rc, 2)
        self.assertEqual(out, b"")

    def test_nonregular_reason_map_rejected(self):
        rc, out, err = _run_adapter([
            "verdict", "--lane", "python_bundle", "--input", CLEAN_BUNDLE,
            "--reason-map", _TMP, "--python-bin", PYTHON_BIN,
            "--python-entry", PYTHON_ENTRY])
        self.assertEqual(rc, 2)
        self.assertEqual(out, b"")


# ----------------------------------------------------------------------
# Comparison
# ----------------------------------------------------------------------

class TestComparison(unittest.TestCase):
    CONTRACT = os.path.join(
        ROOT, "verify", "agreement_harness_v01", "corpus",
        "bundle_cases.json")

    def _compare(self, py_entry, rust_bin, case_id, bundle=None):
        return _run_adapter([
            "compare", "--input", bundle or CLEAN_BUNDLE,
            "--reason-map", REASON_MAP, "--python-bin", PYTHON_BIN,
            "--python-entry", py_entry, "--rust-bin", rust_bin,
            "--case-id", case_id, "--comparison-contract", self.CONTRACT])

    def _rust(self, name, verdict, reason_code, exit_code):
        line = (
            '{"verifier": "witness-verify",'
            ' "version": "0.0.8-step79-diagnostics",'
            ' "verdict": "%s", "reason_code": "%s", "detail": "d"}'
            % (verdict, reason_code))
        return _fake_rust(name, line + "\n", exit_code)

    def test_agreement_clean_control(self):
        # real Python PASS/0 + Rust INCONCLUSIVE/3 matching the frozen
        # clean_control expected -> AGREEMENT, exit 0
        rust = self._rust("cmp_clean.py", "INCONCLUSIVE",
                          "RECEIPT_CHAIN_HASHES_RECOMPUTED", 3)
        rc, out, err = self._compare(PYTHON_ENTRY, rust, "clean_control")
        obj = json.loads(out)
        self.assertEqual(obj["record_type"], "comparison")
        self.assertEqual(obj["comparison_status"], "AGREEMENT")
        self.assertEqual(rc, 0)
        self.assertEqual(obj["case_id"], "clean_control")
        # both complete lane records preserved
        self.assertEqual(obj["python_lane"]["verdict"], "PASS")
        self.assertEqual(obj["rust_lane"]["verdict"], "INCONCLUSIVE")
        self.assertNotIn(obj["comparison_status"],
                         ("PASS", "FAIL", "INCONCLUSIVE"))

    def test_declared_divergence(self):
        # stage_manifest_json_invalid: python FAIL/1 REPORT_NOT_CANONICAL@
        # canonical_report, rust FAIL/1 MANIFEST_MALFORMED@manifest.
        py = _write_exe(
            "cmp_py_div.py",
            "import json,sys\n"
            "print(json.dumps({'verify_ok': False,"
            " 'companion_status':'C',"
            " 'error':'companion_report not canonical'}))\n"
            "sys.exit(1)\n")
        # rust raw reason_code MANIFEST_JSON_INVALID maps to class
        # MANIFEST_MALFORMED@manifest, matching the frozen expected.
        rust = self._rust("cmp_rust_div.py", "FAIL",
                          "MANIFEST_JSON_INVALID", 1)
        rc, out, err = self._compare(py, rust, "stage_manifest_json_invalid")
        obj = json.loads(out)
        self.assertEqual(obj["comparison_status"], "DECLARED_DIVERGENCE")
        self.assertEqual(rc, 0)
        self.assertEqual(obj["python_lane"]["verdict"], "FAIL")
        self.assertEqual(obj["rust_lane"]["verdict"], "FAIL")

    def test_lane_not_applicable(self):
        # stage_receipt_linkage_broken: python out_of_scope (null lane),
        # rust in_scope FAIL/1 RECEIPT_LINKAGE_BROKEN@receipts.
        rust = self._rust("cmp_rust_single.py", "FAIL",
                          "RECEIPT_LINKAGE_BROKEN", 1)
        rc, out, err = self._compare(
            PYTHON_ENTRY, rust, "stage_receipt_linkage_broken")
        obj = json.loads(out)
        self.assertEqual(obj["comparison_status"], "LANE_NOT_APPLICABLE")
        self.assertEqual(rc, 0)
        # the out-of-scope python lane is legitimately null
        self.assertIsNone(obj["python_lane"])
        # the in-scope rust lane is a complete record
        self.assertEqual(obj["rust_lane"]["record_type"], "verdict")
        self.assertEqual(obj["rust_lane"]["verdict"], "FAIL")

    def test_unexpected_divergence(self):
        # clean_control but rust returns FAIL instead of the expected
        # INCONCLUSIVE -> lanes do not match the adopted contract ->
        # UNEXPECTED_DIVERGENCE, exit 1.
        rust = self._rust("cmp_unexp.py", "FAIL",
                          "RECEIPT_HASH_RECOMPUTATION_MISMATCH", 1)
        rc, out, err = self._compare(PYTHON_ENTRY, rust, "clean_control")
        obj = json.loads(out)
        self.assertEqual(obj["comparison_status"], "UNEXPECTED_DIVERGENCE")
        self.assertEqual(rc, 1)
        # both lane records preserved, neither flattened
        self.assertEqual(obj["python_lane"]["record_type"], "verdict")
        self.assertEqual(obj["rust_lane"]["record_type"], "verdict")

    def test_measurement_error_preserves_lanes(self):
        # rust lane malformed -> its record is a measurement_error,
        # comparison_status MEASUREMENT_ERROR, python lane preserved,
        # rust lane NOT null.
        rust = _fake_rust("cmp_rust_bad.py", "{bad\n", 3)
        rc, out, err = self._compare(PYTHON_ENTRY, rust, "clean_control")
        obj = json.loads(out)
        self.assertEqual(obj["comparison_status"], "MEASUREMENT_ERROR")
        self.assertEqual(rc, 1)
        self.assertEqual(obj["python_lane"]["record_type"], "verdict")
        self.assertEqual(obj["rust_lane"]["record_type"],
                         "measurement_error")
        self.assertIsNotNone(obj["rust_lane"])

    def test_unknown_case_id_is_measurement_error(self):
        # An unknown case id is a measurement error about the COMPARE
        # operation itself -- one top-level measurement_error record, never
        # a comparison record with both lanes null.
        rust = self._rust("cmp_unknown.py", "INCONCLUSIVE",
                          "RECEIPT_CHAIN_HASHES_RECOMPUTED", 3)
        rc, out, err = self._compare(
            PYTHON_ENTRY, rust, "no_such_case_id_xyz")
        obj = json.loads(out)
        self.assertEqual(obj["record_type"], "measurement_error")
        self.assertEqual(obj["measurement_error_code"],
                         "ADAPTER_UNKNOWN_CASE_ID")
        self.assertEqual(obj["operation"], "compare")
        self.assertNotIn("comparison_status", obj)
        self.assertEqual(rc, 1)

    def test_comparison_status_never_verdict_label(self):
        rust = self._rust("cmp_lbl.py", "INCONCLUSIVE",
                          "RECEIPT_CHAIN_HASHES_RECOMPUTED", 3)
        rc, out, err = self._compare(PYTHON_ENTRY, rust, "clean_control")
        obj = json.loads(out)
        self.assertNotIn(obj["comparison_status"],
                         ("PASS", "FAIL", "INCONCLUSIVE"))

    def test_compare_missing_case_id_is_usage(self):
        rust = self._rust("cmp_nocase.py", "INCONCLUSIVE",
                          "RECEIPT_CHAIN_HASHES_RECOMPUTED", 3)
        rc, out, err = _run_adapter([
            "compare", "--input", CLEAN_BUNDLE, "--reason-map", REASON_MAP,
            "--python-bin", PYTHON_BIN, "--python-entry", PYTHON_ENTRY,
            "--rust-bin", rust, "--comparison-contract", self.CONTRACT])
        self.assertEqual(rc, 2)
        self.assertEqual(out, b"")


# ----------------------------------------------------------------------
# Legacy default output preservation
# ----------------------------------------------------------------------

class TestLegacyOutputPreserved(unittest.TestCase):
    def test_python_default_verify_output_unchanged(self):
        # invoking the adopted companion verify directly yields the
        # legacy {verify_ok, companion_status, reason} object; the adapter
        # does not alter that command's own output.
        proc = subprocess.run(
            [PYTHON_BIN, "-B", PYTHON_ENTRY, "verify", "--run",
             CLEAN_BUNDLE], capture_output=True,
            timeout=SUBPROCESS_TIMEOUT)
        self.assertEqual(proc.returncode, 0)
        obj = json.loads(proc.stdout)
        self.assertEqual(set(obj.keys()),
                         {"verify_ok", "companion_status", "reason"})
        self.assertTrue(obj["verify_ok"])


# ----------------------------------------------------------------------
# detail safety
# ----------------------------------------------------------------------

class TestDetailSafety(unittest.TestCase):
    def test_unsafe_detail_omitted(self):
        # a rust line whose detail contains a path -> detail omitted
        line = _RUST_FAIL.replace('"detail": "bad"',
                                  '"detail": "/abs/path/leak"')
        rb = _fake_rust("ds_path.py", line + "\n", 1)
        d = os.path.join(_TMP, "dsbundle")
        os.makedirs(d, exist_ok=True)
        rc, out, err = _run_adapter([
            "verdict", "--lane", "rust_bundle", "--input", d,
            "--reason-map", REASON_MAP, "--rust-bin", rb])
        self.assertEqual(rc, 1)
        obj = json.loads(out)
        self.assertNotIn("detail", obj)

    def test_safe_detail_included(self):
        rb = _fake_rust("ds_safe.py", _RUST_FAIL + "\n", 1)
        d = os.path.join(_TMP, "dsbundle2")
        os.makedirs(d, exist_ok=True)
        rc, out, err = _run_adapter([
            "verdict", "--lane", "rust_bundle", "--input", d,
            "--reason-map", REASON_MAP, "--rust-bin", rb])
        obj = json.loads(out)
        self.assertEqual(obj.get("detail"), "bad")

    def test_detail_safety_predicate(self):
        self.assertTrue(adapter._detail_is_safe("companion completed"))
        self.assertTrue(adapter._detail_is_safe(""))
        self.assertFalse(adapter._detail_is_safe("/tmp/x"))
        self.assertFalse(adapter._detail_is_safe("2026-07-20"))
        self.assertFalse(adapter._detail_is_safe("0xdeadbeef"))
        self.assertFalse(adapter._detail_is_safe("a/b"))


# ----------------------------------------------------------------------
# A. Underlying stderr rejected for EVERY lane
# ----------------------------------------------------------------------

class TestUnderlyingStderrEveryLane(unittest.TestCase):
    def _bundle(self):
        d = os.path.join(_TMP, "stderrbundle")
        os.makedirs(d, exist_ok=True)
        return d

    def test_python_valid_json_plus_stderr_rejected(self):
        fake = _write_exe(
            "se_py.py",
            "import json,sys\n"
            "sys.stderr.write('warning: noise')\n"
            "print(json.dumps({'verify_ok': True,"
            " 'companion_status':'C','reason':'companion completed'}))\n"
            "sys.exit(0)\n")
        rc, out, err = _run_adapter([
            "verdict", "--lane", "python_bundle", "--input", CLEAN_BUNDLE,
            "--reason-map", REASON_MAP, "--python-bin", PYTHON_BIN,
            "--python-entry", fake])
        self.assertEqual(rc, schema.MEASUREMENT_ERROR_EXIT)
        obj = json.loads(out)
        self.assertEqual(obj["measurement_error_code"],
                         "ADAPTER_UNEXPECTED_STDERR")
        self.assertNotIn("verdict", obj)

    def test_rust_valid_json_plus_stderr_rejected(self):
        rb = _fake_rust("se_rust.py", _RUST_INCONCLUSIVE + "\n", 3,
                        stderr="warning: noise")
        rc, out, err = _run_adapter([
            "verdict", "--lane", "rust_bundle", "--input", self._bundle(),
            "--reason-map", REASON_MAP, "--rust-bin", rb])
        self.assertEqual(rc, schema.MEASUREMENT_ERROR_EXIT)
        obj = json.loads(out)
        self.assertEqual(obj["measurement_error_code"],
                         "ADAPTER_UNEXPECTED_STDERR")
        self.assertNotIn("verdict", obj)

    def test_archive_valid_json_plus_stderr_rejected(self):
        rb = _fake_rust("se_arch.py", _ARCHIVE_INCONCLUSIVE + "\n", 3,
                        stderr="warning: noise")
        z = os.path.join(_TMP, "se.zip")
        with open(z, "wb") as h:
            h.write(b"PK\x03\x04")
        rc, out, err = _run_adapter([
            "verdict", "--lane", "archive", "--input", z,
            "--reason-map", REASON_MAP, "--rust-bin", rb])
        self.assertEqual(rc, schema.MEASUREMENT_ERROR_EXIT)
        obj = json.loads(out)
        self.assertEqual(obj["measurement_error_code"],
                         "ADAPTER_UNEXPECTED_STDERR")
        self.assertNotIn("verdict", obj)


# ----------------------------------------------------------------------
# B. Strict stdout framing
# ----------------------------------------------------------------------

class TestStrictFraming(unittest.TestCase):
    def _bundle(self):
        d = os.path.join(_TMP, "framebundle")
        os.makedirs(d, exist_ok=True)
        return d

    def _expect(self, stdout, code, tag):
        rb = _fake_rust("frm_%s.py" % tag, stdout, 3)
        rc, out, err = _run_adapter([
            "verdict", "--lane", "rust_bundle", "--input", self._bundle(),
            "--reason-map", REASON_MAP, "--rust-bin", rb])
        self.assertEqual(rc, schema.MEASUREMENT_ERROR_EXIT)
        obj = json.loads(out)
        self.assertEqual(obj["measurement_error_code"], code)
        self.assertNotIn("verdict", obj)

    def test_leading_space(self):
        self._expect(" " + _RUST_INCONCLUSIVE + "\n",
                     "ADAPTER_STDOUT_CONTAMINATION", "lspace")

    def test_leading_newline(self):
        self._expect("\n" + _RUST_INCONCLUSIVE + "\n",
                     "ADAPTER_STDOUT_CONTAMINATION", "lnl")

    def test_leading_blank_line(self):
        self._expect("\n\n" + _RUST_INCONCLUSIVE + "\n",
                     "ADAPTER_STDOUT_CONTAMINATION", "lblank")

    def test_trailing_space(self):
        self._expect(_RUST_INCONCLUSIVE + " \n",
                     "ADAPTER_STDOUT_CONTAMINATION", "tspace")

    def test_extra_trailing_newline(self):
        self._expect(_RUST_INCONCLUSIVE + "\n\n",
                     "ADAPTER_STDOUT_CONTAMINATION", "tnl")

    def test_prefix_text(self):
        self._expect("PROGRESS\n" + _RUST_INCONCLUSIVE + "\n",
                     "ADAPTER_STDOUT_CONTAMINATION", "prefix")

    def test_suffix_text(self):
        self._expect(_RUST_INCONCLUSIVE + "\nDONE\n",
                     "ADAPTER_STDOUT_CONTAMINATION", "suffix")

    def test_multiple_objects_framing(self):
        self._expect(_RUST_INCONCLUSIVE + "\n" + _RUST_FAIL + "\n",
                     "ADAPTER_MULTIPLE_OBJECTS", "multi")

    def test_exactly_one_object_no_newline_accepted(self):
        # a single object with NO trailing newline is the adopted minimum
        rb = _fake_rust("frm_nonl.py", _RUST_INCONCLUSIVE, 3)
        rc, out, err = _run_adapter([
            "verdict", "--lane", "rust_bundle", "--input", self._bundle(),
            "--reason-map", REASON_MAP, "--rust-bin", rb])
        self.assertEqual(rc, 3)
        self.assertEqual(json.loads(out)["verdict"], "INCONCLUSIVE")


# ----------------------------------------------------------------------
# C. Verifier identity variants
# ----------------------------------------------------------------------

class TestVerifierIdentityVariants(unittest.TestCase):
    def _bundle(self):
        d = os.path.join(_TMP, "identbundle")
        os.makedirs(d, exist_ok=True)
        return d

    def _expect_identity_error(self, line, tag):
        rb = _fake_rust("id_%s.py" % tag, line + "\n", 3)
        rc, out, err = _run_adapter([
            "verdict", "--lane", "rust_bundle", "--input", self._bundle(),
            "--reason-map", REASON_MAP, "--rust-bin", rb])
        self.assertEqual(rc, schema.MEASUREMENT_ERROR_EXIT)
        obj = json.loads(out)
        self.assertEqual(obj["measurement_error_code"],
                         "ADAPTER_VERIFIER_IDENTITY_MISMATCH")
        self.assertNotIn("verdict", obj)

    def test_identity_empty_string(self):
        self._expect_identity_error(
            _RUST_INCONCLUSIVE.replace('"witness-verify"', '""'), "empty")

    def test_identity_non_string(self):
        self._expect_identity_error(
            _RUST_INCONCLUSIVE.replace('"witness-verify"', '123'), "nonstr")

    def test_identity_correct_accepted(self):
        rb = _fake_rust("id_ok.py", _RUST_INCONCLUSIVE + "\n", 3)
        rc, out, err = _run_adapter([
            "verdict", "--lane", "rust_bundle", "--input", self._bundle(),
            "--reason-map", REASON_MAP, "--rust-bin", rb])
        self.assertEqual(rc, 3)
        self.assertEqual(json.loads(out)["verifier"], "witness-verify")


# ----------------------------------------------------------------------
# D. Real inherited Python verifier integration
# ----------------------------------------------------------------------

class TestRealPythonVerifierIntegration(unittest.TestCase):
    def _copy_bundle(self, name):
        import shutil
        dest = os.path.join(_TMP, name)
        if os.path.isdir(dest):
            shutil.rmtree(dest)
        shutil.copytree(CLEAN_BUNDLE, dest)
        return dest

    def test_real_verifier_missing_companion_report(self):
        # A genuinely prepared bundle with companion_report.json removed,
        # verified by the REAL inherited Python entry point.
        bundle = self._copy_bundle("missing_report_bundle")
        target = os.path.join(bundle, "companion_report.json")
        self.assertTrue(os.path.isfile(target))
        os.remove(target)
        rc, out, err = _run_adapter([
            "verdict", "--lane", "python_bundle", "--input", bundle,
            "--reason-map", REASON_MAP, "--python-bin", PYTHON_BIN,
            "--python-entry", PYTHON_ENTRY])
        self.assertEqual(err, b"")
        obj = json.loads(out)
        self.assertEqual(obj["record_type"], "verdict")
        self.assertEqual(obj["verdict"], "FAIL")
        self.assertEqual(obj["exit_code"], 1)
        self.assertEqual(rc, 1)
        self.assertEqual(obj["reason_code"], "REQUIRED_FILE_MISSING")
        self.assertEqual(obj["stage"], "manifest")

    def test_real_verifier_noncanonical_report(self):
        # An honestly prepared noncanonical companion_report.json (same
        # data, non-canonical byte form), verified by the REAL entry point.
        bundle = self._copy_bundle("noncanon_report_bundle")
        target = os.path.join(bundle, "companion_report.json")
        with open(target, encoding="utf-8") as handle:
            data = json.load(handle)
        # re-serialize with indentation => valid JSON, non-canonical bytes
        with open(target, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=4, sort_keys=False)
        rc, out, err = _run_adapter([
            "verdict", "--lane", "python_bundle", "--input", bundle,
            "--reason-map", REASON_MAP, "--python-bin", PYTHON_BIN,
            "--python-entry", PYTHON_ENTRY])
        self.assertEqual(err, b"")
        obj = json.loads(out)
        self.assertEqual(obj["record_type"], "verdict")
        self.assertEqual(obj["verdict"], "FAIL")
        self.assertEqual(obj["exit_code"], 1)
        self.assertEqual(rc, 1)
        self.assertEqual(obj["reason_code"], "REPORT_NOT_CANONICAL")
        self.assertEqual(obj["stage"], "canonical_report")

    def test_reason_form_fail(self):
        fake = _write_exe(
            "rf_reason.py",
            "import json,sys\n"
            "print(json.dumps({'verify_ok': False,"
            " 'reason':'missing required file: bar'}))\n"
            "sys.exit(1)\n")
        rc, out, err = _run_adapter([
            "verdict", "--lane", "python_bundle", "--input", CLEAN_BUNDLE,
            "--reason-map", REASON_MAP, "--python-bin", PYTHON_BIN,
            "--python-entry", fake])
        self.assertEqual(rc, 1)
        self.assertEqual(json.loads(out)["reason_code"],
                         "REQUIRED_FILE_MISSING")

    def test_error_key_takes_precedence_over_reason(self):
        # adopted rule: out.get("error", out.get("reason", ""))
        fake = _write_exe(
            "rf_both.py",
            "import json,sys\n"
            "print(json.dumps({'verify_ok': False,"
            " 'error':'companion_report not canonical',"
            " 'reason':'missing required file: ignored'}))\n"
            "sys.exit(1)\n")
        rc, out, err = _run_adapter([
            "verdict", "--lane", "python_bundle", "--input", CLEAN_BUNDLE,
            "--reason-map", REASON_MAP, "--python-bin", PYTHON_BIN,
            "--python-entry", fake])
        self.assertEqual(rc, 1)
        # the ERROR key wins, so the class is the canonical-report one
        self.assertEqual(json.loads(out)["reason_code"],
                         "REPORT_NOT_CANONICAL")

    def test_non_string_reason_fails_closed(self):
        fake = _write_exe(
            "rf_nonstr.py",
            "import json,sys\n"
            "print(json.dumps({'verify_ok': False, 'error': 42}))\n"
            "sys.exit(1)\n")
        rc, out, err = _run_adapter([
            "verdict", "--lane", "python_bundle", "--input", CLEAN_BUNDLE,
            "--reason-map", REASON_MAP, "--python-bin", PYTHON_BIN,
            "--python-entry", fake])
        self.assertEqual(rc, schema.MEASUREMENT_ERROR_EXIT)
        self.assertEqual(json.loads(out)["measurement_error_code"],
                         "ADAPTER_INCOMPLETE_RESULT")

    def test_empty_error_fails_closed(self):
        fake = _write_exe(
            "rf_emptyerr.py",
            "import json,sys\n"
            "print(json.dumps({'verify_ok': False, 'error': ''}))\n"
            "sys.exit(1)\n")
        rc, out, err = _run_adapter([
            "verdict", "--lane", "python_bundle", "--input", CLEAN_BUNDLE,
            "--reason-map", REASON_MAP, "--python-bin", PYTHON_BIN,
            "--python-entry", fake])
        self.assertEqual(rc, schema.MEASUREMENT_ERROR_EXIT)
        self.assertEqual(json.loads(out)["measurement_error_code"],
                         "ADAPTER_INCOMPLETE_RESULT")


# ----------------------------------------------------------------------
# E. Comparison-contract validation
# ----------------------------------------------------------------------

class TestComparisonContractValidation(unittest.TestCase):
    CONTRACT = os.path.join(
        ROOT, "verify", "agreement_harness_v01", "corpus",
        "bundle_cases.json")
    ARCHIVE_CONTRACT = os.path.join(
        ROOT, "verify", "agreement_harness_v01", "corpus",
        "archive_cases.json")

    def _rust(self, name):
        return _fake_rust(name, _RUST_INCONCLUSIVE + "\n", 3)

    def _compare_with(self, contract_path, case_id="clean_control",
                      tag="x"):
        rust = self._rust("cc_%s.py" % tag)
        return _run_adapter([
            "compare", "--input", CLEAN_BUNDLE, "--reason-map", REASON_MAP,
            "--python-bin", PYTHON_BIN, "--python-entry", PYTHON_ENTRY,
            "--rust-bin", rust, "--case-id", case_id,
            "--comparison-contract", contract_path])

    def _write_contract(self, name, obj):
        path = os.path.join(_TMP, name)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(obj, handle)
        return path

    def _base_contract(self):
        with open(self.CONTRACT, encoding="utf-8") as handle:
            return json.load(handle)

    def _expect_contract_invalid(self, contract_path, tag):
        rc, out, err = self._compare_with(contract_path, tag=tag)
        self.assertEqual(rc, schema.MEASUREMENT_ERROR_EXIT)
        self.assertEqual(err, b"")
        obj = json.loads(out)
        self.assertEqual(obj["record_type"], "measurement_error")
        self.assertEqual(obj["measurement_error_code"],
                         "ADAPTER_COMPARISON_CONTRACT_INVALID")
        self.assertEqual(obj["operation"], "compare")
        # never a comparison record with both lanes null
        self.assertNotIn("python_lane", obj)
        self.assertNotIn("rust_lane", obj)
        self.assertNotIn("comparison_status", obj)

    def test_invalid_json_contract(self):
        path = os.path.join(_TMP, "cc_badjson.json")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("{not json")
        self._expect_contract_invalid(path, "badjson")

    def test_wrong_corpus_lane(self):
        # the archive corpus must not be usable for a bundle comparison
        self._expect_contract_invalid(self.ARCHIVE_CONTRACT, "wronglane")

    def test_missing_expected_object(self):
        data = self._base_contract()
        data["cases"][0].pop("expected", None)
        self._expect_contract_invalid(
            self._write_contract("cc_noexp.json", data), "noexp")

    def test_invalid_category(self):
        data = self._base_contract()
        data["cases"][0]["category"] = "NOT_A_CATEGORY"
        self._expect_contract_invalid(
            self._write_contract("cc_badcat.json", data), "badcat")

    def test_invalid_scope(self):
        data = self._base_contract()
        data["cases"][0]["python_scope"] = "maybe"
        self._expect_contract_invalid(
            self._write_contract("cc_badscope.json", data), "badscope")

    def test_duplicate_case_ids(self):
        data = self._base_contract()
        data["cases"].append(dict(data["cases"][0]))
        self._expect_contract_invalid(
            self._write_contract("cc_dup.json", data), "dup")

    def test_malformed_expected_lane_shape(self):
        data = self._base_contract()
        for case in data["cases"]:
            if case["case_id"] == "clean_control":
                case["expected"]["rust"]["exit_code"] = "three"
        self._expect_contract_invalid(
            self._write_contract("cc_badshape.json", data), "badshape")

    def test_cases_not_a_list(self):
        data = self._base_contract()
        data["cases"] = {"clean_control": {}}
        self._expect_contract_invalid(
            self._write_contract("cc_notlist.json", data), "notlist")

    def test_category_scope_inconsistency(self):
        # an AGREEMENT_CASE must have both lanes in scope
        data = self._base_contract()
        for case in data["cases"]:
            if case["case_id"] == "clean_control":
                case["python_scope"] = "out_of_scope"
        self._expect_contract_invalid(
            self._write_contract("cc_incons.json", data), "incons")

    def test_unknown_case_id_shape(self):
        rc, out, err = self._compare_with(
            self.CONTRACT, case_id="definitely_not_a_case", tag="unk")
        self.assertEqual(rc, schema.MEASUREMENT_ERROR_EXIT)
        obj = json.loads(out)
        self.assertEqual(obj["record_type"], "measurement_error")
        self.assertEqual(obj["measurement_error_code"],
                         "ADAPTER_UNKNOWN_CASE_ID")
        self.assertEqual(obj["operation"], "compare")
        self.assertNotIn("comparison_status", obj)

    def test_missing_expected_divergence(self):
        data = self._base_contract()
        for case in data["cases"]:
            if case["category"] == "KNOWN_DIVERGENCE_CASE":
                case.pop("expected_divergence", None)
        self._expect_contract_invalid(
            self._write_contract("cc_nodiv.json", data), "nodiv")

    def test_inconsistent_expected_divergence(self):
        data = self._base_contract()
        for case in data["cases"]:
            if case["category"] == "KNOWN_DIVERGENCE_CASE":
                case["expected_divergence"]["rust_stage"] = "not_the_stage"
                break
        self._expect_contract_invalid(
            self._write_contract("cc_baddiv.json", data), "baddiv")

    def test_impossible_verdict_exit_pairing_rejected(self):
        data = self._base_contract()
        for case in data["cases"]:
            if case["case_id"] == "clean_control":
                # rust INCONCLUSIVE must pair with exit 3, not 1
                case["expected"]["rust"]["exit_code"] = 1
        self._expect_contract_invalid(
            self._write_contract("cc_badpair.json", data), "badpair")

    def test_expected_exit_2_rejected(self):
        data = self._base_contract()
        for case in data["cases"]:
            if case["case_id"] == "clean_control":
                case["expected"]["python"]["exit_code"] = 2
        self._expect_contract_invalid(
            self._write_contract("cc_exit2.json", data), "exit2")

    def test_python_inconclusive_expectation_rejected(self):
        data = self._base_contract()
        for case in data["cases"]:
            if case["case_id"] == "clean_control":
                case["expected"]["python"]["verdict"] = "INCONCLUSIVE"
                case["expected"]["python"]["exit_code"] = 3
        self._expect_contract_invalid(
            self._write_contract("cc_pyinc.json", data), "pyinc")

    def test_rust_pass_expectation_rejected(self):
        data = self._base_contract()
        for case in data["cases"]:
            if case["case_id"] == "clean_control":
                case["expected"]["rust"]["verdict"] = "PASS"
                case["expected"]["rust"]["exit_code"] = 0
        self._expect_contract_invalid(
            self._write_contract("cc_rustpass.json", data), "rustpass")

    def test_wrong_per_case_lane_rejected(self):
        data = self._base_contract()
        data["cases"][0]["lane"] = "archive"
        self._expect_contract_invalid(
            self._write_contract("cc_caselane.json", data), "caselane")

    def test_whitespace_only_case_id_rejected(self):
        data = self._base_contract()
        data["cases"][0]["case_id"] = "   "
        self._expect_contract_invalid(
            self._write_contract("cc_wscase.json", data), "wscase")

    def test_invalid_normalized_outcome_rejected(self):
        data = self._base_contract()
        data["cases"][0]["expected"]["normalized_outcome"] = "MAYBE"
        self._expect_contract_invalid(
            self._write_contract("cc_badout.json", data), "badout")

    def test_outcome_inconsistent_with_lane_verdict_rejected(self):
        data = self._base_contract()
        for case in data["cases"]:
            if case["case_id"] == "clean_control":
                # ACCEPTED declared, but a FAIL lane verdict contradicts it
                case["expected"]["python"]["verdict"] = "FAIL"
                case["expected"]["python"]["exit_code"] = 1
        self._expect_contract_invalid(
            self._write_contract("cc_outincons.json", data), "outincons")

    def test_malformed_out_of_scope_observed_record_rejected(self):
        data = self._base_contract()
        for case in data["cases"]:
            if case["category"] == "SINGLE_IMPLEMENTATION_CASE":
                obs = ("python_observed"
                       if case["python_scope"] == "out_of_scope"
                       else "rust_observed")
                if obs in case["expected"]:
                    case["expected"][obs]["exit_code"] = "one"
                    break
        self._expect_contract_invalid(
            self._write_contract("cc_badobs.json", data), "badobs")

    def test_non_divergence_case_with_divergence_metadata_rejected(self):
        data = self._base_contract()
        for case in data["cases"]:
            if case["category"] == "AGREEMENT_CASE":
                case["expected_divergence"] = {
                    "python_class": "X", "python_stage": "y",
                    "rust_class": "Z", "rust_stage": "w"}
                break
        self._expect_contract_invalid(
            self._write_contract("cc_extradiv.json", data), "extradiv")

    def test_real_frozen_contract_is_accepted(self):
        # the validator must NOT reject the genuine adopted authority
        rust = self._rust("cc_real.py")
        rc, out, err = _run_adapter([
            "compare", "--input", CLEAN_BUNDLE, "--reason-map", REASON_MAP,
            "--python-bin", PYTHON_BIN, "--python-entry", PYTHON_ENTRY,
            "--rust-bin", rust, "--case-id", "clean_control",
            "--comparison-contract", self.CONTRACT])
        obj = json.loads(out)
        self.assertEqual(obj["record_type"], "comparison")
        self.assertEqual(obj["comparison_status"], "AGREEMENT")

    def test_contract_error_records_carry_input_type(self):
        # repair: the input directory is validated BEFORE authority lookup,
        # so its type is honestly established and must be preserved
        path = os.path.join(_TMP, "cc_badjson2.json")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("{nope")
        rc, out, err = self._compare_with(path, tag="itype")
        obj = json.loads(out)
        self.assertEqual(obj["input_type"], "bundle_dir")
        self.assertEqual(obj["operation"], "compare")
        self.assertNotIn("verdict", obj)
        self.assertNotIn("python_lane", obj)

    def test_second_declared_divergence_id(self):
        # stage_report_field_missing_repaired is the OTHER adopted
        # known-divergence case; prove the contract declares it as such.
        data = self._base_contract()
        found = [c for c in data["cases"]
                 if c["case_id"] == "stage_report_field_missing_repaired"]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["category"], "KNOWN_DIVERGENCE_CASE")
        self.assertEqual(found[0]["python_scope"], "in_scope")
        self.assertEqual(found[0]["rust_scope"], "in_scope")
        # and that the adapter emits DECLARED_DIVERGENCE when both lanes
        # match its adopted expected outcomes
        exp = found[0]["expected"]
        py = _write_exe(
            "cc_div2_py.py",
            "import json,sys\n"
            "print(json.dumps({'verify_ok': %s, 'error': %r}))\n"
            "sys.exit(%d)\n"
            % (exp["python"]["verdict"] == "PASS",
               _reason_text_for(exp["python"]["reason_class"],
                                "python_bundle"),
               exp["python"]["exit_code"]))
        rust = _fake_rust(
            "cc_div2_rust.py",
            '{"verifier": "witness-verify",'
            ' "version": "0.0.8-step79-diagnostics",'
            ' "verdict": "%s", "reason_code": "%s", "detail": "d"}\n'
            % (exp["rust"]["verdict"],
               _reason_text_for(exp["rust"]["reason_class"], "rust_bundle")),
            exp["rust"]["exit_code"])
        rc, out, err = _run_adapter([
            "compare", "--input", CLEAN_BUNDLE, "--reason-map", REASON_MAP,
            "--python-bin", PYTHON_BIN, "--python-entry", py,
            "--rust-bin", rust, "--case-id",
            "stage_report_field_missing_repaired",
            "--comparison-contract", self.CONTRACT])
        obj = json.loads(out)
        self.assertEqual(obj["comparison_status"], "DECLARED_DIVERGENCE")
        self.assertEqual(rc, 0)


def _reason_text_for(reason_class, lane):
    """Find a raw reason value in the frozen reason map that normalizes to
    the given class for the given lane. Used only by tests to drive fakes
    from the adopted authority instead of hardcoding."""
    with open(REASON_MAP, encoding="utf-8") as handle:
        rm = json.load(handle)
    for entry in rm[lane]:
        if entry.get("class") == reason_class \
                and entry.get("match_type") == "exact":
            return entry["value"]
    raise AssertionError("no exact reason value for %s in %s"
                         % (reason_class, lane))


# ----------------------------------------------------------------------
# F. Gate authority
# ----------------------------------------------------------------------

GATE = os.path.join(ROOT, "tools",
                    "check_move81_structured_verdict_adoption.sh")
BASELINE_CHECKER = os.path.join(HERE, "check_move81_inherited.py")
ALLOWLIST = os.path.join(HERE, "allowlist_move81.json")
ADOPTED_M80_SHA = \
    "8c08342efae3b17458e33c6ae54ff42bf79d6759170b46cfbf32ef218d0dd2ad"


class TestGateAuthority(unittest.TestCase):
    def _gate_text(self):
        with open(GATE, encoding="utf-8") as handle:
            return handle.read()

    def _pre_bootstrap_section(self, strip_comments=False):
        text = self._gate_text()
        marker = '. "$ROOT/tools/gate_bootstrap.sh"'
        idx = text.find(marker)
        self.assertNotEqual(idx, -1, "gate must source gate_bootstrap.sh")
        pre = text[:idx]
        if strip_comments:
            # only EXECUTABLE lines matter for the trust-order property;
            # prose in comments is not an invocation.
            pre = "\n".join(
                line for line in pre.splitlines()
                if not line.strip().startswith("#"))
        return pre

    def test_no_path_resolved_tools_before_bootstrap(self):
        # Hostile PATH must not be able to substitute any pre-bootstrap
        # tool: no bare external command may be invoked before the trusted
        # bootstrap is sourced. The ONLY external execution permitted is
        # the LITERAL trusted readlink path.
        pre = self._pre_bootstrap_section(strip_comments=True)
        forbidden = ("dirname", "basename", "$(pwd)", "`pwd`", "sha256sum",
                     "cargo", "rustc", "python3", "mktemp", "grep", "sed",
                     "awk", "realpath")
        for token in forbidden:
            self.assertNotIn(
                token, pre,
                "pre-bootstrap section must not reference %r" % token)
        # readlink may be reached ONLY via the literal trusted absolute
        # path (assigned to _TRUSTED_READLINK and invoked through it).
        # A BARE `readlink` command would be PATH-resolved and is banned.
        self.assertIn(
            '_TRUSTED_READLINK=/data/data/com.termux/files/usr/bin/readlink',
            pre)
        for line in pre.splitlines():
            if "readlink" not in line:
                continue
            # every executable mention must be either the literal path
            # assignment or an invocation through the validated variable
            self.assertTrue(
                "/data/data/com.termux/files/usr/bin/readlink" in line
                or "$_TRUSTED_READLINK" in line
                or '"$_TRUSTED_READLINK"' in line,
                "bare readlink reference before bootstrap: %r" % line)
        # and the invocation itself must go through the variable
        self.assertIn('$("$_TRUSTED_READLINK" -f -- "$0")', pre)

    def test_pre_bootstrap_validates_canonical_script_path(self):
        pre = self._pre_bootstrap_section()
        self.assertIn(
            "*/tools/check_move81_structured_verdict_adoption.sh", pre)
        self.assertIn("_SCRIPT_DIR=${SCRIPT_REAL%/*}", pre)
        self.assertIn("ROOT=${_SCRIPT_DIR%/*}", pre)

    def test_gate_hash_verifies_baseline_with_trusted_sha256sum(self):
        # static: the gate must use the trusted sha256sum against the exact
        # adopted hash, before the inherited comparison
        text = self._gate_text()
        self.assertIn('_M80_SHA=$("$TRUSTED_SHA256SUM" "$M80_ZIP")', text)
        self.assertIn(ADOPTED_M80_SHA, text)
        # the SHELL gate genuinely uses $TRUSTED_SHA256SUM, so it keeps
        # that wording; the Python checker must NOT claim it
        self.assertIn("REAL_MOVE80 verified by trusted sha256sum:", text)
        with open(BASELINE_CHECKER, encoding="utf-8") as h:
            checker_src = h.read()
        self.assertNotIn("verified by trusted sha256sum", checker_src)
        self.assertIn("independently matched --expect-sha256", checker_src)
        self.assertLess(text.find(ADOPTED_M80_SHA),
                        text.find("check_move81_inherited.py"))
        # and it must pass the expected hash down to the checker so the
        # authority is enforced independently a second time
        self.assertIn('--expect-sha256 "$_M80_EXPECT"', text)


class TestBaselineHashAuthorityExecutable(unittest.TestCase):
    """EXECUTABLE negative tests around the baseline hash authority. These
    RUN the real authority logic rather than searching source text, and are
    self-contained: they build synthetic baselines and use their true
    hashes, so they need no external artifact and never skip."""

    def _sha256(self, path):
        import hashlib
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            digest.update(handle.read())
        return digest.hexdigest()

    def _make_zip(self, name, members):
        import zipfile
        path = os.path.join(_TMP, name)
        with zipfile.ZipFile(path, "w") as zf:
            for member, content in members:
                zf.writestr(member, content)
        return path

    def _run_authority(self, zip_path, expect):
        return subprocess.run(
            [PYTHON_BIN, "-B", BASELINE_CHECKER,
             "--baseline-zip", zip_path, "--root", ROOT,
             "--allowlist", ALLOWLIST, "--expect-sha256", expect],
            capture_output=True, timeout=SUBPROCESS_TIMEOUT)

    def test_exact_hash_accepted_and_proceeds_past_hash_gate(self):
        z = self._make_zip(
            "auth_exact.zip",
            [("project-witness-main/a.txt", "content")])
        proc = self._run_authority(z, self._sha256(z))
        # the hash gate passes, so the run PROCEEDS (it then fails the
        # inherited comparison, which is expected for a synthetic tree)
        self.assertIn(b"REAL_MOVE80 independently matched "
                      b"--expect-sha256 in the baseline checker:",
                      proc.stdout)
        self.assertNotIn(b"BASELINE_HASH_MISMATCH", proc.stdout)
        # having passed the hash gate it reaches safety inspection
        self.assertIn(b"baseline ZIP safety:", proc.stdout)

    def test_different_zip_rejected(self):
        good = self._make_zip(
            "auth_good.zip", [("project-witness-main/a.txt", "one")])
        other = self._make_zip(
            "auth_other.zip", [("project-witness-main/a.txt", "two")])
        proc = self._run_authority(other, self._sha256(good))
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"BASELINE_HASH_MISMATCH", proc.stdout)

    def test_byte_modified_zip_rejected(self):
        z = self._make_zip(
            "auth_orig.zip", [("project-witness-main/a.txt", "payload")])
        expected = self._sha256(z)
        modified = os.path.join(_TMP, "auth_modified.zip")
        with open(z, "rb") as src:
            data = bytearray(src.read())
        data[len(data) // 2] ^= 0xFF
        with open(modified, "wb") as dst:
            dst.write(bytes(data))
        proc = self._run_authority(modified, expected)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"BASELINE_HASH_MISMATCH", proc.stdout)

    def test_arbitrary_zip_merely_renamed_rejected(self):
        # named exactly like the adopted baseline, but arbitrary content:
        # the NAME confers no authority, only the hash does.
        renamed = self._make_zip(
            "project-witness-MOVE_80_candidate_v07.zip",
            [("project-witness-main/README.md", "not the baseline")])
        proc = self._run_authority(renamed, ADOPTED_M80_SHA)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"BASELINE_HASH_MISMATCH", proc.stdout)

    def test_comparison_never_reached_after_hash_mismatch(self):
        # a ZIP that would ALSO fail safety inspection: prove the run stops
        # at the hash check and never reaches safety inspection or the
        # member comparison.
        bad = self._make_zip(
            "auth_mismatch_unsafe.zip",
            [("project-witness-main/ok.txt", "x"),
             ("project-witness-main/../evil.txt", "x")])
        proc = self._run_authority(bad, ADOPTED_M80_SHA)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"BASELINE_HASH_MISMATCH", proc.stdout)
        self.assertIn(b"comparison not attempted", proc.stdout)
        # neither safety-inspection evidence nor any comparison count may
        # appear, proving those stages were never reached
        self.assertNotIn(b"baseline ZIP safety:", proc.stdout)
        self.assertNotIn(b"byte-identical inherited files:", proc.stdout)
        self.assertNotIn(b"BASELINE_ZIP_UNSAFE", proc.stdout)

    def test_adopted_hash_constant_is_the_move80_baseline(self):
        # the constant the gate enforces must be the adopted Move 80 v07
        # hash exactly, and must appear in the gate
        self.assertEqual(len(ADOPTED_M80_SHA), 64)
        with open(GATE, encoding="utf-8") as handle:
            self.assertIn(ADOPTED_M80_SHA, handle.read())


class TestHostilePathPreBootstrap(unittest.TestCase):
    """EXECUTABLE proof that no PATH-resolved tool runs before the trusted
    bootstrap. Fake dirname/readlink/python3/sha256sum/pwd are placed FIRST
    on PATH; each records a marker when executed. The real gate is then
    run. No marker may appear."""

    # The exact set of tools a hostile PATH could try to substitute for
    # before the trusted bootstrap runs.
    HOSTILE_TOOLS = ("dirname", "basename", "readlink", "python3",
                     "sh", "sha256sum", "pwd", "realpath", "mktemp",
                     "cargo", "rustc")

    def _build_hostile_path(self, markers_dir):
        """Create fake PATH tools that each record their OWN name when
        executed. Generated with the exact validated interpreter shebang
        (never /bin/sh, which may not exist on the target), so a selected
        tool cannot fail before writing its marker and produce false
        evidence of safety."""
        os.makedirs(markers_dir, exist_ok=True)
        bindir = os.path.join(_TMP, "hostile_bin")
        os.makedirs(bindir, exist_ok=True)
        marker_file = os.path.join(markers_dir, "executed")
        for tool in self.HOSTILE_TOOLS:
            body = (
                "import sys\n"
                "with open(%r, 'a') as _h:\n"
                "    _h.write(%r + '\\n')\n"
                "    _h.flush()\n"
                "sys.exit(0)\n" % (marker_file, tool))
            path = os.path.join(bindir, tool)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("#!%s\n%s" % (PYTHON_BIN, body))
            os.chmod(path, 0o755)
        return bindir

    def test_no_pre_bootstrap_tool_is_path_resolved(self):
        markers = os.path.join(_TMP, "hostile_markers")
        import shutil
        if os.path.isdir(markers):
            shutil.rmtree(markers)
        bindir = self._build_hostile_path(markers)
        env = dict(os.environ)
        env["PATH"] = bindir + os.pathsep + env.get("PATH", "")
        # supply the required inputs so argument validation passes and the
        # gate proceeds to the pre-bootstrap trust logic
        env["REAL_MOVE78"] = "/nonexistent/m78.zip"
        env["REAL_705"] = "/nonexistent/m705.zip"
        env["REAL_MOVE79"] = "/nonexistent/m79.zip"
        env["REAL_MOVE80"] = "/nonexistent/m80.zip"
        proc = subprocess.run(
            [TEST_SH, GATE], capture_output=True, env=env,
            timeout=SUBPROCESS_TIMEOUT)
        # PLATFORM-HONEST refusal. Off Termux the literal trusted readlink
        # is absent, so the gate stops with exit 3 and the INCONCLUSIVE
        # marker. ON Termux the readlink exists, the gate proceeds, and it
        # then refuses the deliberately nonexistent baseline with exit 1.
        # Both are refusals; the suite must not depend on being off Termux.
        self.assertIn(proc.returncode, (1, 3),
                      proc.stdout + proc.stderr)
        if proc.returncode == 3:
            self.assertIn(b"INCONCLUSIVE_RUST_UNAVAILABLE", proc.stdout)
        else:
            self.assertIn(b"MOVE_81_STRUCTURED_VERDICT_ADOPTION_GATE: FAIL",
                          proc.stdout)
        # the PASS marker must never appear on a refusal
        self.assertNotIn(b"MOVE_81_STRUCTURED_VERDICT_ADOPTION_GATE: PASS",
                         proc.stdout)
        # DECISIVE, and platform-independent: no hostile PATH executable
        # ran at any point. If the boundary fails, name exactly which.
        executed = os.path.join(markers, "executed")
        if os.path.exists(executed):
            with open(executed, encoding="utf-8") as handle:
                ran = sorted({line.strip() for line in handle
                              if line.strip()})
            self.fail("PATH-resolved tool(s) executed before bootstrap: %s"
                      % ", ".join(ran))

    def test_hostile_marker_fixtures_actually_work(self):
        """POSITIVE CONTROL. The absence of a marker is only security
        evidence if the marker fixture demonstrably writes one. Invoke
        every hostile tool directly through its absolute path and require
        each to record its own name."""
        markers = os.path.join(_TMP, "hostile_control_markers")
        import shutil
        if os.path.isdir(markers):
            shutil.rmtree(markers)
        bindir = self._build_hostile_path(markers)
        for tool in self.HOSTILE_TOOLS:
            tool_path = os.path.join(bindir, tool)
            # directly executable through its absolute path: no PATH
            # lookup, no /bin/sh, no /usr/bin/env
            self.assertTrue(os.path.isfile(tool_path))
            self.assertTrue(os.access(tool_path, os.X_OK))
            proc = subprocess.run(
                [tool_path], capture_output=True,
                timeout=SUBPROCESS_TIMEOUT)
            self.assertEqual(proc.returncode, 0,
                             "hostile fixture %s failed to run: %r"
                             % (tool, proc.stderr))
        executed = os.path.join(markers, "executed")
        self.assertTrue(os.path.exists(executed),
                        "hostile fixtures wrote no marker at all")
        with open(executed, encoding="utf-8") as handle:
            recorded = {line.strip() for line in handle if line.strip()}
        self.assertEqual(recorded, set(self.HOSTILE_TOOLS),
                         "not every hostile fixture recorded its own name")

    def test_hostile_path_mutation_does_not_change_resolved_test_sh(self):
        """TEST_SH is resolved once at import, before any hostile PATH
        exists, so installing one cannot change it."""
        before = TEST_SH
        markers = os.path.join(_TMP, "hostile_sh_markers")
        bindir = self._build_hostile_path(markers)
        original_path = os.environ.get("PATH", "")
        try:
            os.environ["PATH"] = bindir + os.pathsep + original_path
            # the module-level constant is unaffected by the mutation
            self.assertEqual(TEST_SH, before)
            _require_abs_exec(TEST_SH, "TEST_SH after hostile PATH")
            self.assertNotEqual(os.path.dirname(TEST_SH), bindir)
        finally:
            os.environ["PATH"] = original_path

    def test_gate_refuses_when_script_path_is_not_the_named_gate(self):
        # copy the gate under a different name; the canonical-path check
        # must refuse it (executed, not merely inspected).
        import shutil
        alias = os.path.join(_TMP, "not_the_gate.sh")
        shutil.copyfile(GATE, alias)
        os.chmod(alias, 0o755)
        env = dict(os.environ)
        env["REAL_MOVE78"] = "/nonexistent/m78.zip"
        env["REAL_705"] = "/nonexistent/m705.zip"
        env["REAL_MOVE79"] = "/nonexistent/m79.zip"
        env["REAL_MOVE80"] = "/nonexistent/m80.zip"
        proc = subprocess.run(
            [TEST_SH, alias], capture_output=True, env=env,
            timeout=SUBPROCESS_TIMEOUT)
        # Off Termux the trusted-readlink check fires first (exit 3); on
        # Termux the canonical-name check fires (exit 1). Both are refusals
        # and neither proceeds to the gate body.
        self.assertIn(proc.returncode, (1, 3))
        self.assertNotIn(b"MOVE_81_STRUCTURED_VERDICT_ADOPTION_GATE: PASS",
                         proc.stdout)

    def test_gate_usage_error_without_required_inputs(self):
        env = dict(os.environ)
        for key in ("REAL_MOVE78", "REAL_705", "REAL_MOVE79", "REAL_MOVE80"):
            env.pop(key, None)
        proc = subprocess.run(
            [TEST_SH, GATE], capture_output=True, env=env,
            timeout=SUBPROCESS_TIMEOUT)
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"USAGE (missing:", proc.stdout)

    def test_unsafe_baseline_zip_rejected(self):
        # a ZIP carrying a traversal entry must fail safety inspection
        import zipfile
        bad = os.path.join(_TMP, "unsafe_baseline.zip")
        with zipfile.ZipFile(bad, "w") as zf:
            zf.writestr("project-witness-main/ok.txt", "x")
            zf.writestr("project-witness-main/../evil.txt", "x")
        proc = subprocess.run(
            [PYTHON_BIN, "-B", BASELINE_CHECKER, "--baseline-zip", bad,
             "--root", ROOT, "--allowlist", ALLOWLIST],
            capture_output=True, timeout=SUBPROCESS_TIMEOUT)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"BASELINE_ZIP_UNSAFE", proc.stdout)

    def test_baseline_zip_with_duplicate_names_rejected(self):
        import warnings
        import zipfile
        bad = os.path.join(_TMP, "dup_baseline.zip")
        # zipfile warns when deliberately writing a duplicate name; the
        # duplicate is the point of this fixture, and the focused suite
        # must stay stderr-clean.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(bad, "w") as zf:
                zf.writestr("project-witness-main/a.txt", "1")
                zf.writestr("project-witness-main/a.txt", "2")
        proc = subprocess.run(
            [PYTHON_BIN, "-B", BASELINE_CHECKER, "--baseline-zip", bad,
             "--root", ROOT, "--allowlist", ALLOWLIST],
            capture_output=True, timeout=SUBPROCESS_TIMEOUT)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"duplicate entry name", proc.stdout)

    def test_baseline_zip_outside_root_rejected(self):
        import zipfile
        bad = os.path.join(_TMP, "root_baseline.zip")
        with zipfile.ZipFile(bad, "w") as zf:
            zf.writestr("other-root/a.txt", "1")
        proc = subprocess.run(
            [PYTHON_BIN, "-B", BASELINE_CHECKER, "--baseline-zip", bad,
             "--root", ROOT, "--allowlist", ALLOWLIST],
            capture_output=True, timeout=SUBPROCESS_TIMEOUT)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"BASELINE_ZIP_UNSAFE", proc.stdout)

    def test_gate_invokes_exactly_one_move80_child_and_no_move79(self):
        with open(GATE, encoding="utf-8") as handle:
            text = handle.read()
        code = "\n".join(line for line in text.splitlines()
                         if not line.strip().startswith("#"))
        self.assertEqual(
            code.count('"$TRUSTED_SH" '
                       "tools/check_move80_corrupted_bundle_adoption.sh"), 1,
            "the complete Move 80 child gate must be invoked exactly once")
        # the Move 79 gate must NOT be invoked independently (the Move 80
        # child gate already composes it)
        self.assertNotIn("check_move79_instrument_adoption.sh", code)


class TestExitTwoPrecedence(unittest.TestCase):
    """Underlying exit 2 is an INVOCATION failure and takes precedence over
    all stdout/stderr framing validation. Usage text on stderr with no
    stdout must NOT become ADAPTER_UNEXPECTED_STDERR or
    ADAPTER_INCOMPLETE_RESULT."""

    def _bundle(self):
        d = os.path.join(_TMP, "e2bundle")
        os.makedirs(d, exist_ok=True)
        return d

    def _assert_invocation_error(self, rc, out):
        self.assertEqual(rc, schema.MEASUREMENT_ERROR_EXIT)
        obj = json.loads(out)
        self.assertEqual(obj["record_type"], "measurement_error")
        self.assertEqual(obj["measurement_error_code"],
                         "ADAPTER_INVOCATION_ERROR")
        # the exit code IS honestly established here (normal completion)
        self.assertEqual(obj["exit_code"], 2)
        self.assertNotIn("verdict", obj)
        return obj

    def test_python_exit2_usage_text_on_stderr(self):
        fake = _write_exe(
            "e2_py.py",
            "import sys\n"
            "sys.stderr.write('usage: companion.py [-h] ...\\n')\n"
            "sys.exit(2)\n")
        rc, out, err = _run_adapter([
            "verdict", "--lane", "python_bundle", "--input", CLEAN_BUNDLE,
            "--reason-map", REASON_MAP, "--python-bin", PYTHON_BIN,
            "--python-entry", fake])
        self._assert_invocation_error(rc, out)

    def test_rust_exit2_usage_text_on_stderr(self):
        rb = _fake_rust("e2_rust.py", "", 2,
                        stderr="usage: witness-verify <command>\n")
        rc, out, err = _run_adapter([
            "verdict", "--lane", "rust_bundle", "--input", self._bundle(),
            "--reason-map", REASON_MAP, "--rust-bin", rb])
        self._assert_invocation_error(rc, out)

    def test_archive_exit2_usage_text_on_stderr(self):
        rb = _fake_rust("e2_arch.py", "", 2,
                        stderr="usage: witness-verify inspect-archive\n")
        z = os.path.join(_TMP, "e2.zip")
        with open(z, "wb") as h:
            h.write(b"PK\x03\x04")
        rc, out, err = _run_adapter([
            "verdict", "--lane", "archive", "--input", z,
            "--reason-map", REASON_MAP, "--rust-bin", rb])
        self._assert_invocation_error(rc, out)

    def test_exit2_with_valid_looking_stdout_is_still_invocation_error(self):
        # a usage failure that ALSO prints a plausible verdict object must
        # never be reinterpreted as a verdict
        rb = _fake_rust("e2_valid.py", _RUST_INCONCLUSIVE + "\n", 2)
        rc, out, err = _run_adapter([
            "verdict", "--lane", "rust_bundle", "--input", self._bundle(),
            "--reason-map", REASON_MAP, "--rust-bin", rb])
        obj = self._assert_invocation_error(rc, out)
        self.assertNotIn("reason_code", obj)
        self.assertNotIn("stage", obj)

    def test_python_exit2_no_output_at_all(self):
        fake = _write_exe("e2_py_silent.py", "import sys\nsys.exit(2)\n")
        rc, out, err = _run_adapter([
            "verdict", "--lane", "python_bundle", "--input", CLEAN_BUNDLE,
            "--reason-map", REASON_MAP, "--python-bin", PYTHON_BIN,
            "--python-entry", fake])
        self._assert_invocation_error(rc, out)

    def test_rust_exit2_no_output_at_all(self):
        rb = _fake_rust("e2_rust_silent.py", "", 2)
        rc, out, err = _run_adapter([
            "verdict", "--lane", "rust_bundle", "--input", self._bundle(),
            "--reason-map", REASON_MAP, "--rust-bin", rb])
        self._assert_invocation_error(rc, out)


class TestExitTwoPrecedenceArchiveSilent(unittest.TestCase):
    def test_archive_exit2_no_output_at_all(self):
        rb = _fake_rust("e2_arch_silent.py", "", 2)
        z = os.path.join(_TMP, "e2b.zip")
        with open(z, "wb") as h:
            h.write(b"PK\x03\x04")
        rc, out, err = _run_adapter([
            "verdict", "--lane", "archive", "--input", z,
            "--reason-map", REASON_MAP, "--rust-bin", rb])
        self.assertEqual(rc, schema.MEASUREMENT_ERROR_EXIT)
        obj = json.loads(out)
        self.assertEqual(obj["measurement_error_code"],
                         "ADAPTER_INVOCATION_ERROR")
        self.assertEqual(obj["exit_code"], 2)


class TestCategorySemantics(unittest.TestCase):
    """Repair 4: adopted AGREEMENT / KNOWN_DIVERGENCE category semantics."""

    CONTRACT = os.path.join(
        ROOT, "verify", "agreement_harness_v01", "corpus",
        "bundle_cases.json")

    def _base(self):
        with open(self.CONTRACT, encoding="utf-8") as handle:
            return json.load(handle)

    def _write(self, name, obj):
        path = os.path.join(_TMP, name)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(obj, handle)
        return path

    def _expect_invalid(self, contract_path, tag):
        rust = _fake_rust("cs_%s.py" % tag, _RUST_INCONCLUSIVE + "\n", 3)
        rc, out, err = _run_adapter([
            "compare", "--input", CLEAN_BUNDLE, "--reason-map", REASON_MAP,
            "--python-bin", PYTHON_BIN, "--python-entry", PYTHON_ENTRY,
            "--rust-bin", rust, "--case-id", "clean_control",
            "--comparison-contract", contract_path])
        self.assertEqual(rc, schema.MEASUREMENT_ERROR_EXIT)
        self.assertEqual(err, b"")
        obj = json.loads(out)
        self.assertEqual(obj["record_type"], "measurement_error")
        self.assertEqual(obj["measurement_error_code"],
                         "ADAPTER_COMPARISON_CONTRACT_INVALID")
        self.assertEqual(obj["operation"], "compare")
        self.assertEqual(obj["input_type"], "bundle_dir")
        self.assertNotIn("comparison_status", obj)

    def test_agreement_case_with_different_classes_rejected(self):
        data = self._base()
        for case in data["cases"]:
            if case["case_id"] == "delete_top_level_checksums":
                case["expected"]["rust"]["reason_class"] = "MANIFEST_MALFORMED"
                case["expected"]["python"]["reason_class"] = \
                    "REQUIRED_FILE_MISSING"
        self._expect_invalid(
            self._write("cs_agree_cls.json", data), "agreecls")

    def test_agreement_case_with_different_stages_rejected(self):
        data = self._base()
        for case in data["cases"]:
            if case["case_id"] == "delete_top_level_checksums":
                case["expected"]["rust"]["stage"] = "receipts"
        self._expect_invalid(
            self._write("cs_agree_stg.json", data), "agreestg")

    def test_known_divergence_with_identical_class_and_stage_rejected(self):
        data = self._base()
        for case in data["cases"]:
            if case["category"] == "KNOWN_DIVERGENCE_CASE":
                py = case["expected"]["python"]
                rust = case["expected"]["rust"]
                # make them identical AND keep the metadata self-consistent
                rust["reason_class"] = py["reason_class"]
                rust["stage"] = py["stage"]
                case["expected_divergence"] = {
                    "python_class": py["reason_class"],
                    "python_stage": py["stage"],
                    "rust_class": rust["reason_class"],
                    "rust_stage": rust["stage"]}
                break
        self._expect_invalid(
            self._write("cs_div_same.json", data), "divsame")

    def test_known_divergence_changed_to_accepted_outcome_rejected(self):
        data = self._base()
        for case in data["cases"]:
            if case["category"] == "KNOWN_DIVERGENCE_CASE":
                # an "accepted divergence" is not something we may invent
                case["expected"]["normalized_outcome"] = "ACCEPTED"
                case["expected"]["python"]["verdict"] = "PASS"
                case["expected"]["python"]["exit_code"] = 0
                case["expected"]["rust"]["verdict"] = "INCONCLUSIVE"
                case["expected"]["rust"]["exit_code"] = 3
                break
        self._expect_invalid(
            self._write("cs_div_accept.json", data), "divaccept")

    def test_self_consistent_metadata_that_is_not_a_divergence_rejected(self):
        # metadata internally consistent with the lanes, but the lanes do
        # not actually diverge -> still invalid
        data = self._base()
        for case in data["cases"]:
            if case["category"] == "KNOWN_DIVERGENCE_CASE":
                py = case["expected"]["python"]
                case["expected"]["rust"]["reason_class"] = py["reason_class"]
                case["expected"]["rust"]["stage"] = py["stage"]
                case["expected_divergence"]["rust_class"] = py["reason_class"]
                case["expected_divergence"]["rust_stage"] = py["stage"]
                break
        self._expect_invalid(
            self._write("cs_div_fake.json", data), "divfake")

    def test_genuine_frozen_contract_still_accepted(self):
        rust = _fake_rust("cs_real.py", _RUST_INCONCLUSIVE + "\n", 3)
        rc, out, err = _run_adapter([
            "compare", "--input", CLEAN_BUNDLE, "--reason-map", REASON_MAP,
            "--python-bin", PYTHON_BIN, "--python-entry", PYTHON_ENTRY,
            "--rust-bin", rust, "--case-id", "clean_control",
            "--comparison-contract", self.CONTRACT])
        obj = json.loads(out)
        self.assertEqual(obj["record_type"], "comparison")
        self.assertEqual(obj["comparison_status"], "AGREEMENT")
        self.assertEqual(rc, 0)


class TestGateBootstrapProtocol(unittest.TestCase):
    """Repair 1: the adopted bootstrap protocol must be complete."""

    def _gate(self):
        with open(GATE, encoding="utf-8") as handle:
            return handle.read()

    def _code(self):
        return "\n".join(line for line in self._gate().splitlines()
                         if not line.strip().startswith("#"))

    def test_bootstrap_return_code_captured_and_classified(self):
        code = self._code()
        self.assertIn('gate_bootstrap "$GATE_INHERITED_LD_PRELOAD"', code)
        self.assertIn("BOOT_RC=$?", code)
        # exit 3 -> honest INCONCLUSIVE marker
        self.assertIn('[ "$BOOT_RC" -eq 3 ]', code)
        self.assertIn(
            "MOVE_81_STRUCTURED_VERDICT_ADOPTION_GATE: "
            "INCONCLUSIVE_RUST_UNAVAILABLE", code)
        # any other nonzero -> controlled FAIL, with the preload cases
        self.assertIn('[ "$BOOT_RC" -ne 0 ]', code)
        self.assertIn('GATE_PRELOAD_FAIL:-', code)
        self.assertIn("missing Termux exec preload", code)
        self.assertIn("untrusted Termux exec preload", code)
        self.assertIn("untrusted environment", code)

    def test_traps_installed_immediately_after_successful_bootstrap(self):
        code = self._code()
        boot = code.find("BOOT_RC=$?")
        traps = code.find("gate_install_traps")
        lib = code.find('. "$ROOT/tools/gate_lib.sh"')
        self.assertNotEqual(traps, -1, "gate_install_traps must be called")
        self.assertLess(boot, traps, "traps must follow bootstrap")
        self.assertLess(traps, lib, "traps must precede sourcing gate_lib")
        # no tracked temporary may be created before the traps
        pre_traps = code[:traps]
        self.assertNotIn("gate_track_tmp", pre_traps,
                         "no temp may be tracked before traps are installed")
        self.assertNotIn("TRUSTED_MKTEMP", pre_traps,
                         "no temp may be created before traps are installed")

    def test_nested_exec_probe_runs_before_stage_a(self):
        code = self._code()
        probe = code.find("gate_nested_exec_probe")
        stage_a = code.find("STAGE A:")
        self.assertNotEqual(probe, -1, "nested-exec probe must be called")
        self.assertNotEqual(stage_a, -1)
        self.assertLess(probe, stage_a,
                        "the probe must run before Stage A")
        self.assertIn("TERMUX_NESTED_EXEC_CHECK: PASS", code)
        self.assertIn("TERMUX_NESTED_EXEC_CHECK: FAIL", code)
        self.assertIn(
            "MOVE_81_STRUCTURED_VERDICT_ADOPTION_GATE: FAIL (nested exec)",
            code)

    def test_probe_follows_gate_lib_sourcing(self):
        code = self._code()
        lib = code.find('. "$ROOT/tools/gate_lib.sh"')
        probe = code.find("gate_nested_exec_probe")
        self.assertLess(lib, probe)

    def test_unavailable_toolchain_produces_exact_inconclusive_marker(self):
        # EXECUTED: off Termux the literal trusted readlink is absent, so
        # the gate must stop with the exact INCONCLUSIVE marker and exit 3.
        env = dict(os.environ)
        env["REAL_MOVE78"] = "/nonexistent/a.zip"
        env["REAL_705"] = "/nonexistent/b.zip"
        env["REAL_MOVE79"] = "/nonexistent/c.zip"
        env["REAL_MOVE80"] = "/nonexistent/d.zip"
        proc = subprocess.run(
            [TEST_SH, GATE], capture_output=True, env=env,
            timeout=SUBPROCESS_TIMEOUT)
        if proc.returncode == 3:
            self.assertIn(b"INCONCLUSIVE_RUST_UNAVAILABLE", proc.stdout)
        else:
            # on a real Termux host the toolchain exists and the gate
            # proceeds, then refuses the nonexistent baseline
            self.assertEqual(proc.returncode, 1)
            self.assertIn(b"MOVE_81_STRUCTURED_VERDICT_ADOPTION_GATE: FAIL",
                          proc.stdout)
        self.assertNotIn(b"MOVE_81_STRUCTURED_VERDICT_ADOPTION_GATE: PASS",
                         proc.stdout)

    def test_no_unbound_variable_abort_on_refusal(self):
        # a refusal must be a controlled marker, never a shell
        # unbound-variable abort
        env = dict(os.environ)
        env["REAL_MOVE78"] = "/nonexistent/a.zip"
        env["REAL_705"] = "/nonexistent/b.zip"
        env["REAL_MOVE79"] = "/nonexistent/c.zip"
        env["REAL_MOVE80"] = "/nonexistent/d.zip"
        proc = subprocess.run(
            [TEST_SH, GATE], capture_output=True, env=env,
            timeout=SUBPROCESS_TIMEOUT)
        combined = proc.stdout + proc.stderr
        for token in (b"unbound variable", b"parameter not set",
                      b"bad substitution"):
            self.assertNotIn(token, combined)


class TestTargetPortability(unittest.TestCase):
    """Repair: the focused suite must not assume desktop filesystem paths
    that are absent from the adopted Termux environment."""

    def _suite_source(self):
        with open(os.path.join(HERE, "structured_tests.py"),
                  encoding="utf-8") as handle:
            return handle.read()

    def _suite_code_lines(self):
        return [line for line in self._suite_source().splitlines()
                if not line.strip().startswith("#")]

    # The forbidden tokens are assembled from fragments so that this
    # scanner's OWN source does not contain them -- otherwise the check
    # would flag itself and could never pass. This keeps the scan honest
    # across the whole file, including this class.
    _SH_PATH = "/bin" + "/sh"
    _ENV_PATH = "/usr" + "/bin" + "/env"
    _SHEBANG = "#" + "!"

    def test_no_literal_bin_sh_gate_invocation(self):
        double = '"' + self._SH_PATH + '"'
        single = "'" + self._SH_PATH + "'"
        for line in self._suite_code_lines():
            self.assertNotIn(
                double, line,
                "gate subprocesses must use the resolved TEST_SH")
            self.assertNotIn(single, line)

    def test_no_env_shebang_in_any_fixture(self):
        # no fixture may be generated with an env-based shebang
        token = self._SHEBANG + self._ENV_PATH
        for line in self._suite_code_lines():
            self.assertNotIn(token, line)

    def test_no_bin_sh_shebang_in_any_fixture(self):
        token = self._SHEBANG + self._SH_PATH
        for line in self._suite_code_lines():
            self.assertNotIn(token, line)

    def test_test_sh_is_absolute_regular_executable(self):
        self.assertTrue(os.path.isabs(TEST_SH))
        self.assertTrue(os.path.isfile(TEST_SH))
        self.assertTrue(os.access(TEST_SH, os.X_OK))
        # and it is canonical (realpath of itself)
        self.assertEqual(TEST_SH, os.path.realpath(TEST_SH))

    def test_python_bin_is_absolute_regular_executable(self):
        self.assertTrue(os.path.isabs(PYTHON_BIN))
        self.assertTrue(os.path.isfile(PYTHON_BIN))
        self.assertTrue(os.access(PYTHON_BIN, os.X_OK))
        self.assertEqual(PYTHON_BIN, os.path.realpath(PYTHON_BIN))

    def test_require_abs_exec_rejects_bad_paths(self):
        with self.assertRaises(RuntimeError):
            _require_abs_exec("", "empty")
        with self.assertRaises(RuntimeError):
            _require_abs_exec("relative/path", "relative")
        with self.assertRaises(RuntimeError):
            _require_abs_exec(os.path.join(_TMP, "does_not_exist"),
                              "missing")
        # a regular, non-executable file is rejected
        plain = os.path.join(_TMP, "plain_not_exec.txt")
        with open(plain, "w", encoding="utf-8") as handle:
            handle.write("x")
        os.chmod(plain, 0o644)
        with self.assertRaises(RuntimeError):
            _require_abs_exec(plain, "non-executable")
        # a directory is rejected
        with self.assertRaises(RuntimeError):
            _require_abs_exec(_TMP, "directory")

    def test_generated_python_fixtures_carry_interpreter_shebang(self):
        fixture = _write_python_exe(
            "portability_probe.py", "import sys\nsys.exit(0)\n")
        with open(fixture, encoding="utf-8") as handle:
            first = handle.readline().rstrip("\n")
        self.assertEqual(first, "#!%s" % PYTHON_BIN)
        self.assertNotIn("/usr/bin/env", first)

    def test_fake_rust_fixture_executes_directly_without_path_lookup(self):
        # every fake Rust fixture must be directly executable by absolute
        # path, with an EMPTY PATH, proving no PATH lookup is involved
        rb = _fake_rust("portable_rust.py", _RUST_INCONCLUSIVE + "\n", 3)
        with open(rb, encoding="utf-8") as handle:
            self.assertEqual(handle.readline().rstrip("\n"),
                             "#!%s" % PYTHON_BIN)
        env = dict(os.environ)
        env["PATH"] = ""
        proc = subprocess.run(
            [rb], capture_output=True, env=env,
            timeout=SUBPROCESS_TIMEOUT)
        self.assertEqual(proc.returncode, 3)
        self.assertIn(b"INCONCLUSIVE", proc.stdout)

    def test_shell_fixture_helper_carries_shell_shebang(self):
        fixture = _write_sh_exe("portability_sh_probe.sh", "exit 0\n")
        with open(fixture, encoding="utf-8") as handle:
            first = handle.readline().rstrip("\n")
        self.assertEqual(first, "#!%s" % TEST_SH)
        proc = subprocess.run(
            [fixture], capture_output=True, timeout=SUBPROCESS_TIMEOUT)
        self.assertEqual(proc.returncode, 0)

    def test_gate_passes_trusted_shell_to_the_focused_suite(self):
        # the production gate must hand the EXACT trusted shell down
        with open(GATE, encoding="utf-8") as handle:
            gate = handle.read()
        code = "\n".join(line for line in gate.splitlines()
                         if not line.strip().startswith("#"))
        self.assertIn('MOVE81_TEST_SH="$TRUSTED_SH"', code)
        # and it must not hand down a desktop path
        desktop = 'MOVE81_TEST_SH="' + self._SH_PATH + '"'
        self.assertNotIn(desktop, code)


def _write_invalid_format_exe(name):
    """An absolute, regular, chmod-executable file whose contents are NOT
    a valid executable format. It passes every path validation the adapter
    performs, then makes the OS refuse to launch it (Errno 8, "Exec format
    error") -- the launch-time failure class that must still produce a
    clean canonical record rather than a traceback."""
    path = os.path.join(_TMP, name)
    with open(path, "wb") as handle:
        handle.write(b"\x00\x01\x02\x03 not a valid executable \xff\xfe")
    os.chmod(path, 0o755)
    return path


class TestLaunchFailureIsCleanRecord(unittest.TestCase):
    """Blocker 1: a generic launch-time OSError must become one canonical
    measurement_error, never a traceback."""

    def _bundle(self):
        d = os.path.join(_TMP, "lfbundle")
        os.makedirs(d, exist_ok=True)
        return d

    def _assert_clean_invocation_error(self, rc, out, err):
        # completely empty stderr: no traceback, no path leakage
        self.assertEqual(err, b"")
        self.assertNotIn(b"Traceback", err)
        self.assertEqual(rc, schema.MEASUREMENT_ERROR_EXIT)
        obj = json.loads(out)
        self.assertEqual(obj["record_type"], "measurement_error")
        self.assertEqual(obj["measurement_error_code"],
                         "ADAPTER_INVOCATION_ERROR")
        # the process never completed normally, so there is no honestly
        # established exit status
        self.assertNotIn("exit_code", obj)
        self.assertNotIn("verdict", obj)
        # no raw path may leak into the canonical record
        serialized = json.dumps(obj)
        self.assertNotIn(_TMP, serialized)
        self.assertNotIn("Errno", serialized)
        return obj

    def test_invalid_format_rust_bin_under_rust_bundle(self):
        bad = _write_invalid_format_exe("badexec_rust")
        rc, out, err = _run_adapter([
            "verdict", "--lane", "rust_bundle", "--input", self._bundle(),
            "--reason-map", REASON_MAP, "--rust-bin", bad])
        obj = self._assert_clean_invocation_error(rc, out, err)
        self.assertEqual(obj["implementation_lane"], "rust_bundle")

    def test_invalid_format_rust_bin_under_archive(self):
        bad = _write_invalid_format_exe("badexec_archive")
        z = os.path.join(_TMP, "lf.zip")
        with open(z, "wb") as h:
            h.write(b"PK\x03\x04")
        rc, out, err = _run_adapter([
            "verdict", "--lane", "archive", "--input", z,
            "--reason-map", REASON_MAP, "--rust-bin", bad])
        obj = self._assert_clean_invocation_error(rc, out, err)
        self.assertEqual(obj["implementation_lane"], "archive")
        self.assertEqual(obj["operation"], "inspect_archive")

    def test_invalid_format_python_bin_under_python_bundle(self):
        bad = _write_invalid_format_exe("badexec_python")
        rc, out, err = _run_adapter([
            "verdict", "--lane", "python_bundle", "--input", CLEAN_BUNDLE,
            "--reason-map", REASON_MAP, "--python-bin", bad,
            "--python-entry", PYTHON_ENTRY])
        obj = self._assert_clean_invocation_error(rc, out, err)
        self.assertEqual(obj["implementation_lane"], "python_bundle")

    def test_compare_with_one_invalid_format_attempted_lane(self):
        # the Rust lane cannot be launched; the Python lane completes
        bad = _write_invalid_format_exe("badexec_compare")
        contract = os.path.join(
            ROOT, "verify", "agreement_harness_v01", "corpus",
            "bundle_cases.json")
        rc, out, err = _run_adapter([
            "compare", "--input", CLEAN_BUNDLE, "--reason-map", REASON_MAP,
            "--python-bin", PYTHON_BIN, "--python-entry", PYTHON_ENTRY,
            "--rust-bin", bad, "--case-id", "clean_control",
            "--comparison-contract", contract])
        self.assertEqual(err, b"")
        self.assertEqual(rc, 1)
        obj = json.loads(out)
        self.assertEqual(obj["record_type"], "comparison")
        self.assertEqual(obj["comparison_status"], "MEASUREMENT_ERROR")
        # the failed attempted lane carries its COMPLETE measurement_error
        self.assertIsNotNone(obj["rust_lane"])
        self.assertEqual(obj["rust_lane"]["record_type"],
                         "measurement_error")
        self.assertEqual(obj["rust_lane"]["measurement_error_code"],
                         "ADAPTER_INVOCATION_ERROR")
        self.assertNotIn("exit_code", obj["rust_lane"])
        # the unaffected completed lane remains present, in full
        self.assertIsNotNone(obj["python_lane"])
        self.assertEqual(obj["python_lane"]["record_type"], "verdict")
        self.assertEqual(obj["python_lane"]["verdict"], "PASS")
        # neither attempted lane was replaced with null
        self.assertIsNotNone(obj["python_lane"])
        self.assertIsNotNone(obj["rust_lane"])


class TestReasonMapValidation(unittest.TestCase):
    """Blocker 2: every malformed reason-map structure fails
    deterministically, before any verifier runs, with no traceback and no
    new schema or reason code. An unusable --reason-map is adapter CLI
    misuse -- the same existing semantics an absent lane already had:
    exit 2, no record, deterministic usage text on stderr."""

    def _base(self):
        with open(REASON_MAP, encoding="utf-8") as handle:
            return json.load(handle)

    def _write(self, name, obj):
        path = os.path.join(_TMP, name)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(obj, handle)
        return path

    def _expect_usage_refusal(self, map_path, tag):
        # a canary verifier that records if it is ever launched: the map
        # is unusable, so NO verifier may run
        canary = os.path.join(_TMP, "canary_%s" % tag)
        rb = _fake_rust(
            "rmv_%s.py" % tag,
            _RUST_INCONCLUSIVE + "\n", 3)
        with open(rb, encoding="utf-8") as handle:
            body = handle.read()
        body = body.replace(
            "import sys\n",
            "import sys\nopen(%r,'a').close()\n" % canary, 1)
        with open(rb, "w", encoding="utf-8") as handle:
            handle.write(body)
        os.chmod(rb, 0o755)
        d = os.path.join(_TMP, "rmvbundle")
        os.makedirs(d, exist_ok=True)
        rc, out, err = _run_adapter([
            "verdict", "--lane", "rust_bundle", "--input", d,
            "--reason-map", map_path, "--rust-bin", rb])
        self.assertEqual(rc, schema.USAGE_EXIT,
                         "expected adapter usage refusal for %s" % tag)
        self.assertEqual(out, b"", "no record may be emitted for %s" % tag)
        self.assertNotIn(b"Traceback", err)
        self.assertNotIn(b"AttributeError", err)
        self.assertNotIn(b"KeyError", err)
        self.assertNotIn(b"TypeError", err)
        self.assertFalse(
            os.path.exists(canary),
            "a verifier was launched despite an unusable reason map (%s)"
            % tag)

    def test_non_object_lane_entry(self):
        self._expect_usage_refusal(
            self._write("rm_nonobj.json",
                        {"python_bundle": [1], "rust_bundle": [],
                         "archive": []}),
            "nonobj")

    def test_missing_match_type(self):
        data = self._base()
        data["rust_bundle"][0].pop("match_type", None)
        self._expect_usage_refusal(
            self._write("rm_nomatch.json", data), "nomatch")

    def test_unknown_match_type(self):
        data = self._base()
        data["rust_bundle"][0]["match_type"] = "fuzzy"
        self._expect_usage_refusal(
            self._write("rm_badmatch.json", data), "badmatch")

    def test_missing_value(self):
        data = self._base()
        data["rust_bundle"][0].pop("value", None)
        self._expect_usage_refusal(
            self._write("rm_noval.json", data), "noval")

    def test_non_string_value(self):
        data = self._base()
        data["rust_bundle"][0]["value"] = 17
        self._expect_usage_refusal(
            self._write("rm_intval.json", data), "intval")

    def test_malformed_regex_value(self):
        data = self._base()
        data["python_bundle"].insert(0, {
            "class": "X", "match_type": "regex", "value": "[unclosed",
            "stage": "manifest"})
        self._expect_usage_refusal(
            self._write("rm_badregex.json", data), "badregex")

    def test_missing_class(self):
        data = self._base()
        data["rust_bundle"][0].pop("class", None)
        self._expect_usage_refusal(
            self._write("rm_nocls.json", data), "nocls")

    def test_non_string_class(self):
        data = self._base()
        data["rust_bundle"][0]["class"] = ["not", "a", "string"]
        self._expect_usage_refusal(
            self._write("rm_listcls.json", data), "listcls")

    def test_missing_stage(self):
        data = self._base()
        data["rust_bundle"][0].pop("stage", None)
        self._expect_usage_refusal(
            self._write("rm_nostage2.json", data), "nostage2")

    def test_non_string_stage(self):
        data = self._base()
        data["rust_bundle"][0]["stage"] = 3
        self._expect_usage_refusal(
            self._write("rm_intstage.json", data), "intstage")

    def test_reason_map_not_an_object(self):
        self._expect_usage_refusal(
            self._write("rm_notobj.json", ["a", "b"]), "notobj")

    def test_real_frozen_reason_map_still_accepted(self):
        # the validator must NOT reject the genuine adopted authority
        loaded = adapter.load_reason_map(REASON_MAP)
        for lane in ("python_bundle", "rust_bundle", "archive"):
            self.assertIn(lane, loaded)
            self.assertTrue(loaded[lane])
        # and a real end-to-end verdict still resolves through it
        rc, out, err = _run_adapter([
            "verdict", "--lane", "python_bundle", "--input", CLEAN_BUNDLE,
            "--reason-map", REASON_MAP, "--python-bin", PYTHON_BIN,
            "--python-entry", PYTHON_ENTRY])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out)["reason_code"], "OK")


class TestGateStderrDiscipline(unittest.TestCase):
    """Blocker 3: no live adapter execution used for acceptance may
    discard stderr."""

    def _gate_lines(self):
        with open(GATE, encoding="utf-8") as handle:
            return handle.read().splitlines()

    def test_no_adapter_invocation_discards_stderr(self):
        lines = self._gate_lines()
        offenders = []
        for index, line in enumerate(lines):
            if line.strip().startswith("#"):
                continue
            if "2>/dev/null" not in line:
                continue
            context = "\n".join(lines[max(0, index - 4):index + 1])
            if "$ADAPTER" in context or "adapter.py" in context:
                offenders.append((index + 1, line.strip()))
        self.assertEqual(
            offenders, [],
            "adapter invocation(s) discard stderr: %r" % (offenders,))

    def test_both_determinism_runs_capture_stderr(self):
        text = "\n".join(l for l in self._gate_lines()
                         if not l.strip().startswith("#"))
        # both runs write stderr to a tracked temporary, and both are
        # checked with the strict emptiness policy
        self.assertIn('>"$_D1" 2>"$_DE"', text)
        self.assertIn('>"$_D2" 2>"$_DE2"', text)
        self.assertIn('[ -s "$_DE" ]', text)
        self.assertIn('[ -s "$_DE2" ]', text)
        # the second stderr file is tracked for cleanup like the first
        self.assertIn('gate_track_tmp "$_DE2"', text)

    def test_focused_suite_and_comparison_capture_stderr(self):
        text = "\n".join(l for l in self._gate_lines()
                         if not l.strip().startswith("#"))
        self.assertIn('>"$_MT_OUT" 2>"$_MT_ERR"', text)
        self.assertIn('>"$_C1" 2>"$_CE"', text)
        self.assertIn('>"$_R1" 2>"$_RE"', text)


class TestMove80ChildGateComposition(unittest.TestCase):
    """The Move 80 gate validates ITS tree against Move 79 and permits only
    the Move 80 addition set, so it must run from a private extracted copy
    of the adopted baseline -- never from the Move 81 candidate root, whose
    legitimate additions would look undeclared relative to Move 79."""

    def _gate_code(self):
        with open(GATE, encoding="utf-8") as handle:
            text = handle.read()
        return "\n".join(line for line in text.splitlines()
                         if not line.strip().startswith("#"))

    def _make_baseline_zip(self, name, extra_members=(), root="project-witness-main"):
        """A synthetic, self-contained stand-in for the adopted baseline:
        a single canonical root containing the Move 80 gate path."""
        import zipfile
        path = os.path.join(_TMP, name)
        with zipfile.ZipFile(path, "w") as zf:
            # built from fragments so this suite never contains a
            # literal desktop shebang (see TestTargetPortability)
            stub = "#" + "!" + TEST_SH + "\nexit 0\n"
            zf.writestr(
                "%s/tools/check_move80_corrupted_bundle_adoption.sh" % root,
                stub)
            zf.writestr("%s/README.md" % root, "baseline stand-in\n")
            for member, content in extra_members:
                zf.writestr(member, content)
        return path

    def _sha256(self, path):
        import hashlib
        with open(path, "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()

    def _extract(self, zip_path, dest, expect=None):
        args = [PYTHON_BIN, "-B", BASELINE_CHECKER,
                "--baseline-zip", zip_path, "--extract-to", dest]
        if expect is not None:
            args += ["--expect-sha256", expect]
        return subprocess.run(args, capture_output=True,
                              timeout=SUBPROCESS_TIMEOUT)

    # ---- executable extraction behaviour ----

    def test_valid_baseline_extracts_and_reports_root(self):
        z = self._make_baseline_zip("comp_ok.zip")
        dest = os.path.join(_TMP, "comp_ok_dest")
        os.makedirs(dest, exist_ok=True)
        proc = self._extract(z, dest, self._sha256(z))
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertEqual(proc.stderr, b"")
        self.assertIn(b"MOVE_81_BASELINE_EXTRACT: PASS", proc.stdout)
        self.assertIn(b"EXTRACTED_ROOT: ", proc.stdout)
        root = os.path.join(dest, "project-witness-main")
        self.assertTrue(os.path.isdir(root))
        self.assertTrue(os.path.isfile(os.path.join(
            root, "tools", "check_move80_corrupted_bundle_adoption.sh")))

    def test_hash_mismatch_fails_before_extraction(self):
        z = self._make_baseline_zip("comp_badhash.zip")
        dest = os.path.join(_TMP, "comp_badhash_dest")
        os.makedirs(dest, exist_ok=True)
        proc = self._extract(z, dest, "0" * 64)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"BASELINE_HASH_MISMATCH", proc.stdout)
        self.assertIn(b"extraction and comparison not attempted",
                      proc.stdout)
        # nothing was written: extraction was never reached
        self.assertEqual(os.listdir(dest), [])
        self.assertNotIn(b"baseline ZIP safety:", proc.stdout)

    def test_unsafe_baseline_rejected_before_extraction(self):
        z = self._make_baseline_zip(
            "comp_unsafe.zip",
            extra_members=(("project-witness-main/../evil.txt", "x"),))
        dest = os.path.join(_TMP, "comp_unsafe_dest")
        os.makedirs(dest, exist_ok=True)
        proc = self._extract(z, dest, self._sha256(z))
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"BASELINE_ZIP_UNSAFE", proc.stdout)
        self.assertIn(b"MOVE_81_BASELINE_EXTRACT: FAIL", proc.stdout)
        # nothing escaped and nothing was written
        self.assertEqual(os.listdir(dest), [])
        self.assertFalse(os.path.exists(
            os.path.join(os.path.dirname(dest), "evil.txt")))

    def test_second_root_rejected_before_extraction(self):
        z = self._make_baseline_zip(
            "comp_tworoot.zip",
            extra_members=(("other-root/x.txt", "x"),))
        dest = os.path.join(_TMP, "comp_tworoot_dest")
        os.makedirs(dest, exist_ok=True)
        proc = self._extract(z, dest, self._sha256(z))
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"BASELINE_ZIP_UNSAFE", proc.stdout)
        self.assertEqual(os.listdir(dest), [])

    def test_move81_additions_cannot_contaminate_extracted_tree(self):
        # The decisive property: the extracted baseline contains NONE of
        # the declared Move 81 additions, so the Move 80 gate's
        # inherited-tree comparison cannot see them.
        z = self._make_baseline_zip("comp_clean.zip")
        dest = os.path.join(_TMP, "comp_clean_dest")
        os.makedirs(dest, exist_ok=True)
        proc = self._extract(z, dest, self._sha256(z))
        self.assertEqual(proc.returncode, 0)
        root = os.path.join(dest, "project-witness-main")
        with open(ALLOWLIST, encoding="utf-8") as handle:
            additions = json.load(handle)["added_paths"]
        self.assertTrue(additions)
        for rel in additions:
            self.assertFalse(
                os.path.exists(os.path.join(root, rel)),
                "Move 81 addition leaked into the extracted baseline: %s"
                % rel)
        # and the extraction destination is disjoint from the candidate
        self.assertFalse(os.path.realpath(root).startswith(
            os.path.realpath(ROOT) + os.sep))

    def test_paths_containing_spaces_supported(self):
        spaced_dir = os.path.join(_TMP, "dir with spaces")
        os.makedirs(spaced_dir, exist_ok=True)
        z = self._make_baseline_zip(
            os.path.join("dir with spaces", "base line.zip"))
        dest = os.path.join(_TMP, "dest with spaces")
        os.makedirs(dest, exist_ok=True)
        proc = self._extract(z, dest, self._sha256(z))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertTrue(os.path.isfile(os.path.join(
            dest, "project-witness-main", "tools",
            "check_move80_corrupted_bundle_adoption.sh")))

    def test_extraction_uses_no_path_lookup(self):
        # the extractor runs under an EMPTY PATH: it performs no PATH
        # lookup of its own
        z = self._make_baseline_zip("comp_nopath.zip")
        dest = os.path.join(_TMP, "comp_nopath_dest")
        os.makedirs(dest, exist_ok=True)
        env = dict(os.environ)
        env["PATH"] = ""
        proc = subprocess.run(
            [PYTHON_BIN, "-B", BASELINE_CHECKER, "--baseline-zip", z,
             "--extract-to", dest, "--expect-sha256", self._sha256(z)],
            capture_output=True, env=env, timeout=SUBPROCESS_TIMEOUT)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_trap_cleanup_mechanism_removes_a_directory(self):
        # The gate registers the extraction directory with gate_track_tmp,
        # whose adopted cleanup removes every tracked item under an EXIT
        # trap. This probe proves that trap-and-remove contract: the trap
        # fires on exit and every tracked item is gone afterwards.
        #
        # The removal here is performed through the absolute validated
        # interpreter rather than a bare `rm`, so the probe itself needs no
        # PATH and runs identically with PATH empty. In production the
        # adopted gate_cleanup calls `rm -rf`, which resolves through the
        # TRUSTED PATH the bootstrap installs (see the assertion below), so
        # a hostile PATH cannot substitute the cleanup tool there either.
        victim = os.path.join(_TMP, "trap_victim")
        os.makedirs(os.path.join(victim, "nested"), exist_ok=True)
        with open(os.path.join(victim, "nested", "f.txt"), "w") as handle:
            handle.write("x")
        script = _write_sh_exe(
            "trap_probe.sh",
            'ITEMS=""\n'
            'track() { ITEMS="$ITEMS $1"; }\n'
            'cleanup() { for i in $ITEMS; do [ -n "$i" ] && '
            '"%s" -c "import shutil,sys;'
            'shutil.rmtree(sys.argv[1], ignore_errors=True)" "$i"; '
            'done; }\n'
            'trap cleanup EXIT\n'
            'track "%s"\n'
            'exit 0\n' % (PYTHON_BIN, victim))
        proc = subprocess.run([script], capture_output=True,
                              timeout=SUBPROCESS_TIMEOUT)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(os.path.exists(victim),
                         "trap cleanup did not remove the tracked directory")

    def test_bootstrap_installs_a_trusted_path_for_cleanup_tools(self):
        # A hostile PATH cannot replace the cleanup/extraction tools the
        # gate relies on, because the adopted bootstrap REPLACES PATH with
        # a trusted one before any stage runs.
        with open(os.path.join(ROOT, "tools", "gate_bootstrap.sh"),
                  encoding="utf-8") as handle:
            bootstrap = handle.read()
        self.assertIn("GATE_TRUSTED_PATH=", bootstrap)
        self.assertIn("export PATH=", bootstrap)
        self.assertIn("/data/data/com.termux/files/usr", bootstrap)
        # and the Move 81 gate sources that bootstrap before any stage
        code = self._gate_code()
        boot = code.find('. "$ROOT/tools/gate_bootstrap.sh"')
        stage_a = code.find("STAGE A")
        self.assertNotEqual(boot, -1)
        self.assertLess(boot, stage_a)

    # ---- gate composition structure ----

    def test_child_gate_runs_from_extracted_root_not_candidate_root(self):
        code = self._gate_code()
        # the child is invoked inside a subshell that cds into the
        # extracted baseline root
        self.assertIn('( cd "$_M80_ROOT" \\', code)
        self.assertIn('_M80_ROOT="$_M80_EXTRACT/project-witness-main"',
                      code)
        child = "tools/check_move80_corrupted_bundle_adoption.sh"
        # exactly one invocation of the child gate
        self.assertEqual(
            code.count('"$TRUSTED_SH" ' + child), 1,
            "the Move 80 child gate must be invoked exactly once")
        invocation = code.find('"$TRUSTED_SH" ' + child)
        cd_pos = code.find('( cd "$_M80_ROOT"')
        self.assertNotEqual(cd_pos, -1)
        self.assertLess(cd_pos, invocation,
                        "the child gate must be launched from inside the "
                        "extracted Move 80 tree")

    def test_extraction_precedes_child_invocation(self):
        code = self._gate_code()
        extract = code.find("--extract-to")
        child = code.find('"$TRUSTED_SH" '
                          "tools/check_move80_corrupted_bundle_adoption.sh")
        self.assertNotEqual(extract, -1)
        self.assertLess(extract, child)

    def test_extract_dir_tracked_for_trap_cleanup(self):
        code = self._gate_code()
        self.assertIn('gate_track_tmp "$_M80_EXTRACT"', code)
        # and removed promptly on the success path too
        self.assertIn('rm -rf "$_M80_EXTRACT"', code)
        # tracking happens before the extraction that populates it
        self.assertLess(code.find('gate_track_tmp "$_M80_EXTRACT"'),
                        code.find("--extract-to"))

    def test_child_nonzero_exit_fails_stage_f(self):
        code = self._gate_code()
        self.assertIn('if [ "$_m80_rc" -ne 0 ]; then', code)
        self.assertIn("Move 80 child adoption gate failed", code)
        self.assertIn('die "move80 regression"', code)

    def test_child_stdout_and_stderr_retained(self):
        code = self._gate_code()
        self.assertIn(
            "---- BEGIN COMPLETE MOVE 80 CHILD GATE OUTPUT (retained) ----",
            code)
        self.assertIn(
            "---- END COMPLETE MOVE 80 CHILD GATE OUTPUT ----", code)
        # combined stream captured, then printed in full
        self.assertIn('>"$_M80_OUT" 2>&1', code)
        self.assertIn('cat "$_M80_OUT"', code)
        # extraction evidence retained too
        self.assertIn(
            "---- BEGIN REAL_MOVE80 VALIDATED EXTRACTION EVIDENCE ----",
            code)

    def test_adopted_dependencies_forwarded_to_child(self):
        code = self._gate_code()
        for var in ("REAL_MOVE78", "REAL_705", "REAL_MOVE79"):
            self.assertIn('%s="$%s"' % (var, var), code)

    def test_extraction_and_child_use_only_trusted_tools(self):
        code = self._gate_code()
        # extraction directory, extraction, hashing, shell: all trusted
        self.assertIn('_M80_EXTRACT=$("$TRUSTED_MKTEMP" -d)', code)
        self.assertIn('"$TRUSTED_PYTHON3" -B "$P/check_move81_inherited.py"',
                      code)
        self.assertIn('_M80_SHA=$("$TRUSTED_SHA256SUM" "$M80_ZIP")', code)
        self.assertIn('"$TRUSTED_SH" '
                      "tools/check_move80_corrupted_bundle_adoption.sh",
                      code)
        # no bare tool names in the Stage F region
        start = code.find("STAGE F")
        region = code[start:start + 3000] if start != -1 else ""
        for bare in ("$(mktemp", "`mktemp", "$(sha256sum", "`sha256sum",
                     "$(unzip", "`unzip"):
            self.assertNotIn(bare, region)

    def test_move80_gate_is_not_modified_or_overlaid(self):
        code = self._gate_code()
        # nothing is copied or overlaid into the extracted tree
        for forbidden in ('cp -r "$P"', 'cp -a "$P"',
                          'cp "$P"', "rsync"):
            self.assertNotIn(forbidden, code)
        # the Move 80 gate file itself is inherited byte-identical, which
        # the Stage A baseline comparison already proves; assert here that
        # the Move 81 gate never writes to it
        self.assertNotIn("check_move80_corrupted_bundle_adoption.sh >",
                         code)


if __name__ == "__main__":
    _suite = unittest.defaultTestLoader.loadTestsFromModule(
        sys.modules[__name__])
    _result = unittest.TextTestRunner(
        stream=sys.stdout, verbosity=1).run(_suite)
    sys.exit(0 if _result.wasSuccessful() else 1)
