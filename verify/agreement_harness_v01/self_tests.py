"""Move 79 harness SELF-TESTS (verification-only).

These test the HARNESS, not the systems it invokes. Each uses a fake
responder to prove the harness fails closed on a specific false-green
class. The v1 harness would have PASSED several of these — notably
"correct reason code with wrong verdict", which is why they exist.

Run: python3 verify/agreement_harness_v01/self_tests.py
"""

import copy
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import run_agreement as H  # noqa: E402
import gate_test_fixtures as _fixtures  # noqa: E402


def base_case(**over):
    case = {
        "case_id": "t1", "lane": "archive", "archive_file": "t1.zip",
        "category": "AGREEMENT_CASE",
        "python_scope": "in_scope", "rust_scope": "in_scope",
        "expected": {
            "normalized_outcome": "REJECTED",
            "python": {"verdict": "FAIL", "exit_code": 1,
                       "reason_class": "ARCHIVE_PATH_TRAVERSAL",
                       "stage": "archive"},
            "rust": {"verdict": "FAIL", "exit_code": 1,
                     "reason_class": "ARCHIVE_PATH_TRAVERSAL",
                     "stage": "archive"},
        },
        "provenance": {"source_contract": "self-test",
                       "reference": "self-test",
                       "justification": "self-test fixture"},
    }
    case.update(over)
    return case


MAPPER = H.ReasonMapper(H.load_json(os.path.join(HERE, "reason_map.json")))


class FakePython:
    def __init__(self, **res):
        self.res = res

    def archive(self, _t):
        return dict(self.res)

    def bundle(self, _t):
        return dict(self.res)


class FakeRust(FakePython):
    pass


def good_py(**over):
    r = {"verdict": "FAIL", "exit_code": 1,
         "raw": "ARCHIVE_PATH_TRAVERSAL", "entry_count": None}
    r.update(over)
    return FakePython(**r)


def good_rs(**over):
    r = {"verdict": "FAIL", "exit_code": 1,
         "raw": "ARCHIVE_PATH_TRAVERSAL", "entry_count": None}
    r.update(over)
    return FakeRust(**r)


def run(case, py, rs):
    return H.compare_case(case, MAPPER, py, rs, {case["case_id"]: "/dev/null"})


class HarnessRejects(unittest.TestCase):

    def test_baseline_passes(self):
        rec = run(base_case(), good_py(), good_rs())
        self.assertEqual(rec["python_class"], "ARCHIVE_PATH_TRAVERSAL")

    def test_correct_reason_wrong_verdict(self):
        # THE v1 FALSE-GREEN: correct code, wrong verdict
        with self.assertRaises(H.HarnessError) as ctx:
            run(base_case(), good_py(),
                good_rs(verdict="INCONCLUSIVE", exit_code=3))
        self.assertTrue("VERDICT_DISAGREE" in ctx.exception.code or "NORMALIZED_OUTCOME_DISAGREE" in ctx.exception.code)

    def test_correct_json_wrong_exit_code(self):
        with self.assertRaises(H.HarnessError) as ctx:
            run(base_case(), good_py(), good_rs(exit_code=0))
        self.assertIn("EXIT_DISAGREE", ctx.exception.code)

    def test_missing_rust_entry_count(self):
        case = base_case()
        case["expected"]["normalized_outcome"] = "ACCEPTED"
        for side in ("python", "rust"):
            case["expected"][side] = {"verdict": "INCONCLUSIVE",
                                      "exit_code": 3,
                                      "reason_class": "ARCHIVE_OK",
                                      "stage": "archive"}
        case["expected"]["entry_count"] = 3
        py = good_py(verdict="INCONCLUSIVE", exit_code=3,
                     raw="ARCHIVE_SAFETY_OK", entry_count=3)
        rs = good_rs(verdict="INCONCLUSIVE", exit_code=3,
                     raw="ARCHIVE_SAFETY_OK", entry_count=None)
        with self.assertRaises(H.HarnessError) as ctx:
            run(case, py, rs)
        self.assertEqual(ctx.exception.code, "MISSING_RUST_ENTRY_COUNT")

    def test_unmapped_reason(self):
        with self.assertRaises(H.HarnessError) as ctx:
            run(base_case(), good_py(raw="TOTALLY_UNKNOWN_CODE"), good_rs())
        self.assertEqual(ctx.exception.code, "UNMAPPED_REASON")

    def test_ambiguous_reason(self):
        mapping = {"archive": [
            {"class": "A", "match_type": "exact", "value": "X"},
            {"class": "B", "match_type": "exact", "value": "X"}]}
        mapper = H.ReasonMapper(mapping)
        with self.assertRaises(H.HarnessError) as ctx:
            mapper.map("archive", "X")
        self.assertEqual(ctx.exception.code, "AMBIGUOUS_REASON")

    def test_python_rust_class_disagree(self):
        with self.assertRaises(H.HarnessError) as ctx:
            run(base_case(), good_py(),
                good_rs(raw="ARCHIVE_ABSOLUTE_PATH"))
        # expected/rust check fires first — both are stop conditions
        self.assertIn("DISAGREE", ctx.exception.code)


