#!/usr/bin/env python3
"""Move 84 focused test suite.

Stdout-bound runner, pinned count, warning-clean, target-portable.

Scope note, stated plainly: this environment has no Rust toolchain, so the
adopted `witness-verify` binary cannot be built or executed here. The
Python lane IS genuinely executed. Rust-lane behaviour is exercised
end-to-end through the real demo driver using a stand-in verifier, which
proves the driver's logic but establishes nothing about the adopted
binary. The adopted binary is the authority only in the on-device gate.
"""

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import build_demo_fixtures as fixtures  # noqa: E402

GATE = os.path.join(ROOT, "tools", "check_move84_demo_adoption.sh")
ALLOWLIST = os.path.join(HERE, "allowlist_move84.json")
README = os.path.join(HERE, "README.md")
FIXTURE_TOOL = os.path.join(HERE, "build_demo_fixtures.py")
DEMO_TOOL = os.path.join(HERE, "demo.py")
FROZEN_BUNDLE = os.path.join(
    ROOT, "freeze_record", "python_behaviour_freeze_v01", "reference_bundle")
COMPANION = os.path.join(
    ROOT, "src", "12_companion_cli_v031", "companion.py")

ADOPTED_M83_SHA = \
    "aa06feb870ec3d72ff7c942fe8c0752efff313cbbdab6e280302dba288975a6c"

SUBPROCESS_TIMEOUT = 300


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
    supplied = os.environ.get("MOVE84_TEST_SH")
    if supplied:
        return _require_abs_exec(os.path.realpath(supplied),
                                 "MOVE84_TEST_SH (trusted shell)")
    found = shutil.which("sh")
    if not found:
        raise RuntimeError(
            "no shell available: set MOVE84_TEST_SH to the trusted shell")
    return _require_abs_exec(os.path.realpath(found), "fallback shell")


TEST_SH = _resolve_test_sh()

_TMP = None


def setUpModule():
    global _TMP
    import tempfile
    _TMP = tempfile.mkdtemp(prefix="m84_tests_")


def tearDownModule():
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


CLEAN_LINE = ('{"verifier": "witness-verify", "version": '
              '"0.0.8-step79-diagnostics", "verdict": "%s", '
              '"reason_code": "%s", "detail": "ok"}')


def _standin(name, clean_digest, fail_reason="A_DETECTED_MISMATCH",
             clean_verdict="INCONCLUSIVE", clean_exit=3,
             fail_verdict="FAIL", fail_exit=1):
    """A stand-in reproducing the ADOPTED shape: a clean bundle and a
    nested-evidence tamper are indistinguishable, while a top-level
    declared-file tamper is detected. It is a test double for the driver,
    never an authority for what the adopted binary actually does."""
    body = (
        "import hashlib, os, sys\n"
        "root = sys.argv[-1]\n"
        "top = os.path.join(root, %r)\n"
        "with open(top, 'rb') as handle:\n"
        "    digest = hashlib.sha256(handle.read()).hexdigest()\n"
        "if digest != %r:\n"
        "    sys.stdout.write(%r + chr(10))\n"
        "    sys.exit(%d)\n"
        "sys.stdout.write(%r + chr(10))\n"
        "sys.exit(%d)\n"
        % (fixtures.TOPLEVEL_DECLARED, clean_digest,
           CLEAN_LINE % (fail_verdict, fail_reason), fail_exit,
           CLEAN_LINE % (clean_verdict, "RECEIPT_CHAIN_HASHES_RECOMPUTED"),
           clean_exit))
    return _write_python_exe(name, body)