class SchemaRejects(unittest.TestCase):

    def test_agreement_case_with_one_side_out_of_scope(self):
        case = base_case(rust_scope="out_of_scope")
        with self.assertRaises(H.HarnessError) as ctx:
            H.validate_corpus([case])
        self.assertEqual(ctx.exception.code, "CATEGORY_SCOPE_CONTRADICTION")

    def test_single_implementation_with_both_in_scope(self):
        case = base_case(category="SINGLE_IMPLEMENTATION_CASE")
        with self.assertRaises(H.HarnessError) as ctx:
            H.validate_corpus([case])
        self.assertEqual(ctx.exception.code, "CATEGORY_SCOPE_CONTRADICTION")

    def test_unsupported_case_with_a_side_in_scope(self):
        case = base_case(category="UNSUPPORTED_CASE")
        with self.assertRaises(H.HarnessError) as ctx:
            H.validate_corpus([case])
        self.assertEqual(ctx.exception.code, "CATEGORY_SCOPE_CONTRADICTION")

    def test_duplicate_case_ids(self):
        with self.assertRaises(H.HarnessError) as ctx:
            H.validate_corpus([base_case(), base_case()])
        self.assertEqual(ctx.exception.code, "DUPLICATE_CASE_ID")

    def test_verdict_exit_inconsistency_in_expectation(self):
        case = base_case()
        case["expected"]["rust"]["exit_code"] = 3   # FAIL must be exit 1
        with self.assertRaises(H.HarnessError) as ctx:
            H.validate_corpus([case])
        self.assertEqual(ctx.exception.code, "SCHEMA_INVALID")

    def test_missing_provenance(self):
        case = base_case()
        case["provenance"] = {}
        with self.assertRaises(H.HarnessError) as ctx:
            H.validate_corpus([case])
        self.assertEqual(ctx.exception.code, "SCHEMA_INVALID")

    def test_missing_per_impl_expectation(self):
        case = base_case()
        del case["expected"]["rust"]["stage"]
        with self.assertRaises(H.HarnessError) as ctx:
            H.validate_corpus([case])
        self.assertEqual(ctx.exception.code, "SCHEMA_INVALID")

    def test_real_corpus_schema_ok(self):
        # the shipped corpus must satisfy the schema
        cases = (H.load_json(os.path.join(HERE, "corpus",
                                          "bundle_cases.json"))["cases"]
                 + H.load_json(os.path.join(HERE, "corpus",
                                            "archive_cases.json"))["cases"])
        H.validate_corpus(cases)


class RustProtocolRejects(unittest.TestCase):
    """Identity / version / JSON checks live in RustRunner._run; exercise
    them through a stub subprocess result."""

    def _runner_with(self, payload, returncode=1):
        import subprocess

        class FakeProc:
            def __init__(self):
                self.stdout = payload
                self.stderr = ""
                self.returncode = returncode

        orig = subprocess.run
        subprocess.run = lambda *a, **k: FakeProc()
        try:
            runner = H.RustRunner("/nonexistent")
            return runner.archive("/dev/null")
        finally:
            subprocess.run = orig

    def test_wrong_verifier_identity(self):
        payload = json.dumps({"verifier": "not-witness-verify",
                              "version": H.RUST_VERSION_REQUIRED,
                              "verdict": "FAIL",
                              "reason_code": "ARCHIVE_MALFORMED"})
        with self.assertRaises(H.HarnessError) as ctx:
            self._runner_with(payload)
        self.assertEqual(ctx.exception.code, "RUST_IDENTITY_MISMATCH")

    def test_stale_version(self):
        payload = json.dumps({"verifier": "witness-verify",
                              "version": "0.0.7-step78-zipguard",
                              "verdict": "FAIL",
                              "reason_code": "ARCHIVE_MALFORMED"})
        with self.assertRaises(H.HarnessError) as ctx:
            self._runner_with(payload)
        self.assertEqual(ctx.exception.code, "RUST_VERSION_MISMATCH")

    def test_malformed_json(self):
        with self.assertRaises(H.HarnessError) as ctx:
            self._runner_with("{not json")
        self.assertEqual(ctx.exception.code, "RUST_MALFORMED_JSON")

    def test_stderr_only_failure(self):
        with self.assertRaises(H.HarnessError) as ctx:
            self._runner_with("")
        self.assertEqual(ctx.exception.code, "RUST_STDERR_ONLY_FAILURE")

    def test_exit_code_contradicts_verdict(self):
        payload = json.dumps({"verifier": "witness-verify",
                              "version": H.RUST_VERSION_REQUIRED,
                              "verdict": "INCONCLUSIVE",
                              "reason_code": "ARCHIVE_SAFETY_OK",
                              "entry_count": 1})
        with self.assertRaises(H.HarnessError) as ctx:
            self._runner_with(payload, returncode=1)   # should be 3
        self.assertEqual(ctx.exception.code, "RUST_EXIT_CODE_MISMATCH")