class DemoHarness(unittest.TestCase):
    """Shared fixture construction and driver invocation."""

    def _fixtures(self, tag):
        outdir = os.path.join(_TMP, "fx_" + tag)
        manifest = os.path.join(_TMP, "fx_%s.json" % tag)
        proc = _run([PYTHON_BIN, "-B", FIXTURE_TOOL,
                     "--source", FROZEN_BUNDLE, "--outdir", outdir,
                     "--manifest-out", manifest])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        with open(manifest, encoding="utf-8") as handle:
            return manifest, json.load(handle)["cases"]

    def _clean_digest(self, cases):
        clean = [c for c in cases if c["case_id"] == "clean"][0]
        target = os.path.join(clean["root"], fixtures.TOPLEVEL_DECLARED)
        with open(target, "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()

    def _establish(self, tag, manifest, verifier):
        out = os.path.join(_TMP, "exp_%s.json" % tag)
        proc = _run([PYTHON_BIN, "-B", DEMO_TOOL, "--mode", "establish",
                     "--verifier", verifier, "--python-bin", PYTHON_BIN,
                     "--companion", COMPANION, "--fixtures", manifest,
                     "--expectations-out", out])
        return proc, out

    def _demonstrate(self, tag, manifest, verifier, expectations):
        transcript = os.path.join(_TMP, "tr_%s.txt" % tag)
        proc = _run([PYTHON_BIN, "-B", DEMO_TOOL, "--mode", "demonstrate",
                     "--verifier", verifier, "--python-bin", PYTHON_BIN,
                     "--companion", COMPANION, "--fixtures", manifest,
                     "--expectations", expectations,
                     "--transcript-out", transcript])
        return proc, transcript

    def _setup(self, tag, **kw):
        manifest, cases = self._fixtures(tag)
        verifier = _standin("sv_%s.py" % tag, self._clean_digest(cases),
                            **kw)
        return manifest, cases, verifier


class TestFixtureConstruction(DemoHarness):
    """A4: minimum new fixture, deterministic, exactly the declared
    mutation, independently verified, no authored Rust verdict."""

    def test_three_cases_are_built(self):
        _manifest, cases = self._fixtures("three")
        self.assertEqual([c["case_id"] for c in cases],
                         list(fixtures.CASES))

    def test_clean_case_is_unmutated(self):
        _manifest, cases = self._fixtures("clean")
        clean = [c for c in cases if c["case_id"] == "clean"][0]
        self.assertIsNone(clean["mutation"])
        self.assertEqual(clean["changed_files"], [])

    def test_toplevel_case_mutates_a_declared_file(self):
        _manifest, cases = self._fixtures("top")
        case = [c for c in cases if c["case_id"] == "toplevel_tamper"][0]
        self.assertEqual(case["changed_files"],
                         [fixtures.TOPLEVEL_DECLARED])
        with open(os.path.join(FROZEN_BUNDLE, "companion_checksums.txt"),
                  encoding="utf-8") as handle:
            declared = [line.split()[1] for line in handle if line.strip()]
        self.assertIn(fixtures.TOPLEVEL_DECLARED, declared)

    def test_nested_case_mutates_the_genuine_evidence_payload(self):
        _manifest, cases = self._fixtures("nested")
        case = [c for c in cases
                if c["case_id"] == "nested_evidence_tamper"][0]
        self.assertEqual(case["changed_files"],
                         [fixtures.NESTED_EVIDENCE.replace(os.sep, "/")])

    def test_nested_target_is_absent_from_the_toplevel_checksums(self):
        """This is precisely why the Rust lane is blind to it."""
        with open(os.path.join(FROZEN_BUNDLE, "companion_checksums.txt"),
                  encoding="utf-8") as handle:
            self.assertNotIn("evidence_001.bin", handle.read())

    def test_exactly_one_file_changes_per_tamper_case(self):
        _manifest, cases = self._fixtures("one")
        for case in cases:
            if case["mutation"] is None:
                self.assertEqual(case["changed_files"], [])
            else:
                self.assertEqual(len(case["changed_files"]), 1)

    def test_the_file_set_never_changes(self):
        _manifest, cases = self._fixtures("set")
        counts = {c["file_count"] for c in cases}
        self.assertEqual(len(counts), 1)

    def test_mutation_is_the_frozen_byte_flip(self):
        _manifest, cases = self._fixtures("flip")
        for case in cases:
            mutation = case["mutation"]
            if mutation is None:
                continue
            self.assertEqual(mutation["offset"], fixtures.FLIP_OFFSET)
            self.assertEqual(mutation["operation"], "xor")
            self.assertEqual(mutation["operand"], fixtures.FLIP_XOR)
            self.assertEqual(mutation["byte_before"] ^ fixtures.FLIP_XOR,
                             mutation["byte_after"])

    def test_mutation_is_independently_verified_on_disk(self):
        _manifest, cases = self._fixtures("verify")
        for case in cases:
            mutation = case["mutation"]
            if mutation is None:
                continue
            target = os.path.join(case["root"], mutation["path"])
            with open(target, "rb") as handle:
                self.assertEqual(handle.read()[mutation["offset"]],
                                 mutation["byte_after"])
            original = os.path.join(FROZEN_BUNDLE, mutation["path"])
            with open(original, "rb") as handle:
                self.assertEqual(handle.read()[mutation["offset"]],
                                 mutation["byte_before"])

    def test_every_other_file_is_byte_identical_to_the_frozen_bundle(self):
        _manifest, cases = self._fixtures("identical")
        frozen = fixtures.tree_hashes(FROZEN_BUNDLE)
        for case in cases:
            built = fixtures.tree_hashes(case["root"])
            self.assertEqual(set(built), set(frozen))
            differing = sorted(k for k in frozen if frozen[k] != built[k])
            self.assertEqual(differing, case["changed_files"])

    def test_construction_is_reproducible(self):
        _m1, first = self._fixtures("rep1")
        _m2, second = self._fixtures("rep2")
        for a, b in zip(first, second):
            self.assertEqual(a["tree_digest"], b["tree_digest"])
            self.assertEqual(a["mutation"], b["mutation"])

    def test_no_expected_rust_verdict_is_authored(self):
        with open(FIXTURE_TOOL, encoding="utf-8") as handle:
            source = handle.read()
        for token in ("INCONCLUSIVE", "RECEIPT_CHAIN", "reason_code"):
            self.assertNotIn('"%s"' % token, source, token)

    def test_relative_paths_are_refused(self):
        proc = _run([PYTHON_BIN, "-B", FIXTURE_TOOL, "--source", "rel",
                     "--outdir", "rel2"])
        self.assertEqual(proc.returncode, 2)


class TestPythonLaneIsGenuinelyExecuted(DemoHarness):
    """The Python lane genuinely runs in this environment."""

    def _python(self, root):
        return _run([PYTHON_BIN, "-B", COMPANION, "verify", "--run", root])

    def test_python_accepts_the_clean_bundle(self):
        _manifest, cases = self._fixtures("pyclean")
        clean = [c for c in cases if c["case_id"] == "clean"][0]
        proc = self._python(clean["root"])
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertEqual(proc.stderr, b"")
        self.assertTrue(json.loads(proc.stdout)["verify_ok"])

    def test_python_detects_the_nested_evidence_tamper(self):
        _manifest, cases = self._fixtures("pynested")
        case = [c for c in cases
                if c["case_id"] == "nested_evidence_tamper"][0]
        proc = self._python(case["root"])
        self.assertEqual(proc.returncode, 1)
        record = json.loads(proc.stdout)
        self.assertFalse(record["verify_ok"])
        self.assertIn("evidence_001.bin", record["error"])

    def test_python_detects_the_toplevel_tamper(self):
        _manifest, cases = self._fixtures("pytop")
        case = [c for c in cases if c["case_id"] == "toplevel_tamper"][0]
        proc = self._python(case["root"])
        self.assertEqual(proc.returncode, 1)
        self.assertFalse(json.loads(proc.stdout)["verify_ok"])


class TestDemoDriverEndToEnd(DemoHarness):
    """The producer/consumer path, run for real with a stand-in."""

    def test_establish_then_demonstrate_succeeds(self):
        manifest, _cases, verifier = self._setup("e2e")
        proc, expectations = self._establish("e2e", manifest, verifier)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        proc, _transcript = self._demonstrate("e2e", manifest, verifier,
                                              expectations)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn(b"MOVE_84_DEMO: PASS", proc.stdout)
        self.assertEqual(proc.stderr, b"")

    def test_transcript_is_deterministic(self):
        manifest, _cases, verifier = self._setup("det")
        _proc, expectations = self._establish("det", manifest, verifier)
        _p1, t1 = self._demonstrate("det1", manifest, verifier,
                                    expectations)
        _p2, t2 = self._demonstrate("det2", manifest, verifier,
                                    expectations)
        with open(t1, "rb") as a, open(t2, "rb") as b:
            self.assertEqual(a.read(), b.read())

    def test_transcript_carries_no_nondeterministic_content(self):
        manifest, _cases, verifier = self._setup("nondet")
        _proc, expectations = self._establish("nondet", manifest, verifier)
        _p, transcript = self._demonstrate("nondet", manifest, verifier,
                                           expectations)
        with open(transcript, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIsNone(re.search(r"\d{4}-\d{2}-\d{2}", text))
        self.assertIsNone(re.search(r"\d+\.\d+s", text))
        self.assertNotIn(_TMP, text)
        self.assertNotIn("/home/", text)
        self.assertNotIn("/data/data/", text)

    def test_transcript_never_calls_the_rust_result_a_pass(self):
        manifest, _cases, verifier = self._setup("nopass")
        _proc, expectations = self._establish("nopass", manifest, verifier)
        _p, transcript = self._demonstrate("nopass", manifest, verifier,
                                           expectations)
        with open(transcript, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        in_rust = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("RUST lane"):
                in_rust = True
                continue
            if stripped.startswith("PYTHON lane") or \
                    stripped.startswith("CASE:"):
                in_rust = False
            if in_rust and stripped.startswith("verdict"):
                self.assertNotIn("PASS", stripped)

    def test_transcript_states_the_nested_blindness(self):
        manifest, _cases, verifier = self._setup("blind")
        _proc, expectations = self._establish("blind", manifest, verifier)
        _p, transcript = self._demonstrate("blind", manifest, verifier,
                                           expectations)
        with open(transcript, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("DOES NOT", text)
        self.assertIn("nested evidence payload", text)

    def test_transcript_states_what_it_does_not_establish(self):
        manifest, _cases, verifier = self._setup("limits")
        _proc, expectations = self._establish("limits", manifest, verifier)
        _p, transcript = self._demonstrate("limits", manifest, verifier,
                                           expectations)
        with open(transcript, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("universally valid", text)
        self.assertIn("detects every tamper", text)
        self.assertIn("It cannot", text)

    def test_transcript_shows_both_lanes_for_every_case(self):
        manifest, _cases, verifier = self._setup("lanes")
        _proc, expectations = self._establish("lanes", manifest, verifier)
        _p, transcript = self._demonstrate("lanes", manifest, verifier,
                                           expectations)
        with open(transcript, encoding="utf-8") as handle:
            text = handle.read()
        self.assertEqual(text.count("PYTHON lane"), 3)
        self.assertEqual(text.count("RUST lane"), 3)
        for case_id in fixtures.CASES:
            self.assertIn("CASE: %s" % case_id, text)

    # ---- fail-closed behaviour --------------------------------------

    def test_a_verifier_claiming_pass_is_rejected(self):
        manifest, cases = self._fixtures("passliar")
        verifier = _standin("sv_passliar.py", self._clean_digest(cases),
                            clean_verdict="PASS", clean_exit=0)
        proc, _out = self._establish("passliar", manifest, verifier)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"no reachable PASS path", proc.stdout)

    def test_a_verifier_that_never_detects_is_rejected(self):
        manifest, cases = self._fixtures("nofail")
        verifier = _standin("sv_nofail.py", self._clean_digest(cases),
                            fail_verdict="INCONCLUSIVE", fail_exit=3)
        proc, _out = self._establish("nofail", manifest, verifier)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"did not detect a tamper", proc.stdout)

    def test_a_verifier_detecting_the_nested_tamper_is_rejected(self):
        """If the adopted verifier ever gains nested detection, the demo
        must fail loudly rather than keep asserting the old limitation."""
        manifest, _cases = self._fixtures("seesnested")
        body = (
            "import os, sys\n"
            "root = sys.argv[-1]\n"
            "target = os.path.join(root, %r)\n"
            "with open(target, 'rb') as handle:\n"
            "    data = handle.read()\n"
            "if data[%d] != %d:\n"
            "    sys.stdout.write(%r + chr(10))\n"
            "    sys.exit(1)\n"
            "sys.stdout.write(%r + chr(10))\n"
            "sys.exit(3)\n"
            % (fixtures.NESTED_EVIDENCE, fixtures.FLIP_OFFSET, 0x65,
               CLEAN_LINE % ("FAIL", "NESTED_DETECTED"),
               CLEAN_LINE % ("INCONCLUSIVE",
                             "RECEIPT_CHAIN_HASHES_RECOMPUTED")))
        verifier = _write_python_exe("sv_seesnested.py", body)
        proc, _out = self._establish("seesnested", manifest, verifier)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"not INCONCLUSIVE", proc.stdout)

    def test_a_verifier_emitting_stderr_is_rejected(self):
        manifest, _cases = self._fixtures("stderr")
        body = ("import sys\n"
                "sys.stderr.write('warning' + chr(10))\n"
                "sys.stdout.write(%r + chr(10))\n"
                "sys.exit(3)\n"
                % (CLEAN_LINE % ("INCONCLUSIVE", "R"),))
        verifier = _write_python_exe("sv_stderr.py", body)
        proc, _out = self._establish("stderr", manifest, verifier)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"emitted stderr", proc.stdout)

    def test_a_verifier_with_a_mismatched_exit_is_rejected(self):
        manifest, cases = self._fixtures("badexit")
        verifier = _standin("sv_badexit.py", self._clean_digest(cases),
                            fail_exit=2)
        proc, _out = self._establish("badexit", manifest, verifier)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"must exit 1", proc.stdout)

    def test_a_changed_observation_fails_against_the_authority(self):
        manifest, cases = self._fixtures("drift")
        digest = self._clean_digest(cases)
        verifier = _standin("sv_drift_a.py", digest)
        _proc, expectations = self._establish("drift", manifest, verifier)
        drifted = _standin("sv_drift_b.py", digest,
                           fail_reason="A_DIFFERENT_REASON")
        proc, _t = self._demonstrate("drift", manifest, drifted,
                                     expectations)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"differs from the adopted authority", proc.stdout)

    def test_demonstrate_requires_expectations(self):
        manifest, cases = self._fixtures("noexp")
        verifier = _standin("sv_noexp.py", self._clean_digest(cases))
        proc = _run([PYTHON_BIN, "-B", DEMO_TOOL, "--mode", "demonstrate",
                     "--verifier", verifier, "--python-bin", PYTHON_BIN,
                     "--companion", COMPANION, "--fixtures", manifest])
        self.assertEqual(proc.returncode, 2)

    def test_mutating_a_bundle_changes_the_demonstration(self):
        """Proves the demo reads the bundles rather than replaying text."""
        manifest, cases = self._fixtures("reads")
        verifier = _standin("sv_reads.py", self._clean_digest(cases))
        _proc, expectations = self._establish("reads", manifest, verifier)
        clean = [c for c in cases if c["case_id"] == "clean"][0]
        target = os.path.join(clean["root"], fixtures.TOPLEVEL_DECLARED)
        with open(target, "rb") as handle:
            data = bytearray(handle.read())
        data[7] ^= 0xFF
        with open(target, "wb") as handle:
            handle.write(bytes(data))
        proc, _t = self._demonstrate("reads", manifest, verifier,
                                     expectations)
        self.assertEqual(proc.returncode, 1)

    def test_relative_paths_are_refused(self):
        proc = _run([PYTHON_BIN, "-B", DEMO_TOOL, "--mode", "establish",
                     "--verifier", "rel", "--python-bin", "rel",
                     "--companion", "rel", "--fixtures", "rel"])
        self.assertEqual(proc.returncode, 2)