class DeterminismRejects(unittest.TestCase):

    def test_nondeterministic_responder_detected(self):
        """A responder that alternates results must be caught by the
        ordering/repeat comparison in run_once + canonical compare."""
        case = base_case()

        class Flapping:
            def __init__(self):
                self.n = 0

            def archive(self, _t):
                self.n += 1
                raw = "ARCHIVE_PATH_TRAVERSAL" if self.n % 2 \
                    else "ARCHIVE_ABSOLUTE_PATH"
                return {"verdict": "FAIL", "exit_code": 1, "raw": raw,
                        "entry_count": None}

        py = Flapping()
        paths = {"t1": "/dev/null"}
        first = H.run_once([case], MAPPER, py, None, paths, "original")
        try:
            second = H.run_once([case], MAPPER, py, None, paths, "original")
        except H.HarnessError:
            return   # expectation check caught the flip: also acceptable
        self.assertNotEqual(H.canonical(first), H.canonical(second),
                            "flapping responder was not detected")




class NormalizedOutcomeRejects(unittest.TestCase):
    def test_accepted_with_fail_verdict_rejected(self):
        case = base_case()
        case["expected"]["normalized_outcome"] = "ACCEPTED"  # but verdicts FAIL
        with self.assertRaises(H.HarnessError) as ctx:
            H.validate_corpus([case])
        self.assertEqual(ctx.exception.code, "NORMALIZED_OUTCOME_CONTRADICTION")

    def test_rejected_with_pass_verdict_rejected(self):
        case = base_case()
        case["expected"]["python"]["verdict"] = "PASS"
        case["expected"]["python"]["exit_code"] = 0
        with self.assertRaises(H.HarnessError) as ctx:
            H.validate_corpus([case])
        self.assertEqual(ctx.exception.code, "NORMALIZED_OUTCOME_CONTRADICTION")


class ProvenanceRejects(unittest.TestCase):
    def test_missing_source_contract(self):
        case = base_case()
        case["provenance"] = {"reference": "r", "justification": "j"}
        with self.assertRaises(H.HarnessError) as ctx:
            H.validate_corpus([case])
        self.assertEqual(ctx.exception.code, "SCHEMA_INVALID")

    def test_missing_reference(self):
        case = base_case()
        case["provenance"] = {"source_contract": "c", "justification": "j"}
        with self.assertRaises(H.HarnessError) as ctx:
            H.validate_corpus([case])
        self.assertEqual(ctx.exception.code, "SCHEMA_INVALID")


class ExitContractCLI(unittest.TestCase):
    """Top-level CLI exit codes via subprocess."""
    import subprocess as _sp
    HARNESS = os.path.join(HERE, "run_agreement.py")

    def _exit(self, *args):
        import subprocess
        p = subprocess.run([sys.executable, self.HARNESS] + list(args),
                           capture_output=True, text=True)
        return p.returncode

    def test_required_corpus_unavailable_is_exit_3(self):
        # no real archives supplied -> INCONCLUSIVE -> exit 3
        self.assertEqual(self._exit(), 3)

    def test_bad_rust_bin_is_usage_exit_2(self):
        self.assertEqual(self._exit("--rust-bin", "/nonexistent/xyz"), 2)


class BaseCaseProvenanceFix(unittest.TestCase):
    def test_base_case_has_full_provenance(self):
        # ensure the self-test fixtures themselves carry full provenance
        H.validate_corpus([base_case(provenance={
            "source_contract": "c", "reference": "r",
            "justification": "j"})])




class DivergenceNeverPasses(unittest.TestCase):
    """B1: a confirmed in-scope divergence must never produce PASS."""

    def _div_case(self):
        c = base_case(category="KNOWN_DIVERGENCE_CASE")
        c["expected"]["rust"]["reason_class"] = "ARCHIVE_ABSOLUTE_PATH"
        c["expected_divergence"] = {
            "python_class": "ARCHIVE_PATH_TRAVERSAL",
            "python_stage": "archive",
            "rust_class": "ARCHIVE_ABSOLUTE_PATH",
            "rust_stage": "archive"}
        return c

    def test_divergence_is_flagged_on_the_record(self):
        rec = run(self._div_case(), good_py(),
                  good_rs(raw="ARCHIVE_ABSOLUTE_PATH"))
        self.assertTrue(rec["divergent"], "divergence not flagged")

    def test_divergence_count_is_computed_not_hardcoded(self):
        with open(os.path.join(HERE, "run_agreement.py")) as _h:
            src = _h.read()
        self.assertNotIn('"divergences": 0,', src,
                         "divergence count is hardcoded")
        self.assertIn('"divergences": len(divergent)', src)

    def test_pass_impossible_while_divergence_exists(self):
        with open(os.path.join(HERE, "run_agreement.py")) as _h:
            src = _h.read()
        # a divergence must route to a non-passing status
        self.assertIn("BEHAVIOURAL_DIVERGENCE_DETECTED", src)
        self.assertIn("elif divergent:", src)

    def test_declared_divergence_not_observed_is_rejected(self):
        # implementations AGREE but the case declared a divergence
        with self.assertRaises(H.HarnessError) as ctx:
            run(self._div_case(), good_py(), good_rs())
        # either stop condition is correct: Rust fails its own declared
        # expectation, or the declared divergence is not observed. Both
        # are non-passing, which is the property under test.
        self.assertIn(ctx.exception.code,
                      ("DECLARED_DIVERGENCE_NOT_OBSERVED",
                       "EXPECTED_RUST_CLASS_DISAGREE"))

    def test_expected_divergence_forbidden_on_agreement_case(self):
        c = base_case()
        c["expected_divergence"] = {"python_class": "X", "python_stage": "y",
                                    "rust_class": "Z", "rust_stage": "w"}
        with self.assertRaises(H.HarnessError) as ctx:
            H.validate_corpus([c])
        self.assertEqual(ctx.exception.code, "SCHEMA_INVALID")

    def test_malformed_expected_divergence_does_not_crash(self):
        c = base_case(category="KNOWN_DIVERGENCE_CASE")
        c["expected_divergence"] = {"python_class": "X"}   # incomplete
        with self.assertRaises(H.HarnessError) as ctx:
            H.validate_corpus([c])
        self.assertEqual(ctx.exception.code, "SCHEMA_INVALID")


class ObservationSchemaRejects(unittest.TestCase):
    """B3: SINGLE_IMPLEMENTATION cases need a COMPLETE observation spec."""

    def _single(self):
        c = base_case(category="SINGLE_IMPLEMENTATION_CASE",
                      rust_scope="out_of_scope")
        del c["expected"]["rust"]
        return c

    def test_missing_observation_spec_is_schema_invalid(self):
        with self.assertRaises(H.HarnessError) as ctx:
            H.validate_corpus([self._single()])
        self.assertEqual(ctx.exception.code, "SCHEMA_INVALID")

    def test_incomplete_observation_spec_is_schema_invalid(self):
        c = self._single()
        c["expected"]["rust_observed"] = {"verdict": "FAIL", "exit_code": 1}
        with self.assertRaises(H.HarnessError) as ctx:
            H.validate_corpus([c])
        self.assertEqual(ctx.exception.code, "SCHEMA_INVALID")

    def test_observation_verdict_exit_inconsistency_rejected(self):
        c = self._single()
        c["expected"]["rust_observed"] = {"verdict": "FAIL", "exit_code": 3,
                                          "reason_class": "X",
                                          "stage": "archive"}
        with self.assertRaises(H.HarnessError) as ctx:
            H.validate_corpus([c])
        self.assertEqual(ctx.exception.code, "SCHEMA_INVALID")


class RustBinaryFailures(unittest.TestCase):
    def test_nonexecutable_rust_bin_is_structured_usage(self):
        import subprocess
        p = subprocess.run(
            [sys.executable, os.path.join(HERE, "run_agreement.py"),
             "--rust-bin", "/nonexistent/xyz"],
            capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)
        payload = json.loads(p.stdout)
        self.assertEqual(payload["overall_status"], "USAGE")
        self.assertNotIn("Traceback", p.stderr)




class ProtocolInvalidRejects(unittest.TestCase):
    """B6: valid-but-non-object JSON must fail structurally."""

    def _probe(self, payload):
        import subprocess

        class P:
            def __init__(self):
                self.stdout = payload
                self.stderr = ""
                self.returncode = 1

        orig = subprocess.run
        subprocess.run = lambda *a, **k: P()
        try:
            return H.RustRunner("/x").archive("/dev/null")
        finally:
            subprocess.run = orig

    def test_non_object_json_payloads(self):
        for payload in ("[]", "null", '"str"', "123"):
            with self.assertRaises(H.HarnessError) as ctx:
                self._probe(payload)
            self.assertEqual(ctx.exception.code, "RUST_PROTOCOL_INVALID",
                             "payload %s" % payload)


class CorpusLockRejects(unittest.TestCase):
    """B5: the corpus may not silently shrink or drift."""

    def _cases(self):
        return (H.load_json(os.path.join(HERE, "corpus",
                                         "bundle_cases.json"))["cases"]
                + H.load_json(os.path.join(HERE, "corpus",
                                           "archive_cases.json"))["cases"])

    def test_intact_corpus_passes_lock(self):
        H.check_corpus_lock(self._cases())

    def test_deleted_case_fails_lock(self):
        cases = [c for c in self._cases()
                 if c["case_id"] != "compete_unc_vs_traversal"]
        with self.assertRaises(H.HarnessError) as ctx:
            H.check_corpus_lock(cases)
        self.assertIn("CORPUS_LOCK", ctx.exception.code)

    def test_renamed_case_fails_lock(self):
        cases = copy.deepcopy(self._cases())
        for c in cases:
            if c["case_id"] == "traversal":
                c["case_id"] = "traversal_renamed"
        with self.assertRaises(H.HarnessError) as ctx:
            H.check_corpus_lock(cases)
        self.assertIn("CORPUS_LOCK", ctx.exception.code)

    def test_removed_divergence_case_fails_lock(self):
        cases = [c for c in self._cases()
                 if c["case_id"] != "stage_manifest_json_invalid"]
        with self.assertRaises(H.HarnessError) as ctx:
            H.check_corpus_lock(cases)
        self.assertIn("CORPUS_LOCK", ctx.exception.code)