class TestInheritedBaselineIsAdditiveOnly(unittest.TestCase):
    """A5: no Rust change; rust/ stays byte-identical."""

    def test_allowlist_declares_no_modifications(self):
        with open(ALLOWLIST, encoding="utf-8") as handle:
            data = json.load(handle)
        self.assertEqual(data["modified_paths"], [])
        self.assertEqual(data["added_paths"], sorted(data["added_paths"]))

    def test_every_declared_addition_exists(self):
        with open(ALLOWLIST, encoding="utf-8") as handle:
            data = json.load(handle)
        for rel in data["added_paths"]:
            self.assertTrue(os.path.isfile(os.path.join(ROOT, rel)), rel)

    def test_no_addition_touches_rust(self):
        with open(ALLOWLIST, encoding="utf-8") as handle:
            data = json.load(handle)
        for rel in data["added_paths"]:
            self.assertFalse(rel.startswith("rust/"), rel)

    def test_no_packaged_executable(self):
        with open(ALLOWLIST, encoding="utf-8") as handle:
            data = json.load(handle)
        for rel in data["added_paths"]:
            with open(os.path.join(ROOT, rel), "rb") as handle:
                self.assertNotEqual(handle.read(4), b"\x7fELF", rel)

    def test_checker_rejects_any_declared_modification(self):
        with open(os.path.join(HERE, "check_move84_inherited.py"),
                  encoding="utf-8") as handle:
            source = handle.read()
        self.assertIn("no inherited", source)
        self.assertIn("modification is authorised", source)


class TestGateStructure(unittest.TestCase):
    """The gate binds itself to the adopted artifact."""

    def _code(self):
        with open(GATE, encoding="utf-8") as handle:
            return "\n".join(l for l in handle.read().splitlines()
                             if not l.strip().startswith("#"))

    def test_gate_supplies_the_trusted_shell(self):
        self.assertIn('MOVE84_TEST_SH="$TRUSTED_SH"', self._code())

    def test_gate_pins_the_adopted_move83_hash(self):
        self.assertIn(ADOPTED_M83_SHA, self._code())

    def test_gate_establishes_authority_from_the_adopted_artifact(self):
        code = self._code()
        self.assertIn("--mode establish", code)
        self.assertIn("--mode demonstrate", code)
        self.assertIn("AUTHORITY_BIN", code)

    def test_gate_requires_externally_supplied_identity(self):
        code = self._code()
        for name in ("MOVE84_CANDIDATE_ZIP", "MOVE84_CANDIDATE_SHA256",
                     "MOVE84_OUTPUT_DIR", "REAL_MOVE83"):
            self.assertIn(name, code, name)

    def test_gate_marker_family_is_consistent(self):
        code = self._code()
        stale = "MOVE_84_" + "REPORT" + "_ADOPTION_GATE"
        self.assertNotIn(stale, code)
        self.assertIn("MOVE_84_DEMO_ADOPTION_GATE: PASS", code)

    def test_gate_self_binding_matches_the_packaged_name(self):
        match = re.search(r'case "\$SCRIPT_REAL" in\s*\n\s*(\S+)\) : ;;',
                          self._code())
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1),
                         "*/tools/check_move84_demo_adoption.sh")

    def test_every_referenced_helper_is_packaged(self):
        code = self._code()
        refs = set()
        for match in re.finditer(r'"\$P/([A-Za-z0-9_.-]+)"', code):
            refs.add("verify/demo_v01/" + match.group(1))
        for match in re.finditer(
                r'\$ROOT/([A-Za-z0-9_./-]+\.(?:py|sh|json|txt))', code):
            refs.add(match.group(1))
        self.assertGreaterEqual(len(refs), 5)
        missing = [r for r in sorted(refs)
                   if not os.path.isfile(os.path.join(ROOT, r))]
        self.assertEqual(missing, [])

    def test_gate_runs_the_move83_child(self):
        code = self._code()
        self.assertIn("check_move83_report_adoption.sh", code)
        self.assertIn("MOVE_83_REPORT_ADOPTION_GATE: PASS", code)

    def test_gate_preserves_the_adopted_divergences(self):
        code = self._code()
        self.assertIn("SYSTEM_AGREEMENT_RESULT: FAIL", code)
        self.assertIn("BEHAVIOURAL_DIVERGENCE_DETECTED", code)

    def test_gate_uses_the_adopted_focused_result_validator(self):
        self.assertIn("check_focused_result.py", self._code())

    def test_gate_requires_determinism_across_two_runs(self):
        self.assertIn("demo transcript is not deterministic", self._code())