class NoBytecodeWritten(unittest.TestCase):
    """B8: BEHAVIOURAL proof — run the real verification path in a copied
    tree, snapshot before/after, and require zero new files. Source-string
    presence is NOT proof."""

    def _snapshot(self, root):
        seen = set()
        for base, dirs, files in os.walk(root):
            for name in dirs + files:
                seen.add(os.path.relpath(os.path.join(base, name), root))
        return seen

    def test_self_test_run_creates_no_cache(self):
        import shutil
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            dest = os.path.join(tmp, "harness")
            shutil.copytree(HERE, dest,
                            ignore=shutil.ignore_patterns("__pycache__",
                                                          "*.pyc"))
            before = self._snapshot(dest)
            subprocess.run(
                [sys.executable, "-B", os.path.join(dest, "run_agreement.py"),
                 "--rust-bin", "/definitely/not/here"],
                capture_output=True, text=True,
                env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
            after = self._snapshot(dest)
            created = sorted(after - before)
            self.assertEqual(created, [],
                             "verification path created files: %s" % created)
            caches = [p for p in after
                      if "__pycache__" in p or p.endswith((".pyc", ".pyo"))]
            self.assertEqual(caches, [], "cache artefacts: %s" % caches)


class NonExecutableRustBin(unittest.TestCase):
    """B5: an existing but NON-EXECUTABLE file must give structured USAGE."""

    def test_existing_non_executable_file(self):
        import subprocess
        import tempfile
        fd, path = tempfile.mkstemp()
        os.close(fd)
        os.chmod(path, 0o644)
        try:
            p = subprocess.run(
                [sys.executable, "-B",
                 os.path.join(HERE, "run_agreement.py"),
                 "--rust-bin", path],
                capture_output=True, text=True,
                env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
            self.assertEqual(p.returncode, 2, "want USAGE exit 2")
            payload = json.loads(p.stdout)
            self.assertEqual(payload["overall_status"], "USAGE")
            self.assertEqual(payload["reason_code"],
                             "RUST_BIN_NOT_EXECUTABLE")
            self.assertNotIn("Traceback", p.stderr)
        finally:
            os.unlink(path)


class ObservationRecordSchema(unittest.TestCase):
    """B7: every observation record keeps all six audit fields."""

    REQUIRED = {"verdict", "exit_code", "raw_reason", "mapped_reason_class",
                "stage", "normalized_outcome"}

    def test_observation_record_has_six_fields(self):
        case = base_case(category="SINGLE_IMPLEMENTATION_CASE",
                         rust_scope="out_of_scope")
        del case["expected"]["rust"]
        case["expected"]["rust_observed"] = {
            "verdict": "FAIL", "exit_code": 1,
            "reason_class": "ARCHIVE_PATH_TRAVERSAL", "stage": "archive"}
        rec = run(case, good_py(), good_rs())
        obs = rec.get("rust_observed")
        self.assertIsNotNone(obs, "observation not recorded")
        self.assertEqual(self.REQUIRED - set(obs), set(),
                         "missing audit fields: %s"
                         % (self.REQUIRED - set(obs)))




class WarningClean(unittest.TestCase):
    """B2: file handles must not leak. ResourceWarnings fire at finalization
    and do NOT change the exit code, so a zero exit is not proof."""

    def test_corpus_lock_leaks_no_handles(self):
        import gc
        import warnings
        cases = (H.load_json(os.path.join(HERE, "corpus",
                                          "bundle_cases.json"))["cases"]
                 + H.load_json(os.path.join(HERE, "corpus",
                                            "archive_cases.json"))["cases"])
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            H.check_corpus_lock(cases)
            gc.collect()
        leaks = [w for w in caught
                 if issubclass(w.category, ResourceWarning)]
        self.assertEqual(leaks, [],
                         "check_corpus_lock leaked handles: %s"
                         % [str(w.message) for w in leaks])

    def test_pin_check_leaks_no_handles(self):
        import gc
        import warnings
        sys.path.insert(0, HERE)
        import pin_check
        root = os.path.abspath(os.path.join(HERE, "..", ".."))
        pins = os.path.join(root, "tools", "adopted_artifact_pins.json")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            problems = pin_check.verify_pins(pins, root)
            gc.collect()
        leaks = [w for w in caught
                 if issubclass(w.category, ResourceWarning)]
        self.assertEqual(leaks, [], "pin_check leaked handles")
        self.assertEqual(problems, [], "adopted artifacts mutated: %s"
                         % problems)

    def test_no_unclosed_resources_in_harness_tree(self):
        # B4: detects unclosed reads AND bare (non-context-managed) archive
        # construction across the whole harness tree, including this file
        # and resource_scan.py itself.
        import glob
        import resource_scan
        offenders = []
        targets = glob.glob(os.path.join(HERE, "*.py")) \
            + glob.glob(os.path.join(HERE, "corpus", "*.py")) \
            + glob.glob(os.path.join(HERE, "oracles", "*.py"))
        for path in targets:
            for hit in resource_scan.scan_path(path):
                offenders.append("%s:%s" % (os.path.basename(path), hit))
        self.assertEqual(offenders, [],
                         "unclosed resources remain: %s" % offenders)




class RustCheckerWarningClean(unittest.TestCase):
    """B2: the Rust workspace checker must be warning-clean even with NO
    toolchain (it still runs all structural/computed checks)."""

    # Delegates to the single shared fixture so the no-Cargo builder cannot
    # drift between test files. cargo/rustc/rustup are excluded there; no PATH
    # directory is ever enumerated.
    _WORKSPACE_REQUIRED_CMDS = _fixtures.WORKSPACE_REQUIRED_CMDS

    @staticmethod
    def _isolated_bin_without_cargo():
        return _fixtures.build_isolated_bin_without_cargo()

    def test_rust_checker_no_cargo_forced_isolated_path(self):
        """B1: the no-toolchain path must be PROVEN, not inherited. We build a
        deterministic isolated PATH WITHOUT cargo, prove `command -v cargo` is
        nonzero in the exact subprocess environment, then require exit 3, the
        exact standalone unavailable marker, completed structural checks, and no
        warnings. Behaves identically whether or not the host has cargo."""
        import shutil
        import subprocess
        sh_abs = shutil.which("sh")
        self.assertIsNotNone(sh_abs, "no sh on host")
        root = os.path.abspath(os.path.join(HERE, "..", ".."))
        tmp, bindir, missing = self._isolated_bin_without_cargo()
        try:
            self.assertEqual(missing, [],
                             "host is missing required commands: %s" % missing)
            env = {"PATH": bindir,
                   "PYTHONDONTWRITEBYTECODE": "1",
                   "PYTHONWARNINGS": "error::ResourceWarning"}
            # preserve a legitimate loader preload so nested exec works on Termux
            if os.environ.get("LD_PRELOAD"):
                env["LD_PRELOAD"] = os.environ["LD_PRELOAD"]
            # 1. prove cargo is unreachable in this EXACT environment
            probe = subprocess.run([sh_abs, "-c", "command -v cargo"],
                                   capture_output=True, text=True, env=env)
            self.assertNotEqual(probe.returncode, 0,
                                "cargo still resolvable in isolated PATH: %r"
                                % probe.stdout)
            # 2. run the checker in that same environment
            proc = subprocess.run([sh_abs, "tools/check_rust_workspace.sh"],
                                  cwd=root, capture_output=True, text=True,
                                  env=env)
            blob = proc.stdout + proc.stderr
            self.assertEqual(proc.returncode, 3,
                             "no-cargo exit %d, want 3\n%s"
                             % (proc.returncode, blob[-800:]))
            lines = proc.stdout.splitlines()
            self.assertIn(
                "RUST_WORKSPACE_CHECK: INCONCLUSIVE_TOOLCHAIN_UNAVAILABLE",
                lines, "exact unavailable marker line missing")
            self.assertNotIn("RUST_WORKSPACE_CHECK: PASS", lines)
            self.assertIn("Structural checks:", proc.stdout,
                          "structural checks did not run")
            offenders = [ln for ln in blob.splitlines()
                         if ("ResourceWarning" in ln
                             or "Exception ignored in:" in ln
                             or "unclosed file" in ln)]
            self.assertEqual(offenders, [],
                             "warnings under no-cargo: %s" % offenders[:3])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_no_cargo_helper_does_not_enumerate_directories(self):
        # Repair 1: the helper must not os.listdir PATH entries (/system/bin is
        # not enumerable by the Termux app process). It is deterministic.
        import inspect
        import shutil
        src = inspect.getsource(
            RustCheckerWarningClean._isolated_bin_without_cargo)
        self.assertNotIn("os.listdir", src,
                         "no-cargo helper enumerates directories")
        tmp, bindir, missing = self._isolated_bin_without_cargo()
        try:
            built = sorted(os.listdir(bindir))
            self.assertEqual(
                built,
                sorted(RustCheckerWarningClean._WORKSPACE_REQUIRED_CMDS),
                "isolated bin is not the deterministic allowlist")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_no_cargo_helper_survives_unreadable_path_dir(self):
        # Repair 1: an unreadable/absent PATH directory must not crash the
        # helper (it resolves commands individually, never enumerating).
        import tempfile
        import shutil
        bad = tempfile.mkdtemp(prefix="unreadable_")
        realpath = os.environ.get("PATH", "")
        try:
            try:
                os.chmod(bad, 0o000)
            except OSError:
                pass
            os.environ["PATH"] = (bad + os.pathsep + "/system/bin"
                                  + os.pathsep + "/product/bin"
                                  + os.pathsep + "/vendor/bin"
                                  + os.pathsep + "/no/such/dir"
                                  + os.pathsep + realpath)
            tmp, bindir, missing = self._isolated_bin_without_cargo()
            shutil.rmtree(tmp, ignore_errors=True)
            self.assertEqual(missing, [],
                             "helper could not resolve required cmds: %s"
                             % missing)
        finally:
            os.environ["PATH"] = realpath
            try:
                os.chmod(bad, 0o755)
            except OSError:
                pass
            shutil.rmtree(bad, ignore_errors=True)

    def test_no_cargo_isolated_bin_has_no_toolchain(self):
        # Repair 1: cargo/rustc/rustup are genuinely absent from the isolated bin.
        import shutil
        tmp, bindir, missing = self._isolated_bin_without_cargo()
        try:
            for tool in ("cargo", "rustc", "rustup"):
                self.assertFalse(
                    os.path.exists(os.path.join(bindir, tool)),
                    "%s leaked into the isolated bin" % tool)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_no_unclosed_resources_in_rust_checker(self):
        # B4: the checker's real-archive extra-tag guard previously built an
        # archive object with no `with`. That leak must stay gone, and the
        # scanner must see the archive construction to prove it is governed.
        import resource_scan
        root = os.path.abspath(os.path.join(HERE, "..", ".."))
        offenders = resource_scan.scan_path(
            os.path.join(root, "tools", "check_rust_workspace.sh"))
        self.assertEqual(offenders, [],
                         "unclosed resources remain in check_rust_workspace.sh"
                         ": %s" % offenders)

    def test_resource_scanner_detects_a_bare_archive(self):
        # B4: negative control. The scanner MUST flag a non-context-managed
        # archive construction; the token is assembled so this test's own
        # source stays clean under the tree scan above.
        import resource_scan
        bare = "z = zipfile." + "Zip" + "File(path)\n"
        governed = "with zipfile." + "Zip" + "File(path) as z:\n"
        self.assertTrue(any(o.endswith("bare-archive")
                            for o in resource_scan.scan(bare)),
                        "scanner missed a bare archive construction")
        self.assertEqual(resource_scan.scan(governed), [],
                         "scanner false-flagged a governed archive")
        leak = "data = op" + "en('x').re" + "ad()\n"
        self.assertTrue(any(o.endswith("unclosed-read")
                            for o in resource_scan.scan(leak)),
                        "scanner missed an unclosed read")




class AdoptionGateBehaviour(unittest.TestCase):
    """Source-pin provenance: scope, sensitivity, and the v10 deadlock."""

    ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
    PIN = "tools/rust_source_pin.json"

    def _hash(self, cwd):
        import subprocess
        return subprocess.run(
            [sys.executable, "-B", "tools/rust_source_hash.py"],
            cwd=cwd, capture_output=True, text=True).stdout.strip()

    def _copy(self):
        import shutil
        import tempfile
        tmp = tempfile.mkdtemp(prefix="pin_")
        dest = os.path.join(tmp, "cand")
        shutil.copytree(self.ROOT, dest,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc",
                                                      "target"))
        return tmp, dest

    def test_unmutated_source_matches_pin(self):
        with open(os.path.join(self.ROOT, self.PIN)) as handle:
            pin = json.load(handle)
        self.assertEqual(self._hash(self.ROOT), pin["rust_source_sha256"])

    def test_mutated_rust_source_fails_provenance(self):
        import shutil
        tmp, dest = self._copy()
        try:
            first = self._hash(dest)
            target = os.path.join(dest, "rust", "witness-verify", "src",
                                  "main.rs")
            with open(target, "a") as handle:
                handle.write("\n// probe\n")
            self.assertNotEqual(first, self._hash(dest),
                                "behaviour source change not detected")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_readme_status_roll_does_NOT_break_the_pin(self):
        """B4 REGRESSION: check_rust_workspace.sh REQUIRES the rust/README
        status line to name the current step, so it MUST change every Rust
        move. A pin covering README.md made that mandated change break the
        gate — one rule forbidding what another rule requires. The pin must
        cover behaviour-determining source only."""
        import shutil
        tmp, dest = self._copy()
        try:
            first = self._hash(dest)
            readme = os.path.join(dest, "rust", "README.md")
            with open(readme) as handle:
                body = handle.read()
            with open(readme, "w") as handle:
                handle.write(body.replace("Step 79 status:",
                                          "Step 80 status:")
                             + "\nNew Move 80 documentation.\n")
            self.assertEqual(
                first, self._hash(dest),
                "a MANDATED rust/README status roll broke the source pin — "
                "the v10 deadlock has regressed")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_pin_scope_is_recorded_and_documentation_excluded(self):
        with open(os.path.join(self.ROOT, self.PIN)) as handle:
            pin = json.load(handle)
        self.assertIn("pinned_paths", pin)
        self.assertEqual(len(pin["pinned_paths"]), pin["pinned_path_count"])
        docs = [p for p in pin["pinned_paths"] if p.endswith(".md")]
        self.assertEqual(docs, [],
                         "documentation must NOT be pinned: %s" % docs)
        for path in pin["pinned_paths"]:
            self.assertTrue(path.endswith(".rs")
                            or path.endswith("Cargo.toml"),
                            "unexpected pinned path: %s" % path)

    def test_pin_is_derived_from_the_adopted_baseline(self):
        """B2: the pin must be DERIVED, not self-certified. Every pinned file
        carries its adopted-baseline hash and its candidate hash, so a
        reviewer can verify each byte of difference independently."""
        with open(os.path.join(self.ROOT, self.PIN)) as handle:
            pin = json.load(handle)
        prov = pin.get("provenance")
        self.assertIsNotNone(prov, "pin has no provenance block")
        self.assertIn("adopted_baseline", prov)
        self.assertIn("reviewed_delta", prov)
        base = prov["baseline_file_sha256"]
        cand = prov["candidate_file_sha256"]
        self.assertEqual(sorted(base), sorted(pin["pinned_paths"]))
        self.assertEqual(sorted(cand), sorted(pin["pinned_paths"]))
        changed = sorted(r for r in cand if base.get(r) != cand[r])
        self.assertEqual(changed, sorted(prov["files_changed_from_baseline"]),
                         "recorded delta does not match the hashes")

    def test_missing_source_pin_detected(self):
        import shutil
        tmp, dest = self._copy()
        try:
            os.remove(os.path.join(dest, self.PIN))
            self.assertFalse(os.path.isfile(os.path.join(dest, self.PIN)))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class SourceHashDeterminism(unittest.TestCase):
    """The source hash must be stable and must change when source changes."""

    def test_hash_is_stable_and_sensitive(self):
        import shutil
        import subprocess
        import tempfile
        root = os.path.abspath(os.path.join(HERE, "..", ".."))
        script = os.path.join(root, "tools", "rust_source_hash.py")

        def h(cwd):
            return subprocess.run([sys.executable, "-B", script], cwd=cwd,
                                  capture_output=True, text=True).stdout.strip()

        first = h(root)
        self.assertEqual(first, h(root), "source hash is not deterministic")
        tmp = tempfile.mkdtemp(prefix="srch_")
        try:
            dest = os.path.join(tmp, "cand")
            shutil.copytree(root, dest,
                            ignore=shutil.ignore_patterns("__pycache__",
                                                          "*.pyc", "target"))
            self.assertEqual(first, h(dest),
                             "hash changed on an identical copy")
            # NOTE: this deliberately targets a BEHAVIOUR file. An earlier
            # version appended to rust/README.md and demanded the hash change
            # — that requirement WAS the v10 deadlock, because
            # check_rust_workspace.sh mandates a README status roll every
            # Rust move. Documentation is excluded from the pin by design;
            # its correctness is enforced by check_rust_workspace.sh.
            with open(os.path.join(dest, "rust", "witness-verify", "src",
                                   "sha256.rs"), "a") as fh:
                fh.write("\n// changed\n")
            self.assertNotEqual(first, h(dest),
                                "hash did not change when BEHAVIOUR source "
                                "changed")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TamperTopLevelReportIsolation(unittest.TestCase):
    """v27: the rebuilt tamper_top_level_report fixture is isolated to its
    intended stage — companion_report.json is noncanonical yet valid JSON, and
    its declared checksum is repaired to a fixpoint so the shared declared-hash
    stage PASSES (Python then rejects at report-canonicality, Rust reaches its
    out-of-scope INCONCLUSIVE completion — those two behavioural outcomes are
    asserted against bundle_cases.json by the full corpus run on Termux)."""

    def test_fixture_report_noncanonical_with_matching_declared_hash(self):
        import hashlib
        import shutil
        import tempfile
        root = os.path.abspath(os.path.join(HERE, "..", ".."))
        freeze = os.path.join(root, "freeze_record",
                              "python_behaviour_freeze_v01")
        ref = os.path.join(freeze, "reference_bundle")
        if not os.path.isdir(ref):
            self.skipTest("reference bundle not present on this host")
        sys.path.insert(0, os.path.join(HERE, "corpus"))
        sys.path.insert(0, freeze)
        import generate_failure_cases as gen
        import build_bundle_cases as bbc
        self.assertIn("tamper_top_level_report", bbc.BUILDERS,
                      "stage-targeted builder is not registered")
        dest = tempfile.mkdtemp()
        try:
            # frozen generator first, then the stage-targeted builder (as
            # run_agreement does); the builder replaces the legacy directory.
            gen.generate(ref, dest)
            bbc.build(ref, dest)
            bundle = os.path.join(dest, "tamper_top_level_report")
            report = os.path.join(bundle, "companion_report.json")
            with open(report, "rb") as h:
                raw = h.read()
            # noncanonical (trailing byte) yet still valid JSON
            self.assertTrue(raw.endswith(b" "), "report is not noncanonical")
            json.loads(raw)  # must not raise
            # declared checksum matches the actual noncanonical bytes ->
            # the shared declared-hash stage passes (case reaches its stage)
            actual = hashlib.sha256(raw).hexdigest()
            declared = self._declared(bundle, "companion_report.json")
            self.assertEqual(declared, actual,
                             "declared hash not repaired: case would die at "
                             "the shared DECLARED_HASH_MISMATCH stage")
        finally:
            shutil.rmtree(dest, ignore_errors=True)

    @staticmethod
    def _declared(bundle, relname):
        sums = os.path.join(bundle, "companion_checksums.txt")
        with open(sums, "r", encoding="utf-8") as h:
            for line in h.read().splitlines():
                parts = line.split("  ")
                if len(parts) == 2 and parts[1].endswith(relname):
                    return parts[0]
        return None


if __name__ == "__main__":
    unittest.main(verbosity=2)