class TestDocumentation(unittest.TestCase):
    def test_readme_states_the_rust_limitation(self):
        with open(README, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("does not detect", text)
        self.assertIn("evidence_001.bin", text)
        self.assertIn("no reachable PASS path", text)

    def test_readme_states_what_exit_zero_means(self):
        with open(README, encoding="utf-8") as handle:
            self.assertIn("universally valid", handle.read())

    def test_readme_makes_no_untested_platform_claim(self):
        with open(README, encoding="utf-8") as handle:
            text = handle.read()
        for token in ("Windows", "macOS"):
            self.assertNotIn(token, text)


class TestSuitePortability(unittest.TestCase):
    _SH = "/bin" + "/sh"
    _ENV = "/usr" + "/bin" + "/env"
    _SHEBANG = "#" + "!"

    def _sources(self):
        for name in sorted(os.listdir(HERE)):
            if name.endswith(".py"):
                with open(os.path.join(HERE, name), encoding="utf-8") as h:
                    yield name, h.read()

    def test_no_hardcoded_shebangs(self):
        for name, src in self._sources():
            for line in src.splitlines():
                if line.startswith(self._SHEBANG):
                    continue
                self.assertNotIn(self._SHEBANG + self._SH, line, name)
                self.assertNotIn(self._SHEBANG + self._ENV, line, name)

    def test_interpreter_and_shell_validated(self):
        for path in (TEST_SH, PYTHON_BIN):
            self.assertTrue(os.path.isabs(path))
            self.assertTrue(os.access(path, os.X_OK))
            self.assertEqual(path, os.path.realpath(path))

    def test_every_subprocess_is_bounded(self):
        for name, src in self._sources():
            for match in re.finditer(r"subprocess\.run\((.*?)\)\n", src,
                                     re.S):
                self.assertIn("timeout", match.group(1), name)

    def test_driver_declares_no_rust_reason_codes(self):
        """The demo must not predict what the adopted verifier says."""
        with open(DEMO_TOOL, encoding="utf-8") as handle:
            source = handle.read()
        self.assertNotIn('"DECLARED_HASH_MISMATCH"', source)
        self.assertNotIn('"MANIFEST_JSON_INVALID"', source)
        self.assertNotIn('"RECEIPT_CHAIN_HASHES_RECOMPUTED"', source)


class TestGateMoveIdentityIsCorrect(unittest.TestCase):
    """v01 was rejected because the Move 84 gate, derived from the Move 83
    gate, still described the adopted Move 83 v13 baseline as 'Move 82
    v07' throughout its comments, stage names and failure messages. The
    hash bound correctly; the evidence language did not.

    These scan the gate mechanically so the whole class is caught, not
    just the examples that were reported."""

    ADOPTED_BASELINE_MOVE = "Move 83"
    ADOPTED_BASELINE_FILE = "project-witness-MOVE_83_candidate_v13.zip"

    def _text(self):
        with open(GATE, encoding="utf-8") as handle:
            return handle.read()

    def _code(self):
        return "\n".join(l for l in self._text().splitlines()
                          if not l.strip().startswith("#"))

    # ---- the mechanical class check ---------------------------------

    #: phrases that would assign a BASELINE or CHILD-GATE role to a move
    #: other than the adopted Move 83 v13. References to Move 80 fixtures
    #: and the Move 81 adapter are genuine and are not matched here.
    MISIDENTIFYING = (
        r"real Move 8[0-2]\b", r"supplied Move 8[0-2] zip",
        r"adopted Move 8[0-2] v0\d (?:zip|baseline)",
        r"Move 8[0-2] child (?:gate|zip|run|output)",
        r"Move 8[0-2] adoption/regression",
        r"Move 8[0-2] baseline verifier",
        r"extracted Move 8[0-2] (?:root|tree)",
        r"candidate vs real Move 8[0-2]",
        r"MOVE 8[0-2] (?:PORTABLE|REPORT|DEMO) ",
        r"Move 8[0-2] v0\d baseline \+ allowlist",
    )

    #: a line explicitly marking an older move as a DEPENDENCY of a child
    #: gate is stating the truth, not misidentifying the baseline.
    DEPENDENCY_CONTEXT = re.compile(r"DEPENDENCY|dependency")

    def test_no_line_assigns_a_baseline_role_to_an_older_move(self):
        """The defect class: describing an older move as THIS move's
        baseline or child gate. Genuine references to Move 80 fixtures,
        the Move 81 adapter, and older moves named as dependencies of a
        child gate are not matched."""
        patterns = [re.compile(p) for p in self.MISIDENTIFYING]
        offenders = []
        for number, line in enumerate(self._text().splitlines(), 1):
            if self.DEPENDENCY_CONTEXT.search(line):
                continue
            for pattern in patterns:
                if pattern.search(line):
                    offenders.append((number, line.strip()[:80]))
                    break
        self.assertEqual(offenders, [],
                         "lines misidentify an older move: %s" % offenders)

    def test_the_misidentification_scanner_actually_catches_the_defect(self):
        """Mutation check: the exact v01 wording must be flagged."""
        patterns = [re.compile(p) for p in self.MISIDENTIFYING]
        for defective in (
                "# baseline immutability (candidate vs real Move 82 v07 zip)",
                'bad "supplied Move 82 zip sha256 x != y"',
                'echo "STAGE J: complete Move 82 adoption/regression child gate"',
                "# MOVE 82 PORTABLE BUILD ADOPTION GATE.",
                'die "extracted Move 82 root is not complete"'):
            self.assertTrue(any(p.search(defective) for p in patterns),
                            "scanner missed: %s" % defective)

    def test_the_scanner_does_not_flag_genuine_older_references(self):
        patterns = [re.compile(p) for p in self.MISIDENTIFYING]
        for genuine in (
                'ok "adopted Move 80 fixtures generated into the staging area"',
                "# Move 81 adapter equivalence across every applicable case.",
                'bad "Move 81 adapter records were not byte-identical"',
                "#   MOVE_82_REGRESSION_GATE: PASS   (inherited)"):
            self.assertFalse(any(p.search(genuine) for p in patterns),
                             "scanner false-positived: %s" % genuine)

    def test_baseline_is_named_move83_v13_everywhere_it_is_named(self):
        text = self._text()
        self.assertIn(self.ADOPTED_BASELINE_FILE, text)
        self.assertIn("adopted Move 83 v13", text)
        for wrong in ("adopted Move 82 v07 zip", "real Move 82 v07 zip",
                      "supplied Move 82 zip"):
            self.assertNotIn(wrong, text, wrong)

    def test_stage_b_names_the_move83_baseline(self):
        code = self._code()
        self.assertIn("baseline immutability (candidate vs real adopted "
                      "Move 83 v13 zip)", code)

    def test_stage_j_names_the_move83_child_gate(self):
        code = self._code()
        self.assertIn("complete adopted Move 83 v13 adoption/regression "
                      "child gate", code)
        self.assertIn("check_move83_report_adoption.sh", code)

    def test_header_names_this_move_not_an_older_one(self):
        first = self._text().splitlines()[:4]
        joined = " ".join(first)
        self.assertIn("MOVE 84", joined)
        for wrong in ("MOVE 82", "MOVE 83"):
            self.assertNotIn(wrong, joined, wrong)

    def test_real_move83_is_documented_as_the_sole_baseline(self):
        text = self._text()
        self.assertIn("SOLE Move 84", text)
        self.assertIn("REAL_MOVE83", text)

    # ---- the child's marker vocabulary ------------------------------

    #: the markers the ADOPTED Move 83 v13 gate genuinely emits as
    #: "<NAME>: PASS" on a successful run, derived mechanically below
    def _adopted_child_gate(self):
        return os.path.join(ROOT, "tools",
                            "check_move83_report_adoption.sh")

    def _emittable_pass_markers(self):
        """Markers the adopted Move 83 gate can actually EMIT as
        '<NAME>: PASS'.

        v06 required MOVE_83_REPORT_OUTPUT: PASS. The adopted gate assigns
        REPORT_OUTPUT=PASS internally but never echoes it -- that name
        reaches stdout only on a FAIL path -- so a genuinely successful
        child run was rejected. Requiring a marker because its NAME
        appears in the gate is not the same as requiring one the gate
        emits."""
        with open(self._adopted_child_gate(), encoding="utf-8") as handle:
            src = handle.read()
        pass_vars = {m.group(1) for m in
                     re.finditer(r"^([A-Z_0-9]+)=PASS\s*$", src, re.M)}
        emittable = set()
        for match in re.finditer(
                r'echo "((?:MOVE_8\d|SYSTEM)[A-Z_0-9]*): '
                r'(\$([A-Z_0-9]+)|PASS)"', src):
            name, whole, var = match.group(1, 2, 3)
            if whole == "PASS" or (var and var in pass_vars):
                emittable.add(name)
        return emittable

    def _required_of_child(self):
        code = self._code()
        start = code.find("for _need in")
        end = code.find("done", start)
        self.assertNotEqual(start, -1)
        return set(re.findall(r'"([A-Z_0-9]+): PASS"', code[start:end]))

    # ---- 5, 8: the set is DERIVED from the adopted gate --------------

    def test_every_required_marker_is_emittable_by_the_adopted_gate(self):
        emittable = self._emittable_pass_markers()
        self.assertGreaterEqual(len(emittable), 10)
        required = self._required_of_child()
        not_emittable = sorted(required - emittable)
        self.assertEqual(
            not_emittable, [],
            "Move 84 requires marker(s) the adopted Move 83 v13 gate "
            "never emits as PASS: %s" % not_emittable)

    def test_the_never_emitted_markers_are_not_required(self):
        """The exact v06 defect, and its neighbour."""
        required = self._required_of_child()
        emittable = self._emittable_pass_markers()
        for name in ("MOVE_83_REPORT_OUTPUT", "MOVE_83_DIGEST_BINDING"):
            self.assertNotIn(name, emittable,
                             "%s is emittable; this test is stale" % name)
            self.assertNotIn(name, required,
                             "%s is required but never emitted" % name)

    def test_a_name_appearing_only_on_fail_paths_is_not_emittable(self):
        """Proves the derivation distinguishes emission from mention."""
        with open(self._adopted_child_gate(), encoding="utf-8") as handle:
            src = handle.read()
        self.assertIn('echo "MOVE_83_REPORT_OUTPUT: FAIL"', src)
        self.assertNotIn('echo "MOVE_83_REPORT_OUTPUT: PASS"', src)
        self.assertNotIn('echo "MOVE_83_REPORT_OUTPUT: $REPORT_OUTPUT"',
                         src)

    # ---- 2, 4: the genuine markers ARE required ---------------------

    def test_the_terminal_child_marker_is_required(self):
        self.assertIn("MOVE_83_REPORT_ADOPTION_GATE",
                      self._required_of_child())

    def test_the_genuine_stage_markers_are_required(self):
        required = self._required_of_child()
        for name in ("MOVE_83_CANDIDATE_IDENTITY",
                     "MOVE_83_BASELINE_IMMUTABILITY",
                     "MOVE_83_TARGET_DETECTION",
                     "MOVE_83_CLEAN_RELEASE_BUILD",
                     "MOVE_83_BINARY_INSPECTION",
                     "MOVE_83_STANDALONE_EXECUTION",
                     "MOVE_83_CONTROLLED_BEHAVIOUR",
                     "MOVE_83_DEBUG_RELEASE_EQUIVALENCE",
                     "MOVE_83_PROVENANCE"):
            self.assertIn(name, required, name)

    def test_only_the_inherited_move82_regression_marker_is_required(self):
        required = self._required_of_child()
        self.assertEqual({r for r in required if r.startswith("MOVE_82_")},
                         {"MOVE_82_REGRESSION_GATE"})

    # ---- 1: genuine child output is ACCEPTED ------------------------

    def _genuine_child_stdout(self):
        """Reconstruct the marker block a successful adopted Move 83 v13
        run emits, from the adopted gate's own terminal summary."""
        lines = ["  OK    everything the child checked"]
        for name in sorted(self._emittable_pass_markers()):
            lines.append("%s: PASS" % name)
        lines.append("MOVE_82_REGRESSION_GATE: PASS")
        lines.append("SYSTEM_AGREEMENT_RESULT: FAIL")
        lines.append("SYSTEM_AGREEMENT_REASON: "
                     "BEHAVIOURAL_DIVERGENCE_DETECTED")
        return "\n".join(lines) + "\n"

    def _missing_markers(self, stdout_text):
        """Which required markers are absent from this child output."""
        return sorted(name for name in self._required_of_child()
                      if "%s: PASS" % name not in stdout_text)

    def test_genuine_adopted_child_output_is_accepted(self):
        self.assertEqual(self._missing_markers(self._genuine_child_stdout()),
                         [])

    def test_a_missing_genuine_marker_is_rejected(self):
        genuine = self._genuine_child_stdout()
        for name in ("MOVE_83_REPORT_ADOPTION_GATE",
                     "MOVE_83_PROVENANCE", "MOVE_82_REGRESSION_GATE"):
            damaged = genuine.replace("%s: PASS" % name, "%s: FAIL" % name)
            self.assertIn(name, self._missing_markers(damaged), name)

    def test_an_invented_marker_cannot_substitute_for_a_missing_one(self):
        """Adding MOVE_83_REPORT_OUTPUT: PASS to child output must not
        rescue a run that is missing a genuine adopted marker."""
        genuine = self._genuine_child_stdout()
        damaged = genuine.replace("MOVE_83_PROVENANCE: PASS",
                                  "MOVE_83_PROVENANCE: FAIL")
        spoofed = damaged + "MOVE_83_REPORT_OUTPUT: PASS\n"
        self.assertIn("MOVE_83_PROVENANCE",
                      self._missing_markers(spoofed))

    # ---- 3, 7: exit status and stderr -------------------------------

    def test_child_exit_zero_is_required(self):
        code = self._code()
        self.assertIn('"$_m83_rc" -ne 0', code)
        self.assertIn("Move 83 child adoption gate failed", code)

    def test_child_stdout_stderr_and_status_are_checked_separately(self):
        code = self._code()
        self.assertIn('>"$_M83_OUT" 2>"$_M83_ERR"', code)
        self.assertIn('[ -s "$_M83_ERR" ]', code)
        self.assertIn("Move 83 child gate emitted stderr", code)
        self.assertIn('_m83_rc=$?', code)

    def test_the_two_divergences_are_still_required(self):
        code = self._code()
        self.assertIn('"SYSTEM_AGREEMENT_RESULT: FAIL"', code)
        self.assertIn('"SYSTEM_AGREEMENT_REASON: '
                      'BEHAVIOURAL_DIVERGENCE_DETECTED"', code)

    def test_terminal_child_evidence_is_the_move83_regression_gate(self):
        code = self._code()
        self.assertIn("MOVE_83_REGRESSION_GATE: $MOVE_83_REGRESSION", code)
        self.assertNotIn("MOVE_82_REGRESSION_GATE: $", code)

    def test_the_evidence_chain_is_stated(self):
        """Move 84 -> adopted Move 83 v13 -> its Move 82 regression."""
        text = self._text()
        self.assertIn("its inherited Move 82", text)
        self.assertIn("Move 82 v07 is supplied to that", text)

    def test_no_stale_marker_family_from_the_derivation(self):
        code = self._code()
        for stale in ("MOVE_84_" + "REPORT_OUTPUT",
                      "MOVE_84_" + "DIGEST_BINDING",
                      "MOVE_84_" + "PORTABLE_BUILD_ADOPTION_GATE"):
            self.assertNotIn(stale, code, stale)

    def test_documentation_names_the_move83_baseline(self):
        for path in (README, os.path.join(ROOT, "CHANGELOG_MOVE_84.md"),
                     ALLOWLIST):
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            self.assertNotIn("Move 82 v07 baseline", text, path)
        with open(os.path.join(ROOT, "CHANGELOG_MOVE_84.md"),
                  encoding="utf-8") as handle:
            self.assertIn("MOVE_83_candidate_v13", handle.read())


class TestChildTreeReferencesResolve(unittest.TestCase):
    """v02 failed its genuine Termux gate at Stage J: it invoked
    `verify/portable_build_v01/check_move83_inherited.py` inside the
    extracted Move 83 child tree. That path does not exist — the Move 83
    checker lives in `verify/report_v01/`, and `portable_build_v01` holds
    the Move 82 checker. The derivation had renamed the FILE but left the
    DIRECTORY.

    Every path the gate reaches for inside the extracted child tree is
    resolved here against the real adopted Move 83 v13 archive."""

    ADOPTED_ZIP = os.path.join(
        os.sep, "mnt", "user-data", "outputs",
        "project-witness-MOVE_83_candidate_v13.zip")

    def _code(self):
        with open(GATE, encoding="utf-8") as handle:
            return "\n".join(l for l in handle.read().splitlines()
                              if not l.strip().startswith("#"))

    def _child_refs(self):
        code = self._code()
        return set(re.findall(r'\$_M83_ROOT/([A-Za-z0-9_./-]+)', code))

    def _adopted_members(self):
        """Paths inside the adopted Move 83 v13 archive."""
        import zipfile
        if not os.path.isfile(self.ADOPTED_ZIP):
            self.skipTest("adopted Move 83 v13 archive not available here")
        prefix = "project-witness-main/"
        with zipfile.ZipFile(self.ADOPTED_ZIP) as archive:
            return {name[len(prefix):] for name in archive.namelist()
                    if name.startswith(prefix)}

    def test_every_child_tree_reference_exists_in_the_adopted_archive(self):
        members = self._adopted_members()
        refs = self._child_refs()
        self.assertGreaterEqual(len(refs), 2)
        missing = sorted(r for r in refs if r not in members)
        self.assertEqual(missing, [],
                         "the gate reaches for paths absent from the "
                         "adopted Move 83 v13 tree: %s" % missing)

    def test_the_move83_inherited_checker_is_referenced_in_report_v01(self):
        code = self._code()
        self.assertIn("verify/report_v01/check_move83_inherited.py", code)
        self.assertNotIn(
            "verify/portable_build_v01/check_move83_inherited.py", code)

    def test_the_move82_checker_is_not_renamed_in_place(self):
        """portable_build_v01 holds the MOVE 82 checker. A move83-named
        file must never be sought there."""
        members = self._adopted_members()
        self.assertIn("verify/portable_build_v01/check_move82_inherited.py",
                      members)
        self.assertIn("verify/report_v01/check_move83_inherited.py",
                      members)
        self.assertNotIn(
            "verify/portable_build_v01/check_move83_inherited.py", members)

    def test_child_helper_presence_is_checked_before_use(self):
        code = self._code()
        self.assertIn('_M83_ODC="$_M83_ROOT/verify/report_v01/'
                      'check_move83_inherited.py"', code)
        self.assertIn('[ ! -f "$_M83_ODC" ]', code)
        self.assertIn('[ -L "$_M83_ODC" ]', code)

    def test_the_gate_uses_the_same_path_the_adopted_gate_uses(self):
        """Read the adopted Move 83 gate: whatever IT invokes for its own
        output-directory check is what the child must be given."""
        child_gate = os.path.join(ROOT, "tools",
                                  "check_move83_report_adoption.sh")
        with open(child_gate, encoding="utf-8") as handle:
            child_code = handle.read()
        self.assertIn("$P/check_move83_inherited.py", child_code)
        # and $P in that gate is verify/report_v01
        self.assertIn('P="$ROOT/verify/report_v01"', child_code)


class TestTranscriptIdentityIsCurrent(unittest.TestCase):
    """v02's provenance recorded MOVE_84_V01_TERMUX_GATE.txt because the
    single-sourced value was carried forward unchanged when the candidate
    was rebuilt."""

    ACTIVE = "MOVE_84_V07_TERMUX_GATE.txt"

    def _text(self):
        with open(GATE, encoding="utf-8") as handle:
            return handle.read()

    def _code(self):
        return "\n".join(l for l in self._text().splitlines()
                          if not l.strip().startswith("#"))

    def test_transcript_name_is_defined_once(self):
        code = self._code()
        self.assertIn('MOVE84_TRANSCRIPT_NAME="%s"' % self.ACTIVE, code)
        self.assertEqual(code.count(self.ACTIVE), 1)

    def test_provenance_uses_the_variable(self):
        self.assertIn('--transcript-name "$MOVE84_TRANSCRIPT_NAME"',
                      self._code())

    def test_no_superseded_candidate_identity_in_active_code(self):
        code = self._code()
        for old in ("01", "02", "03", "04", "05", "06"):
            stale = "MOVE_84_V%s_TERMUX_GATE.txt" % old
            self.assertNotIn(stale, code, stale)

    def test_changelog_agrees_with_the_pinned_and_discovered_suite(self):
        """The active transcript identity, the active focused-suite count,
        the pinned count and the genuinely discovered count must all
        agree.

        v04 was rejected because its changelog claimed 79 -> 83 while the
        pin and the suite both held 85. The suite-count assertions live
        here rather than in a test of their own so that adding this check
        does not itself change the count it validates."""
        with open(os.path.join(ROOT, "CHANGELOG_MOVE_84.md"),
                  encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("Status: CANDIDATE v07", text)
        self.assertIn(self.ACTIVE, text)

        # the pinned count
        with open(os.path.join(HERE, "EXPECTED_TEST_COUNT.txt"),
                  encoding="utf-8") as handle:
            pinned = handle.read().strip()
        self.assertTrue(pinned.isdigit(), "pinned count is not an integer")

        # the genuinely discovered count, by loading this module
        discovered = unittest.defaultTestLoader.loadTestsFromModule(
            sys.modules[__name__]).countTestCases()
        self.assertEqual(int(pinned), discovered,
                         "the pinned count disagrees with the suite")

        # EVERY suite-count claim is validated, not the first.
        #
        # v05 extracted all claims and then checked only claims[0]; a
        # second, contradictory active claim would have passed silently.
        # Claims are now explicitly classified so active and historical
        # ones are distinguished deterministically rather than by
        # position, and an UNCLASSIFIED claim is itself a failure -- so a
        # future claim cannot be added without being validated.
        active_re = re.compile(r"^Suite \(active\): (\d+) tests", re.M)
        historical_re = re.compile(
            r"^Suite \(historical, candidate (v\d+)\): "
            r"(?:(\d+) -> )?(\d+) tests", re.M)
        any_claim_re = re.compile(r"^Suite\b[^\n]*", re.M)

        active = active_re.findall(text)
        historical = historical_re.findall(text)

        # 1. no unclassified claim may exist anywhere
        classified = set()
        for match in active_re.finditer(text):
            classified.add(match.group(0))
        for match in historical_re.finditer(text):
            classified.add(match.group(0))
        unclassified = [line for line in any_claim_re.findall(text)
                        if not any(line.startswith(c)
                                   for c in classified)]
        self.assertEqual(
            unclassified, [],
            "unclassified focused-suite claim(s), which would escape "
            "validation: %s" % unclassified)

        # 2. at least one active claim must exist
        self.assertTrue(active,
                        "the changelog states no active suite count")

        # 3. EVERY active claim must agree with the pin and the suite
        for claimed in active:
            self.assertEqual(
                int(claimed), discovered,
                "an active changelog claim says %s tests; the suite has "
                "%d" % (claimed, discovered))
            self.assertEqual(
                int(claimed), int(pinned),
                "an active changelog claim says %s tests; the pin says %s"
                % (claimed, pinned))

        # 4. every historical claim must name a SUPERSEDED candidate
        self.assertTrue(historical,
                        "no historical suite claims are classified")
        active_candidate = "v" + self.ACTIVE.split("_V")[1][:2]
        for candidate, _from_count, _to_count in historical:
            self.assertNotEqual(
                candidate, active_candidate,
                "a historical claim names the ACTIVE candidate %s"
                % candidate)


class TestHistoricalEvidenceIsExact(unittest.TestCase):
    """v03 was rejected because its changelog recorded a SHA-256 for the
    v02 Termux transcript that was not the transcript's hash. Nobody
    supplied that value; it was written into the audit record.

    In a project about tamper-evident evidence, a false hash in an audit
    record is indistinguishable from a forged one. These tests pin the
    genuine value and refuse the fabricated one."""

    #: the genuine first-run transcript of candidate v02, as reported with
    #: the v02 rejection
    V02_TRANSCRIPT_SHA256 = \
        "0d8678555d7775addb8496618d23e4e943616982fb2cf510b030fd4c27814493"
    V02_TRANSCRIPT_NAME = "MOVE_84_V02_TERMUX_GATE.txt"

    #: assembled from fragments so this file never contains the false
    #: value as a searchable string
    _FABRICATED = ("9a3ba7bc60b16b09" "b2fc0d33cee4c53f"
                   "2e1de0155e1c5e8b" "28ce88ac00d24a5c")

    #: candidate identities, as reported
    CANDIDATES = {
        "v01": "27d18656a61e5c135b7ba1bbf0a093c986377a64ee6947861dd7cc52b9d1986c",
        "v02": "dfd5ba010291e4659d2481be9115069781ce5a7b62c4eb98e84ea07a91d61f36",
        "v03": "41f5ccdb2c5bce5bc759a3764bf4f2f108208105a0f29929c289315786518071",
        "v04": "4874a898fbf376ce77d071380e5384c1dc0005e8fe83deef771daa4d71554de5",
        "v05": "faeb7ad084ee5a33486b6f8bcb76ad746e9a094bef122b18524668355dbd9140",
        "v06": "a3c23067920addecc643bb767c6b455d77d24e13d8815a4911bc7ee4d023e782",
    }
    #: v02 and v06 were run on Termux; the others never were
    NEVER_RUN_ON_TERMUX = ("v01", "v03", "v04", "v05")
    #: the genuine first-run transcript of candidate v06
    V06_TRANSCRIPT_SHA256 = \
        "ab56b88259a375ec708d2efad8da89125b34c9e14c5b53ba6938d8b42415fa4a"
    #: v02 and v06 reached Termux; the rest were rejected before any run

    CHANGELOG = os.path.join(ROOT, "CHANGELOG_MOVE_84.md")

    def _move84_files(self):
        yield self.CHANGELOG
        yield GATE
        for name in sorted(os.listdir(HERE)):
            yield os.path.join(HERE, name)

    def test_the_genuine_v02_transcript_hash_is_recorded(self):
        with open(self.CHANGELOG, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn(self.V02_TRANSCRIPT_SHA256, text)
        self.assertIn(self.V02_TRANSCRIPT_NAME, text)

    def test_the_fabricated_hash_appears_nowhere(self):
        for path in self._move84_files():
            try:
                with open(path, encoding="utf-8") as handle:
                    text = handle.read()
            except (OSError, UnicodeDecodeError):
                continue
            self.assertNotIn(self._FABRICATED, text,
                             "a fabricated transcript hash survives in %s"
                             % path)

    def test_the_v02_transcript_is_named_with_its_real_hash(self):
        """Wherever the v02 transcript is named, the nearest hash to it
        must be the genuine one."""
        with open(self.CHANGELOG, encoding="utf-8") as handle:
            text = handle.read()
        for index in range(len(text)):
            found = text.find(self.V02_TRANSCRIPT_NAME, index)
            if found == -1:
                break
            window = text[found:found + 400]
            hashes = re.findall(r"[0-9a-f]{64}", window)
            if hashes:
                self.assertEqual(
                    hashes[0], self.V02_TRANSCRIPT_SHA256,
                    "the v02 transcript is credited with a wrong hash")
            index = found + 1

    def test_candidate_identities_are_exact(self):
        with open(self.CHANGELOG, encoding="utf-8") as handle:
            text = handle.read()
        for label, digest in self.CANDIDATES.items():
            self.assertIn(digest, text,
                          "candidate %s identity missing" % label)

    def test_no_transcript_is_claimed_for_a_candidate_never_run(self):
        """v01 and v03 were never run on Termux, so no transcript may be
        attributed to them."""
        with open(self.CHANGELOG, encoding="utf-8") as handle:
            text = handle.read()
        for label in self.NEVER_RUN_ON_TERMUX:
            name = "MOVE_84_V%s_TERMUX_GATE.txt" % label[1:]
            for index in range(len(text)):
                found = text.find(name, index)
                if found == -1:
                    break
                window = text[found:found + 200]
                self.assertIsNone(
                    re.search(r"SHA-256|sha256", window),
                    "a transcript hash is claimed for %s, which was never "
                    "run on Termux" % label)
                index = found + 1

    def test_every_recorded_hash_is_a_known_fact(self):
        """No 64-hex string may appear in the changelog unless it is one
        of the facts actually reported."""
        known = set(self.CANDIDATES.values())
        known.add(self.V02_TRANSCRIPT_SHA256)
        known.add(self.V06_TRANSCRIPT_SHA256)
        known.add(ADOPTED_M83_SHA)
        with open(self.CHANGELOG, encoding="utf-8") as handle:
            text = handle.read()
        found = set(re.findall(r"[0-9a-f]{64}", text))
        unknown = sorted(found - known)
        self.assertEqual(unknown, [],
                         "unrecognised hashes in the audit record: %s"
                         % unknown)


if __name__ == "__main__":
    _suite = unittest.defaultTestLoader.loadTestsFromModule(
        sys.modules[__name__])
    _result = unittest.TextTestRunner(
        stream=sys.stdout, verbosity=1).run(_suite)
    sys.exit(0 if _result.wasSuccessful() else 1)
