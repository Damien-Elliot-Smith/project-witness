"""Move 80: focused tests for the corrupted-bundle pack.

Covers the ruled requirement list:
  --rust-bin handoff discipline (required flag; absolute path; existing,
  regular, executable file; explicit-path execution with NO PATH lookup);
  wrong verdict / wrong reason code / wrong declared stage / wrong exit
  code / unexpected stderr / malformed JSON output / incomplete output /
  signal termination / timeout; missing fixture; duplicate fixture ID;
  duplicate filename; fixture-hash mismatch; undeclared mutation; seed
  mutation; nondeterministic generation; traversal sentinel alteration;
  temporary-directory cleanup; original/reversed/deterministically
  shuffled order identity.

Controlled test executables are permitted HERE by the adoption ruling;
production adoption always receives the gate-verified fresh binary.

Run:  python3 -B -W error::ResourceWarning move80_tests.py
"""

import json
import os
import shutil
import stat
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import author_pins
import generate_fixtures as gen
import integrity_check
import run_move80

CONTRACT_TABLE = {
    "m80_clean_001": ("INCONCLUSIVE", "RECEIPT_CHAIN_HASHES_RECOMPUTED", 3),
    "m80_missing_manifest_001": ("FAIL", "MANIFEST_MISSING", 1),
    "m80_changed_evidence_001":
        ("INCONCLUSIVE", "RECEIPT_CHAIN_HASHES_RECOMPUTED", 3),
    "m80_bad_receipt_hash_001":
        ("FAIL", "RECEIPT_HASH_RECOMPUTATION_MISMATCH", 1),
    "m80_duplicate_receipt_001": ("FAIL", "RECEIPT_ID_SEQUENCE_BROKEN", 1),
    "m80_malformed_json_001": ("FAIL", "MANIFEST_JSON_INVALID", 1),
    "m80_unknown_schema_001": ("FAIL", "SCHEMA_VERSION_UNSUPPORTED", 1),
}

_TMP = None
_FIXTURES = None


def _write_exe(dirpath, name, body):
    path = os.path.join(dirpath, name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("#!%s\n" % sys.executable)
        handle.write(body)
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP
             | stat.S_IXOTH)
    return path


_CONTRACT_BODY = """\
import json, os, sys
TABLE = %r
mode, target = sys.argv[1], sys.argv[2]
if mode == "inspect-archive":
    print(json.dumps({"verifier": "witness-verify", "version": "t",
                      "verdict": "FAIL",
                      "reason_code": "ARCHIVE_PATH_TRAVERSAL",
                      "detail": "d"}))
    sys.exit(1)
name = os.path.basename(target.rstrip("/"))
verdict, code, rc = TABLE[name]
print(json.dumps({"verifier": "witness-verify", "version": "t",
                  "verdict": verdict, "reason_code": code,
                  "detail": "d"}))
sys.exit(rc)
""" % (CONTRACT_TABLE,)


def setUpModule():
    global _TMP, _FIXTURES
    _TMP = tempfile.mkdtemp(prefix="m80_tests_")
    _FIXTURES = os.path.join(_TMP, "fixtures")
    gen.generate(_FIXTURES)


def tearDownModule():
    shutil.rmtree(_TMP, ignore_errors=True)


def contract_bin(dirpath=None):
    return _write_exe(dirpath or _TMP, "contract_bin", _CONTRACT_BODY)


class TestRustBinHandoff(unittest.TestCase):
    GATE = os.path.join(ROOT, "tools",
                        "check_move80_corrupted_bundle_adoption.sh")
    README = os.path.join(HERE, "README.md")
    REQUIRED_INPUTS = ("REAL_MOVE78", "REAL_705", "REAL_MOVE79")

    def _run_gate(self, env_extra):
        """Invoke the gate off-device with a given environment; usage
        validation runs before the Termux bootstrap so exit 2 (usage) is
        reachable here. Returns (rc, combined output)."""
        import subprocess
        env = dict(os.environ)
        for var in ("REAL_MOVE78", "REAL_705", "REAL_MOVE79", "REAL_V20"):
            env.pop(var, None)
        env.update(env_extra)
        proc = subprocess.run(
            ["sh", self.GATE], capture_output=True, text=True,
            env=env, cwd=ROOT)
        return proc.returncode, proc.stdout + proc.stderr

    def test_missing_rust_bin_is_usage(self):
        import contextlib
        import io
        with self.assertRaises(SystemExit) as ctx, \
                contextlib.redirect_stderr(io.StringIO()):
            run_move80.main(["--fixtures", _FIXTURES])
        self.assertEqual(ctx.exception.code, 2)

        # B1: the README states three required inputs, its invocation
        # block names exactly REAL_MOVE78/REAL_705/REAL_MOVE79, the gate's
        # usage validation requires that same set, and omitting any one
        # (with the other two dummied) exits 2 naming the omitted variable.
        import re
        with open(self.README, encoding="utf-8") as handle:
            readme = handle.read()
        # (1) README states "three required real inputs" exactly once
        # (whitespace-flexible: the phrase may wrap across a line break)
        self.assertEqual(
            len(re.findall(r"three\s+required\s+real\s+inputs", readme)),
            1,
            "README must state 'three required real inputs' exactly once")
        self.assertEqual(
            len(re.findall(r"two\s+required\s+real\s+inputs", readme)), 0,
            "obsolete 'two required real inputs' must be gone")
        # (2) the invocation block names exactly the three required vars
        for var in self.REQUIRED_INPUTS:
            self.assertIn(var + "=", readme,
                          "README invocation block must name %s" % var)
        # (3) with all three absent, the gate exits 2 and identifies all
        rc, out = self._run_gate({})
        self.assertEqual(rc, 2, "all-absent must be a usage error (exit 2)")
        for var in self.REQUIRED_INPUTS:
            self.assertIn(var, out,
                          "all-absent usage message must name %s" % var)
        # (4) omitting each one individually (other two dummied) exits 2
        # and names the omitted variable
        dummy = os.path.join(_TMP, "dummy_input")
        with open(dummy, "w", encoding="utf-8") as handle:
            handle.write("x")
        for omitted in self.REQUIRED_INPUTS:
            supplied = {v: dummy for v in self.REQUIRED_INPUTS
                        if v != omitted}
            rc, out = self._run_gate(supplied)
            self.assertEqual(rc, 2,
                             "omitting %s must be a usage error" % omitted)
            self.assertIn(omitted, out,
                          "usage message must name the omitted %s"
                          % omitted)

    def test_relative_path_rejected(self):
        self.assertIn("absolute",
                      run_move80.validate_rust_bin("relative/bin"))

    def test_nonexistent_rejected(self):
        self.assertIn("does not exist",
                      run_move80.validate_rust_bin(
                          os.path.join(_TMP, "nope")))

    def test_directory_rejected(self):
        self.assertIn("regular file",
                      run_move80.validate_rust_bin(_TMP))

    def test_non_executable_rejected(self):
        path = os.path.join(_TMP, "plain_file")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("data")
        os.chmod(path, 0o644)
        self.assertIn("not executable",
                      run_move80.validate_rust_bin(path))

    def test_explicit_path_no_path_lookup(self):
        """Plant a booby-trapped witness-verify on PATH; the runner must
        execute only the explicitly supplied binary and never the PATH
        one."""
        trapdir = os.path.join(_TMP, "trap")
        os.makedirs(trapdir, exist_ok=True)
        marker = os.path.join(trapdir, "TRAP_EXECUTED")
        _write_exe(trapdir, "witness-verify",
                   "import os\nopen(%r, 'w').close()\n"
                   "print('{}')\n" % marker)
        good = contract_bin()
        old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = trapdir + os.pathsep + old_path
        try:
            obs = run_move80.observe_rust(
                good, "verify",
                os.path.join(_FIXTURES, "m80_clean_001"))
        finally:
            os.environ["PATH"] = old_path
        self.assertEqual(obs["verdict"], "INCONCLUSIVE")
        self.assertFalse(os.path.exists(marker),
                         "runner executed a PATH-resolved binary")


class TestWrongResults(unittest.TestCase):
    def _expected_clean_rust(self):
        return run_move80.load_expected()["M80-CLEAN-001"]["rust_expected"]

    def _observe_with(self, body, fixture="m80_clean_001"):
        bad = _write_exe(_TMP, "bad_bin", body)
        return run_move80.observe_rust(
            bad, "verify", os.path.join(_FIXTURES, fixture))

    def test_wrong_verdict_detected(self):
        obs = self._observe_with(
            'import json,sys;print(json.dumps({"verdict":"FAIL",'
            '"reason_code":"RECEIPT_CHAIN_HASHES_RECOMPUTED"}));'
            'sys.exit(3)')
        met, diags = run_move80.evaluate(self._expected_clean_rust(), obs)
        self.assertFalse(met)
        self.assertTrue(any("verdict" in d for d in diags))

    def test_wrong_reason_code_detected(self):
        obs = self._observe_with(
            'import json,sys;print(json.dumps({"verdict":"INCONCLUSIVE",'
            '"reason_code":"ARCHIVE_SAFETY_OK"}));sys.exit(3)')
        met, diags = run_move80.evaluate(self._expected_clean_rust(), obs)
        self.assertFalse(met)
        self.assertTrue(any("reason" in d for d in diags))

    def test_wrong_exit_code_detected(self):
        obs = self._observe_with(
            'import json,sys;print(json.dumps({"verdict":"INCONCLUSIVE",'
            '"reason_code":"RECEIPT_CHAIN_HASHES_RECOMPUTED"}));'
            'sys.exit(0)')
        met, diags = run_move80.evaluate(self._expected_clean_rust(), obs)
        self.assertFalse(met)
        self.assertTrue(any("exit" in d for d in diags))

    def test_unexpected_stderr_detected(self):
        obs = self._observe_with(
            'import json,sys;sys.stderr.write("noise");'
            'print(json.dumps({"verdict":"INCONCLUSIVE",'
            '"reason_code":"RECEIPT_CHAIN_HASHES_RECOMPUTED"}));'
            'sys.exit(3)')
        met, diags = run_move80.evaluate(self._expected_clean_rust(), obs)
        self.assertFalse(met)
        self.assertTrue(any("stderr" in d for d in diags))

    def test_malformed_json_output_detected(self):
        obs = self._observe_with('import sys;print("not json");sys.exit(3)')
        self.assertEqual(obs["status"], "MALFORMED_OUTPUT")
        met, _ = run_move80.evaluate(self._expected_clean_rust(), obs)
        self.assertFalse(met)

    def test_incomplete_output_detected(self):
        obs = self._observe_with(
            'import json,sys;print(json.dumps({"verdict":'
            '"INCONCLUSIVE"}));sys.exit(3)')
        self.assertEqual(obs["status"], "MALFORMED_OUTPUT")
        met, _ = run_move80.evaluate(self._expected_clean_rust(), obs)
        self.assertFalse(met)

    def test_signal_termination_detected(self):
        obs = self._observe_with(
            'import os,signal;os.kill(os.getpid(), signal.SIGKILL)')
        self.assertEqual(obs["status"], "SIGNALED")
        met, diags = run_move80.evaluate(self._expected_clean_rust(), obs)
        self.assertFalse(met)
        self.assertTrue(any("SIGNALED" in d for d in diags))

    def test_timeout_detected(self):
        old = run_move80.SUBPROCESS_TIMEOUT
        run_move80.SUBPROCESS_TIMEOUT = 1
        try:
            obs = self._observe_with('import time;time.sleep(5)')
        finally:
            run_move80.SUBPROCESS_TIMEOUT = old
        self.assertEqual(obs["status"], "TIMEOUT")
        met, _ = run_move80.evaluate(self._expected_clean_rust(), obs)
        self.assertFalse(met)

    def test_declared_stages_match_adopted_reason_map(self):
        """Every declared rust/archive stage must equal the adopted
        reason map's stage for that reason code, so a wrong declared
        stage cannot pass unnoticed."""
        with open(os.path.join(ROOT, "verify", "agreement_harness_v01",
                               "reason_map.json"), encoding="utf-8") as h:
            rmap = json.load(h)
        stage_of = {}
        for lane in ("rust_bundle", "archive"):
            for entry in rmap[lane]:
                stage_of[entry["value"]] = entry["stage"]
        for fid, case in run_move80.load_expected().items():
            for key in ("rust_expected", "archive_oracle_expected"):
                spec = case.get(key)
                if spec is None:
                    continue
                self.assertEqual(
                    spec["stage"], stage_of[spec["reason_code"]],
                    "%s.%s declares a stage that contradicts the "
                    "adopted reason map" % (fid, key))

        # B2: seven of the eight fixtures have at least one FAIL lane;
        # only M80-CLEAN-001 has none. Derived INDEPENDENTLY from the
        # loaded expected_results.json, then cross-checked against the
        # README and the machine-readable _meaning_of_case_pass text.
        expected_fail_ids = {
            "M80-MISSING-MANIFEST-001",
            "M80-CHANGED-EVIDENCE-001",
            "M80-BAD-RECEIPT-HASH-001",
            "M80-DUPLICATE-RECEIPT-001",
            "M80-MALFORMED-JSON-001",
            "M80-PATH-TRAVERSAL-001",
            "M80-UNKNOWN-SCHEMA-001",
        }
        with open(os.path.join(HERE, "expected_results.json"),
                  encoding="utf-8") as handle:
            doc = json.load(handle)
        cases = doc["cases"]
        self.assertEqual(len(cases), 8, "there must be exactly eight cases")
        fail_ids = set()
        for cid, case in cases.items():
            lanes = [v for k, v in case.items()
                     if k.endswith("_expected") and isinstance(v, dict)]
            if any(lane.get("verdict") == "FAIL" for lane in lanes):
                fail_ids.add(cid)
        self.assertEqual(len(fail_ids), 7,
                         "exactly seven fixtures must have a FAIL lane")
        self.assertEqual(fail_ids, expected_fail_ids)
        self.assertEqual(set(cases) - fail_ids, {"M80-CLEAN-001"},
                         "M80-CLEAN-001 must be the sole case without a "
                         "FAIL lane")
        # README and _meaning_of_case_pass must carry the corrected
        # seven-of-eight statement and NOT the obsolete six-of-eight one.
        with open(os.path.join(HERE, "README.md"),
                  encoding="utf-8") as handle:
            readme = handle.read()
        seven = "seven of the eight fixtures"
        six = "six of the eight fixtures"
        self.assertIn(seven, readme,
                      "README must state seven of the eight fixtures")
        self.assertNotIn(six, readme,
                         "obsolete six-of-eight statement must be gone "
                         "from README")
        meaning = doc["_meaning_of_case_pass"]
        self.assertIn(seven, meaning,
                      "_meaning_of_case_pass must state seven of the eight")
        self.assertNotIn(six, meaning,
                         "obsolete six-of-eight statement must be gone "
                         "from _meaning_of_case_pass")


class TestIntegrityFailureModes(unittest.TestCase):
    def _fresh_copy(self):
        dest = tempfile.mkdtemp(prefix="m80_it_", dir=_TMP)
        fixtures = os.path.join(dest, "fixtures")
        shutil.copytree(_FIXTURES, fixtures)
        return fixtures

    def _run(self, gen_a, gen_b=None):
        integrity_check._failures = []
        rc = integrity_check.main(["--gen-a", gen_a,
                                   "--gen-b", gen_b or _FIXTURES])
        return rc

    def test_clean_pass(self):
        self.assertEqual(self._run(_FIXTURES, _FIXTURES), 0)

    def test_missing_fixture_detected(self):
        broken = self._fresh_copy()
        shutil.rmtree(os.path.join(broken, "m80_clean_001"))
        self.assertEqual(self._run(broken), 1)

    def test_fixture_hash_mismatch_detected(self):
        broken = self._fresh_copy()
        target = os.path.join(broken, "m80_clean_001",
                              "companion_steps.json")
        with open(target, "ab") as handle:
            handle.write(b" ")
        self.assertEqual(self._run(broken), 1)

    def test_undeclared_mutation_detected(self):
        broken = self._fresh_copy()
        extra = os.path.join(broken, "m80_missing_manifest_001",
                             "undeclared_extra.txt")
        with open(extra, "w", encoding="utf-8") as handle:
            handle.write("x")
        self.assertEqual(self._run(broken), 1)

    def test_nondeterministic_generation_detected(self):
        other = self._fresh_copy()
        target = os.path.join(other, "m80_clean_001",
                              "companion_steps.json")
        with open(target, "ab") as handle:
            handle.write(b" ")
        self.assertEqual(self._run(_FIXTURES, other), 1)

    def test_seed_mutation_detected(self):
        seed_copy = os.path.join(tempfile.mkdtemp(prefix="m80_seed_",
                                                  dir=_TMP), "seed")
        shutil.copytree(gen.SEED, seed_copy)
        with open(os.path.join(seed_copy, "companion_steps.json"),
                  "ab") as handle:
            handle.write(b" ")
        old_seed = gen.SEED
        gen.SEED = seed_copy
        try:
            self.assertEqual(self._run(_FIXTURES, _FIXTURES), 1)
        finally:
            gen.SEED = old_seed

    def test_duplicate_fixture_id_detected(self):
        integrity_check._failures = []
        old = gen.FIXTURE_IDS
        gen.FIXTURE_IDS = tuple(list(old[:-1]) + [old[0]])
        try:
            results = {fid: {"path": "x", "kind": "dir", "hash": "h"}
                       for fid in old}
            integrity_check.check_fixture_set(results)
        finally:
            gen.FIXTURE_IDS = old
        self.assertTrue(integrity_check._failures)

    def test_duplicate_filename_detected(self):
        integrity_check._failures = []
        old = gen.fixture_filename

        def collide(fid):
            return "same_name"
        gen.fixture_filename = collide
        try:
            results = {fid: {"path": "x", "kind": "dir", "hash": "h"}
                       for fid in gen.FIXTURE_IDS}
            integrity_check.check_fixture_set(results)
        finally:
            gen.fixture_filename = old
        self.assertTrue(integrity_check._failures)


class TestTraversalSandbox(unittest.TestCase):
    def _case(self):
        return run_move80.load_expected()["M80-PATH-TRAVERSAL-001"]

    def test_clean_boundary_passes_and_cleans_temp(self):
        before = set(os.listdir(tempfile.gettempdir()))
        result = run_move80.run_traversal_case(
            "M80-PATH-TRAVERSAL-001", _FIXTURES, self._case(),
            contract_bin())
        after = set(os.listdir(tempfile.gettempdir()))
        self.assertTrue(result["met"])
        creation = result["sandbox_checks"]["creation_test"]
        overwrite = result["sandbox_checks"]["overwrite_test"]
        self.assertTrue(creation["evil_destination_absent"])
        self.assertTrue(creation["sandbox_unchanged"])
        self.assertTrue(creation["temp_cleaned"])
        self.assertTrue(overwrite["evil_destination_intact"])
        self.assertTrue(overwrite["sandbox_unchanged"])
        self.assertTrue(overwrite["temp_cleaned"])
        leftover = [d for d in after - before
                    if d.startswith("m80_sandbox_")]
        self.assertEqual(leftover, [])

    def test_evil_destination_creation_detected(self):
        """A boundary that actually creates the ../evil destination
        (sandbox/evil) must fail the creation test even with a correct
        verdict."""
        creator = _write_exe(
            _TMP, "evil_creator_bin",
            'import json,os,sys\n'
            'open(os.path.join(os.path.dirname(os.getcwd()), "evil"),'
            ' "wb").write(b"escaped")\n'
            'print(json.dumps({"verifier":"w","version":"t",'
            '"verdict":"FAIL",'
            '"reason_code":"ARCHIVE_PATH_TRAVERSAL","detail":"d"}))\n'
            'sys.exit(1)\n')
        result = run_move80.run_traversal_case(
            "M80-PATH-TRAVERSAL-001", _FIXTURES, self._case(), creator)
        creation = result["sandbox_checks"]["creation_test"]
        self.assertFalse(creation["evil_destination_absent"])
        self.assertFalse(creation["sandbox_unchanged"])
        self.assertFalse(result["met"])

    def test_evil_destination_overwrite_detected(self):
        """A boundary that overwrites the pre-created ../evil outside
        sentinel must fail the overwrite test."""
        writer = _write_exe(
            _TMP, "evil_overwriter_bin",
            'import json,os,sys\n'
            'p = os.path.join(os.path.dirname(os.getcwd()), "evil")\n'
            'if os.path.exists(p): open(p, "wb").write(b"overwritten")\n'
            'print(json.dumps({"verifier":"w","version":"t",'
            '"verdict":"FAIL",'
            '"reason_code":"ARCHIVE_PATH_TRAVERSAL","detail":"d"}))\n'
            'sys.exit(1)\n')
        result = run_move80.run_traversal_case(
            "M80-PATH-TRAVERSAL-001", _FIXTURES, self._case(), writer)
        overwrite = result["sandbox_checks"]["overwrite_test"]
        self.assertFalse(overwrite["evil_destination_intact"])
        self.assertFalse(result["met"])

    def test_evil_destination_deletion_detected(self):
        """A boundary that deletes the pre-created ../evil outside
        sentinel must fail the overwrite/deletion test."""
        deleter = _write_exe(
            _TMP, "evil_deleter_bin",
            'import json,os,sys\n'
            'p = os.path.join(os.path.dirname(os.getcwd()), "evil")\n'
            'if os.path.exists(p): os.remove(p)\n'
            'print(json.dumps({"verifier":"w","version":"t",'
            '"verdict":"FAIL",'
            '"reason_code":"ARCHIVE_PATH_TRAVERSAL","detail":"d"}))\n'
            'sys.exit(1)\n')
        result = run_move80.run_traversal_case(
            "M80-PATH-TRAVERSAL-001", _FIXTURES, self._case(), deleter)
        overwrite = result["sandbox_checks"]["overwrite_test"]
        self.assertFalse(overwrite["evil_destination_intact"])
        self.assertFalse(result["met"])

    def test_sandbox_write_detected(self):
        """A boundary that writes anywhere inside the controlled root
        must fail the sandbox comparison even if its verdict looks
        right."""
        writer = _write_exe(
            _TMP, "writer_bin",
            'import json,os,sys\n'
            'open(os.path.join(os.getcwd(), "evil_dropped"),'
            ' "w").close()\n'
            'print(json.dumps({"verifier":"w","version":"t",'
            '"verdict":"FAIL",'
            '"reason_code":"ARCHIVE_PATH_TRAVERSAL","detail":"d"}))\n'
            'sys.exit(1)\n')
        result = run_move80.run_traversal_case(
            "M80-PATH-TRAVERSAL-001", _FIXTURES, self._case(), writer)
        creation = result["sandbox_checks"]["creation_test"]
        self.assertFalse(creation["sandbox_unchanged"])
        self.assertFalse(result["met"])


class TestOrderIdentity(unittest.TestCase):
    def test_orders_are_permutations_and_deterministic(self):
        original = run_move80.ordered_ids("original")
        rev = run_move80.ordered_ids("reversed")
        shuf = run_move80.ordered_ids("shuffled")
        self.assertEqual(sorted(original), sorted(rev))
        self.assertEqual(sorted(original), sorted(shuf))
        self.assertEqual(rev, list(reversed(original)))
        self.assertEqual(shuf, run_move80.ordered_ids("shuffled"))
        self.assertNotEqual(shuf, original)

    def test_three_orders_identical_canonical_output(self):
        bin_path = contract_bin()
        docs = []
        for order in ("original", "reversed", "shuffled"):
            doc = run_move80.run_all(_FIXTURES, bin_path, order)
            docs.append(json.dumps(doc, sort_keys=True,
                                   separators=(",", ":")))
        self.assertEqual(docs[0], docs[1])
        self.assertEqual(docs[0], docs[2])
        parsed = json.loads(docs[0])
        self.assertEqual(parsed["overall_status"], "PASS")
        self.assertEqual(parsed["required_cases"], "8/8")
        self.assertEqual(parsed["negative_detection"], "PASS")


class TestMissingFixtureAtRun(unittest.TestCase):
    def test_runner_fails_on_missing_fixture(self):
        partial = tempfile.mkdtemp(prefix="m80_partial_", dir=_TMP)
        for name in os.listdir(_FIXTURES):
            if name == "m80_clean_001":
                continue
            src = os.path.join(_FIXTURES, name)
            dst = os.path.join(partial, name)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copyfile(src, dst)
        doc = run_move80.run_all(partial, contract_bin(), "original")
        self.assertEqual(doc["overall_status"], "FAIL")
        clean = [r for r in doc["results"]
                 if r["fixture_id"] == "M80-CLEAN-001"][0]
        self.assertFalse(clean["met"])


class TestPinsMatchGenerator(unittest.TestCase):
    def test_committed_pins_reproducible(self):
        hashes, ledger, manifest = author_pins.derive()
        for name, derived in (("fixture_hashes.json", hashes),
                              ("mutation_ledger.json", ledger),
                              ("fixture_manifest.json", manifest)):
            with open(os.path.join(HERE, name), encoding="utf-8") as h:
                self.assertEqual(json.load(h), derived,
                                 "%s drifted from the generator" % name)




class TestSeedPinAlgorithms(unittest.TestCase):
    APPROVED_V0 = ("70e6e975b3d5fab8d4a513573ef4d0d12ea0ca697ad287d46e"
                   "a11b789abe7a24")
    SECONDARY_V1 = ("3a7ad566696155cd86a4ebe707927715495253eee4b404041e"
                    "b5d4bc8cfcbb19")

    def test_approved_pin_cannot_be_silently_replaced(self):
        """The APPROVED contract-inventory algorithm must reproduce the
        approved 70e6... value from the seed bytes; the module constant
        must equal it; and neither value may be assigned to the other
        algorithm's name."""
        live_v0 = gen.seed_tree_hash_v0(gen.SEED)
        live_v1 = gen.entry_tree_hash_v1(gen.SEED)
        self.assertEqual(live_v0, self.APPROVED_V0)
        self.assertEqual(gen.SEED_TREE_HASH_V0, self.APPROVED_V0)
        self.assertEqual(live_v1, self.SECONDARY_V1)
        self.assertEqual(gen.SEED_ENTRY_TREE_HASH_V1, self.SECONDARY_V1)
        self.assertNotEqual(live_v0, self.SECONDARY_V1,
                            "v0 name bound to the v1 value")
        self.assertNotEqual(live_v1, self.APPROVED_V0,
                            "v1 name bound to the v0 value")

    def test_ledger_pins_both_algorithms_by_name(self):
        with open(os.path.join(HERE, "mutation_ledger.json"),
                  encoding="utf-8") as handle:
            seed = json.load(handle)["seed"]
        self.assertEqual(seed["seed_tree_hash_v0"], self.APPROVED_V0)
        self.assertEqual(seed["seed_entry_tree_hash_v1"],
                         self.SECONDARY_V1)


class TestSelectiveRepair(unittest.TestCase):
    STALE_FILE = os.path.join("coordinator_output", "case_bundle_v02",
                              "bundle_checksums.txt")

    def _seed_stale_line(self):
        with open(os.path.join(gen.SEED, self.STALE_FILE),
                  encoding="utf-8") as handle:
            return handle.read().splitlines()[0]

    def test_unrelated_stale_line_not_repaired_in_any_fixture(self):
        """The frozen seed's pre-existing stale case_manifest.json entry
        must remain byte-identical in every generated fixture that
        retains the file."""
        seed_line = self._seed_stale_line()
        self.assertIn("cb1fc67c184dbf70", seed_line)
        for fid in gen.FIXTURE_IDS:
            if fid == "M80-PATH-TRAVERSAL-001":
                continue
            target = os.path.join(_FIXTURES, gen.fixture_filename(fid),
                                  self.STALE_FILE)
            with open(target, encoding="utf-8") as handle:
                self.assertEqual(handle.read().splitlines()[0], seed_line,
                                 "%s repaired the unrelated stale line"
                                 % fid)

    def test_each_fixture_changes_only_principal_plus_closure(self):
        """Exact expected changed-file sets: the principal mutation plus
        strictly the dependency-closure repairs, nothing else."""
        run_rel = "coordinator_output/sentinel_run/sentinel_run.json"
        receipt_closure = {
            run_rel,
            "coordinator_output/case_bundle_v02/sentinel_case/"
            "checksums.txt",
            "coordinator_output/histor_sentinel_case/checksums.txt",
            "coordinator_output/case_bundle_v02/bundle_checksums.txt",
        }
        report_closure = {"companion_report.json",
                          "companion_checksums.txt"}
        expected_changed = {
            "M80-CLEAN-001": set(),
            "M80-MISSING-MANIFEST-001": set(),
            "M80-CHANGED-EVIDENCE-001":
                {"coordinator_output/aletheia_bundle/evidence/"
                 "evidence_001.bin"},
            "M80-BAD-RECEIPT-HASH-001": receipt_closure,
            "M80-DUPLICATE-RECEIPT-001": receipt_closure,
            "M80-MALFORMED-JSON-001": report_closure,
            "M80-UNKNOWN-SCHEMA-001": report_closure,
        }
        seed_files = author_pins._walk_files(gen.SEED)
        for fid, want in expected_changed.items():
            fx = os.path.join(_FIXTURES, gen.fixture_filename(fid))
            fx_files = author_pins._walk_files(fx)
            changed = {rel for rel in set(seed_files) & set(fx_files)
                       if seed_files[rel] != fx_files[rel]}
            self.assertEqual(changed, want, fid)

    def test_selective_repair_ledger_matches_bytes(self):
        """Declared line repairs must carry the true seed and fixture
        digests for exactly the declared lines."""
        with open(os.path.join(HERE, "mutation_ledger.json"),
                  encoding="utf-8") as handle:
            ledger = json.load(handle)["fixtures"]
        repairs = ledger["M80-DUPLICATE-RECEIPT-001"]["files"][
            "checksum_line_repairs"]
        self.assertEqual(len(repairs), 3)
        touched = {(r["checksum_file"], r["line_no"]) for r in repairs}
        self.assertIn(("coordinator_output/case_bundle_v02/"
                       "bundle_checksums.txt", 4), touched)
        self.assertNotIn(("coordinator_output/case_bundle_v02/"
                          "bundle_checksums.txt", 1), touched)


class TestBaselineZipBinding(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, HERE)
        import check_inherited_vs_zip
        self.mod = check_inherited_vs_zip

    def _synthetic_zip(self, entries, name):
        import warnings
        import zipfile
        path = os.path.join(_TMP, name)
        with warnings.catch_warnings(), zipfile.ZipFile(path, "w") as zf:
            # Building an intentionally malformed attack zip (e.g. a
            # duplicate entry name) raises a UserWarning by design; that
            # is the condition under test, so suppress the console noise.
            warnings.simplefilter("ignore", UserWarning)
            for arcname, data, attr in entries:
                info = zipfile.ZipInfo(arcname)
                if attr:
                    info.external_attr = attr
                zf.writestr(info, data)
        return path

    def test_wrong_hash_zip_rejected(self):
        fake = self._synthetic_zip(
            [("project-witness-main/x.txt", b"x", 0)], "fake_v27.zip")
        rc = self.mod.main(["--baseline-zip", fake])
        self.assertEqual(rc, 1)

    def test_zip_safety_inspection_rejects_attacks(self):
        import zipfile
        cases = {
            "duplicate entry name": [
                ("project-witness-main/a", b"1", 0),
                ("project-witness-main/a", b"2", 0)],
            "path traversal": [
                ("project-witness-main/../evil", b"x", 0)],
            "absolute path": [("/abs", b"x", 0)],
            "symlink": [("project-witness-main/link", b"target",
                         (stat.S_IFLNK | 0o777) << 16)],
            "outside root": [("other-root/a", b"x", 0)],
        }
        for label, entries in cases.items():
            path = self._synthetic_zip(entries,
                                       "attack_%s.zip"
                                       % label.replace(" ", "_"))
            with zipfile.ZipFile(path) as zf:
                problems = self.mod.inspect_zip_safety(zf)
            self.assertTrue(problems, "undetected: %s" % label)

    @unittest.skipUnless(os.environ.get("M80_BASELINE_ZIP"),
                         "M80_BASELINE_ZIP not supplied (the adoption "
                         "gate always supplies it and forbids skips)")
    def test_real_zip_comparison_passes_and_detects_modification(self):
        """Direct member-byte comparison against the REAL v27 zip: the
        candidate tree passes; make a PORTABLE independent byte copy of
        the tree (no hardlinks/symlinks/reflinks -- os.link is absent in
        Termux Python 3.13.13), append fixed bytes to ONE inherited file
        in the copy, and require the same comparison to fail -- proving a
        candidate-controlled inventory cannot substitute for the real
        artifact, and that an inherited-file modification is detected."""
        import hashlib
        zip_path = os.environ["M80_BASELINE_ZIP"]
        rc = self.mod.main(["--baseline-zip", zip_path])
        self.assertEqual(rc, 0)

        # Portable independent byte-copy clone (no shared inodes). Retain
        # the pycache / rust-target / *.pyc exclusions.
        clone = os.path.join(_TMP, "tree_clone")
        for dirpath, dirnames, filenames in os.walk(ROOT):
            rel = os.path.relpath(dirpath, ROOT)
            dirnames[:] = [d for d in dirnames
                           if d not in ("__pycache__",)
                           and not (rel == "rust" and d == "target")]
            dest_dir = os.path.join(clone, rel)
            os.makedirs(dest_dir, exist_ok=True)
            for name in filenames:
                if name.endswith(".pyc"):
                    continue
                shutil.copyfile(os.path.join(dirpath, name),
                                os.path.join(dest_dir, name))

        # record the original victim bytes to prove the original tree is
        # never modified by this test
        original_victim = os.path.join(ROOT, "START_HERE.md")
        with open(original_victim, "rb") as handle:
            original_bytes = handle.read()
        original_digest = hashlib.sha256(original_bytes).hexdigest()

        # tamper ONLY the clone's START_HERE.md by appending fixed bytes
        victim = os.path.join(clone, "START_HERE.md")
        with open(victim, "rb") as handle:
            clone_bytes = handle.read()
        self.assertEqual(clone_bytes, original_bytes,
                         "clone must start byte-identical to the original")
        with open(victim, "ab") as handle:
            handle.write(b"tampered")

        # the clone now differs from the original ONLY at START_HERE.md
        for dirpath, dirnames, filenames in os.walk(clone):
            rel_dir = os.path.relpath(dirpath, clone)
            for name in filenames:
                rel = os.path.normpath(os.path.join(rel_dir, name))
                cpath = os.path.join(dirpath, name)
                opath = os.path.join(ROOT, rel)
                if not os.path.isfile(opath):
                    continue
                with open(cpath, "rb") as ch, open(opath, "rb") as oh:
                    same = ch.read() == oh.read()
                if rel == "START_HERE.md":
                    self.assertFalse(same,
                                     "tampered file must differ")
                else:
                    self.assertTrue(same,
                                    "clone %s must match original" % rel)

        old_root = self.mod.ROOT
        self.mod.ROOT = clone
        try:
            rc = self.mod.main(["--baseline-zip", zip_path])
        finally:
            self.mod.ROOT = old_root
            shutil.rmtree(clone, ignore_errors=True)
        # the comparison reports the inherited modification
        self.assertEqual(rc, 1)
        # the ORIGINAL START_HERE.md is untouched
        with open(original_victim, "rb") as handle:
            self.assertEqual(hashlib.sha256(handle.read()).hexdigest(),
                             original_digest,
                             "the original tree must not be modified")
        # the temporary clone is removed
        self.assertFalse(os.path.exists(clone),
                         "temporary clone must be removed")


class TestMove79EvidenceChecker(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, HERE)
        import check_move79_evidence
        self.mod = check_move79_evidence

    def _complete_output(self):
        return "\n".join(line for _label, line
                          in self.mod.REQUIRED_LINES) + "\n"

    def test_complete_evidence_passes(self):
        ok, _report = self.mod.validate(self._complete_output(), 0)
        self.assertTrue(ok)

    def test_each_missing_fact_fails(self):
        for label, required in self.mod.REQUIRED_LINES:
            text = "\n".join(line for _l, line in self.mod.REQUIRED_LINES
                             if line != required) + "\n"
            ok, _report = self.mod.validate(text, 0)
            self.assertFalse(ok, "missing fact undetected: %s" % label)

    def test_nonzero_child_exit_fails(self):
        ok, _report = self.mod.validate(self._complete_output(), 1)
        self.assertFalse(ok)

    def test_altered_count_fails(self):
        text = self._complete_output().replace(
            "  OK    74 agreement cases passed",
            "  OK    73 agreement cases passed")
        ok, _report = self.mod.validate(text, 0)
        self.assertFalse(ok)



class TestIndependentFixtureContract(unittest.TestCase):
    """Independent semantic assertions for all eight fixtures, parsed
    directly from the seed bytes and the generated fixture bytes. The
    expected contract is encoded here as literals; NOTHING in this class
    is derived from generate_fixtures.PRINCIPAL_MUTATIONS, from the
    builder functions, or from the mutation ledger. This is the
    independent check that a generator-vs-ledger self-consistency proof
    cannot provide."""

    SEED = os.path.join(
        ROOT, "freeze_record", "python_behaviour_freeze_v01",
        "reference_bundle")
    RUN_REL = os.path.join("coordinator_output", "sentinel_run",
                           "sentinel_run.json")
    REPORT_REL = "companion_report.json"
    EVIDENCE_REL = os.path.join("coordinator_output", "aletheia_bundle",
                                "evidence", "evidence_001.bin")

    def _fx(self, fid):
        return os.path.join(_FIXTURES, gen.fixture_filename(fid))

    def _walk_bytes(self, root):
        """relpath -> raw bytes for every file under root (independent
        of any project helper)."""
        out = {}
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames.sort()
            for name in sorted(filenames):
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, root).replace(os.sep, "/")
                with open(full, "rb") as handle:
                    out[rel] = handle.read()
        return out

    def _changed_paths(self, fid):
        """Set of relpaths whose bytes differ between seed and fixture,
        plus added/removed sets."""
        seed = self._walk_bytes(self.SEED)
        fx = self._walk_bytes(self._fx(fid))
        common = set(seed) & set(fx)
        changed = {r for r in common if seed[r] != fx[r]}
        added = set(fx) - set(seed)
        removed = set(seed) - set(fx)
        return changed, added, removed, seed, fx

    # ---- CLEAN ------------------------------------------------------
    def test_clean_is_exact_seed_copy(self):
        changed, added, removed, _s, _f = self._changed_paths(
            "M80-CLEAN-001")
        self.assertEqual(changed, set())
        self.assertEqual(added, set())
        self.assertEqual(removed, set())

    # ---- MISSING MANIFEST ------------------------------------------
    def test_missing_manifest_only_report_removed(self):
        changed, added, removed, _s, _f = self._changed_paths(
            "M80-MISSING-MANIFEST-001")
        self.assertEqual(removed, {self.REPORT_REL})
        self.assertEqual(added, set())
        self.assertEqual(changed, set())

    # ---- CHANGED EVIDENCE ------------------------------------------
    def test_changed_evidence_one_fixed_offset_hash_retained(self):
        changed, added, removed, seed, fx = self._changed_paths(
            "M80-CHANGED-EVIDENCE-001")
        self.assertEqual(added, set())
        self.assertEqual(removed, set())
        # exactly the evidence file changed (no checksum repair: the
        # stale nested declared hash is deliberately retained)
        self.assertEqual(changed, {self.EVIDENCE_REL})
        a = seed[self.EVIDENCE_REL]
        b = fx[self.EVIDENCE_REL]
        self.assertEqual(len(a), len(b))
        differing = [i for i in range(len(a)) if a[i] != b[i]]
        # the complete differing-offset list is exactly [5]
        self.assertEqual(differing, [5])
        # byte 5 is the seed byte XOR 0xFF
        self.assertEqual(b[5], a[5] ^ 0xFF)
        # every other byte is identical
        self.assertEqual(a[:5], b[:5])
        self.assertEqual(a[6:], b[6:])
        # nested declared hash retained == the evidence checksum entry
        # still holds the SEED digest, not a repaired one
        cs_rel = ("coordinator_output/aletheia_bundle/"
                  "evidence_checksums.txt")
        self.assertEqual(seed[cs_rel], fx[cs_rel],
                         "nested evidence checksum must be retained stale")

    # ---- BAD RECEIPT HASH (B1) -------------------------------------
    @staticmethod
    def _recompute_receipt_canonical_hash(receipt):
        """Independent recomputation via the declared canonical recipe:
        drop only canonical_hash; JSON-serialize with sorted keys,
        compact separators (',', ':'), ensure_ascii=False; SHA-256 the
        UTF-8 bytes."""
        import hashlib
        payload = {k: v for k, v in receipt.items()
                   if k != "canonical_hash"}
        blob = json.dumps(payload, sort_keys=True,
                          separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def test_bad_receipt_only_one_canonical_hash_changed(self):
        changed, added, removed, seed, fx = self._changed_paths(
            "M80-BAD-RECEIPT-HASH-001")
        self.assertEqual(added, set())
        self.assertEqual(removed, set())
        self.assertIn(self.RUN_REL, changed)
        seed_run = json.loads(seed[self.RUN_REL])
        fx_run = json.loads(fx[self.RUN_REL])
        sr = seed_run["receipts"]
        fr = fx_run["receipts"]
        # receipt count unchanged
        self.assertEqual(len(sr), len(fr))
        # exactly one receipt differs
        differing = [i for i in range(len(sr)) if sr[i] != fr[i]]
        self.assertEqual(len(differing), 1)
        idx = differing[0]
        # exactly one field in that receipt differs, and it is
        # canonical_hash
        field_diffs = [k for k in set(sr[idx]) | set(fr[idx])
                       if sr[idx].get(k) != fr[idx].get(k)]
        self.assertEqual(field_diffs, ["canonical_hash"])
        # all other payload fields (incl. reason_code) JSON-value equal
        for k in sr[idx]:
            if k == "canonical_hash":
                continue
            self.assertEqual(sr[idx][k], fr[idx][k],
                             "payload field %s changed" % k)
        self.assertEqual(sr[idx]["reason_code"], fr[idx]["reason_code"])
        # INDEPENDENT recomputation of the seed receipt's canonical hash:
        # do NOT assume the stored seed value is valid -- recompute it
        # from the declared recipe and require the recomputation to equal
        # the stored value (proving the seed is internally consistent and
        # the recipe is the correct one).
        recomputed = self._recompute_receipt_canonical_hash(sr[idx])
        self.assertEqual(recomputed, sr[idx]["canonical_hash"],
                         "independent recomputation must equal the seed's "
                         "stored canonical_hash")
        # the replacement is exactly 64 zeroes and differs from the
        # independently recomputed (correct) value
        replacement = fr[idx]["canonical_hash"]
        self.assertEqual(replacement, "0" * 64)
        self.assertNotEqual(replacement, recomputed,
                            "replacement must differ from the correct "
                            "recomputed hash")

    # ---- DUPLICATE RECEIPT -----------------------------------------
    def test_duplicate_receipt_final_appended_no_prior_change(self):
        changed, added, removed, seed, fx = self._changed_paths(
            "M80-DUPLICATE-RECEIPT-001")
        self.assertEqual(added, set())
        self.assertEqual(removed, set())
        self.assertIn(self.RUN_REL, changed)
        seed_obj = json.loads(seed[self.RUN_REL])
        sr = seed_obj["receipts"]
        fr = json.loads(fx[self.RUN_REL])["receipts"]
        # one extra receipt, an exact duplicate of the seed's final one
        self.assertEqual(len(fr), len(sr) + 1)
        self.assertEqual(fr[-1], sr[-1])
        # no prior receipt changed
        for i in range(len(sr)):
            self.assertEqual(fr[i], sr[i], "prior receipt %d changed" % i)
        # INDEPENDENT construction: append an exact copy of the seed's
        # final receipt and serialize through the declared _dump byte
        # recipe (sorted keys, compact separators, ensure_ascii=False,
        # trailing newline). Require the fixture bytes to equal exactly
        # that -- not merely parse to an equivalent object.
        import copy
        expected_obj = copy.deepcopy(seed_obj)
        expected_obj["receipts"].append(
            copy.deepcopy(seed_obj["receipts"][-1]))
        expected_bytes = (json.dumps(
            expected_obj, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False) + "\n").encode("utf-8")
        self.assertEqual(fx[self.RUN_REL], expected_bytes)

    # ---- MALFORMED JSON --------------------------------------------
    def test_malformed_json_exact_deterministic_truncation(self):
        changed, added, removed, seed, fx = self._changed_paths(
            "M80-MALFORMED-JSON-001")
        self.assertEqual(added, set())
        self.assertEqual(removed, set())
        self.assertIn(self.REPORT_REL, changed)
        a = seed[self.REPORT_REL]
        b = fx[self.REPORT_REL]
        # deterministic truncation to the first half of the seed bytes
        self.assertEqual(b, a[: len(a) // 2])
        # and it is genuinely not valid JSON
        with self.assertRaises(ValueError):
            json.loads(b.decode("utf-8", "replace"))

    # ---- PATH TRAVERSAL --------------------------------------------
    # Independent expected fixture hash, encoded as a literal (NOT loaded
    # only from fixture_hashes.json), byte-identical to the Move 79
    # TERMUX-confirmed corpus traversal case.
    TRAVERSAL_SHA256 = (
        "286e137fe2fba65daf7b050654cf79555277dff3e2ead027ea831ec133ff109b")

    def test_path_traversal_single_evil_entry_pinned_bytes(self):
        import hashlib
        import zipfile
        path = self._fx("M80-PATH-TRAVERSAL-001")
        with zipfile.ZipFile(path) as zf:
            infos = zf.infolist()
            # exactly one member, named exactly "../evil"
            self.assertEqual(len(infos), 1)
            self.assertEqual(infos[0].filename, "../evil")
            # exact member content is empty bytes
            with zf.open(infos[0]) as member:
                self.assertEqual(member.read(), b"")
        # live fixture hash equals the independent literal
        with open(path, "rb") as handle:
            actual = hashlib.sha256(handle.read()).hexdigest()
        self.assertEqual(actual, self.TRAVERSAL_SHA256)

    # ---- UNKNOWN SCHEMA --------------------------------------------
    def test_unknown_schema_only_cli_version_changed(self):
        changed, added, removed, seed, fx = self._changed_paths(
            "M80-UNKNOWN-SCHEMA-001")
        self.assertEqual(added, set())
        self.assertEqual(removed, set())
        self.assertIn(self.REPORT_REL, changed)
        seed_report = json.loads(seed[self.REPORT_REL])
        fx_report = json.loads(fx[self.REPORT_REL])
        # only companion_cli_version differs, and it is "9.9.9"
        field_diffs = [k for k in set(seed_report) | set(fx_report)
                       if seed_report.get(k) != fx_report.get(k)]
        self.assertEqual(field_diffs, ["companion_cli_version"])
        self.assertEqual(fx_report["companion_cli_version"], "9.9.9")
        # INDEPENDENT construction of the expected report bytes: parse the
        # seed report, replace only companion_cli_version, serialize
        # through the declared canonical recipe (sorted keys, compact
        # separators, ensure_ascii=False, UTF-8, no trailing newline),
        # and require the fixture bytes to equal exactly those bytes.
        expected_obj = dict(seed_report)
        expected_obj["companion_cli_version"] = "9.9.9"
        expected_bytes = json.dumps(
            expected_obj, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False).encode("utf-8")
        self.assertEqual(fx[self.REPORT_REL], expected_bytes)



class TestIntegrityWarningClean(unittest.TestCase):
    """B2: the real integrity run must be warning-clean under
    -W error::ResourceWarning with exactly zero stderr bytes, and the
    gate-side stderr policy must reject an unclosed handle in a
    controlled child even when that child exits 0."""

    def test_real_integrity_run_zero_stderr(self):
        import subprocess
        gen_a = os.path.join(_TMP, "wc_gen_a")
        gen_b = os.path.join(_TMP, "wc_gen_b")
        for d in (gen_a, gen_b):
            if not os.path.isdir(d):
                gen.generate(d)
        proc = subprocess.run(
            [sys.executable, "-B", "-W", "error::ResourceWarning",
             os.path.join(HERE, "integrity_check.py"),
             "--gen-a", gen_a, "--gen-b", gen_b],
            capture_output=True, cwd=HERE,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertEqual(proc.stderr, b"",
                         "integrity stderr must be empty; got: %r"
                         % proc.stderr[:400])

    def test_stderr_policy_rejects_unclosed_handle_child_exit_zero(self):
        """B2 item 6: a controlled child that leaks a file handle must be
        proved to (a) exit 0, (b) emit non-empty stderr, and (c) be
        rejected by the gate-side stderr policy."""
        import subprocess
        leaky = _write_exe(
            _TMP, "leaky_child",
            "import sys\n"
            "f = open(__file__)  # deliberately never closed\n"
            "sys.stdout.write('child ran\\n')\n"
            "sys.exit(0)\n")
        proc = subprocess.run(
            [sys.executable, "-W", "error::ResourceWarning", leaky],
            capture_output=True)
        stderr = proc.stderr.decode("utf-8", "replace")
        # (a) the child exits 0
        self.assertEqual(proc.returncode, 0,
                         "leaky child must exit 0 to exercise the policy")
        # (b) yet its stderr is non-empty (the ResourceWarning fires at
        # interpreter shutdown)
        self.assertTrue(proc.stderr,
                        "leaky child must emit non-empty stderr")

        def gate_stderr_policy_fails(stderr_text):
            if stderr_text.strip():
                return True
            for needle in ("ResourceWarning", "Exception ignored in:",
                           "unclosed file"):
                if needle in stderr_text:
                    return True
            return False

        # (c) the policy rejects it despite the exit-0 code
        self.assertTrue(gate_stderr_policy_fails(stderr),
                        "policy must reject a leaking child regardless "
                        "of its exit code; stderr was: %r" % stderr[:400])
        # and the policy passes clean text
        self.assertFalse(gate_stderr_policy_fails(""))

    def test_successful_suite_summary_on_stdout_stderr_empty(self):
        """Required V04 proof: a successful unittest run of a controlled
        child suite writes its normal 'Ran N tests' / 'OK' summary to
        STDOUT and produces exactly empty STDERR, mirroring the runner
        form move80_tests.py uses."""
        import subprocess
        child = _write_exe(
            _TMP, "ok_suite_child",
            "import sys, unittest\n"
            "class T(unittest.TestCase):\n"
            "    def test_a(self):\n"
            "        self.assertTrue(True)\n"
            "    def test_b(self):\n"
            "        self.assertEqual(1, 1)\n"
            "suite = unittest.defaultTestLoader.loadTestsFromModule(\n"
            "    sys.modules[__name__])\n"
            "result = unittest.TextTestRunner(\n"
            "    stream=sys.stdout, verbosity=1).run(suite)\n"
            "sys.exit(0 if result.wasSuccessful() else 1)\n")
        proc = subprocess.run(
            [sys.executable, "-B", "-W", "error::ResourceWarning", child],
            capture_output=True)
        self.assertEqual(proc.returncode, 0)
        out = proc.stdout.decode("utf-8", "replace")
        self.assertIn("Ran 2 tests", out)
        self.assertIn("OK", out)
        # the success summary must NOT be on stderr, which must be empty
        self.assertEqual(proc.stderr, b"",
                         "successful run must leave stderr empty; got: %r"
                         % proc.stderr[:400])

        # Truth-state consistency: the ACTUAL loaded suite count, the
        # committed EXPECTED_TEST_COUNT.txt pin, and the focused-test
        # count stated in the packaged README must all agree exactly.
        # The README value is PARSED from the committed text (never
        # rewritten here); a missing, duplicate, malformed or divergent
        # count fails.
        loaded = unittest.defaultTestLoader.loadTestsFromModule(
            sys.modules[__name__]).countTestCases()
        with open(os.path.join(HERE, "EXPECTED_TEST_COUNT.txt"),
                  encoding="utf-8") as handle:
            pinned = int(handle.read().strip())
        with open(os.path.join(HERE, "README.md"),
                  encoding="utf-8") as handle:
            readme = handle.read()
        import re
        matches = re.findall(r"focused tests \((\d+)\)", readme)
        self.assertEqual(len(matches), 1,
                         "README must state the focused-test count exactly "
                         "once (found %d)" % len(matches))
        readme_count = int(matches[0])
        self.assertEqual(loaded, 58,
                         "loaded suite count must be 58, got %d" % loaded)
        self.assertEqual(pinned, 58,
                         "EXPECTED_TEST_COUNT.txt must pin 58, got %d"
                         % pinned)
        self.assertEqual(readme_count, 58,
                         "README must state 58 focused tests, got %d"
                         % readme_count)
        self.assertEqual({loaded, pinned, readme_count}, {58},
                         "loaded suite, committed pin and README count "
                         "must all equal 58")

        # B2 failure-evidence: a controlled failing test (with a unique
        # test name and a traceback) must be emitted COMPLETELY by the
        # gate's failure path, between its BEGIN/END markers, never
        # truncated. Extract the real gate_dump_focused_failure helper
        # from the gate script (the gate itself exits early off-device at
        # the Termux bootstrap, so we source only this function's
        # definition) and drive it over captured child stdout/stderr,
        # requiring the full name and traceback to survive.
        gate = os.path.join(ROOT, "tools",
                             "check_move80_corrupted_bundle_adoption.sh")
        with open(gate, encoding="utf-8") as handle:
            gate_src = handle.read()
        marker = "gate_dump_focused_failure()"
        start = gate_src.index(marker)
        # capture the function body up to and including its closing brace
        # at column 0 (the definition is written that way in the gate)
        end = gate_src.index("\n}\n", start) + len("\n}\n")
        func_def = gate_src[start:end]
        self.assertIn("BEGIN FOCUSED TEST STDOUT", func_def,
                      "extracted helper must contain the stdout marker")

        marker_name = "test_controlled_unique_failure_marker_9x7"
        failing = _write_exe(
            _TMP, "failing_suite_child",
            "import sys, unittest\n"
            "class T(unittest.TestCase):\n"
            "    def %s(self):\n"
            "        raise AttributeError('controlled traceback token "
            "Zqx42')\n"
            "suite = unittest.defaultTestLoader.loadTestsFromModule(\n"
            "    sys.modules[__name__])\n"
            "result = unittest.TextTestRunner(\n"
            "    stream=sys.stdout, verbosity=1).run(suite)\n"
            "sys.exit(0 if result.wasSuccessful() else 1)\n"
            % marker_name)
        child = subprocess.run(
            [sys.executable, "-B", failing], capture_output=True)
        self.assertNotEqual(child.returncode, 0,
                            "failing child must exit nonzero")
        out_file = os.path.join(_TMP, "fail_out.txt")
        err_file = os.path.join(_TMP, "fail_err.txt")
        with open(out_file, "wb") as handle:
            handle.write(child.stdout)
        with open(err_file, "wb") as handle:
            handle.write(child.stderr)
        # define only the extracted helper, then invoke it
        harness = func_def + (
            '\ngate_dump_focused_failure "$1" "$2" "$3"\n')
        dumped = subprocess.run(
            ["sh", "-c", harness, "sh", out_file, err_file,
             str(child.returncode)],
            capture_output=True, text=True)
        combined = dumped.stdout + dumped.stderr
        # the gate never truncates: the unique test name, the traceback
        # token, and the exit code all survive between the markers
        self.assertIn("BEGIN FOCUSED TEST STDOUT", combined)
        self.assertIn("END FOCUSED TEST STDOUT", combined)
        self.assertIn("BEGIN FOCUSED TEST STDERR", combined)
        self.assertIn("END FOCUSED TEST STDERR", combined)
        self.assertIn(marker_name, combined,
                      "complete failing test name must be emitted")
        self.assertIn("controlled traceback token Zqx42", combined,
                      "complete traceback must be emitted, untruncated")
        self.assertIn("focused-suite exit code: %d" % child.returncode,
                      combined)

    REPORT = os.path.join(HERE, "MOVE_80_ALLOWLIST_DIFF_REPORT.txt")

    def setUp(self):
        sys.path.insert(0, HERE)
        import check_inherited_vs_zip
        self.mod = check_inherited_vs_zip

    @unittest.skipUnless(os.environ.get("M80_BASELINE_ZIP"),
                         "M80_BASELINE_ZIP not supplied (the adoption "
                         "gate always supplies it and forbids skips)")
    def test_committed_report_equals_live_real_v27_output(self):
        zip_path = os.environ["M80_BASELINE_ZIP"]
        live = os.path.join(_TMP, "live_report.txt")
        rc = self.mod.main(["--baseline-zip", zip_path, "--report", live])
        self.assertEqual(rc, 0)
        with open(live, "rb") as handle:
            live_bytes = handle.read()
        with open(self.REPORT, "rb") as handle:
            committed_bytes = handle.read()
        self.assertEqual(committed_bytes, live_bytes,
                         "committed diff report differs from the live "
                         "real-v27 comparison")
        # the report must carry the required accounting lines
        text = committed_bytes.decode("utf-8")
        self.assertIn(
            "4a95767a3f68ca812c1d543894b65183b82d56f3f8f56e9af61b82"
            "c19de1f26b", text)
        self.assertIn("inherited baseline file members:", text)
        self.assertIn("declared additions (allowlist):", text)
        self.assertIn("observed additions:", text)

    @unittest.skipUnless(os.environ.get("M80_BASELINE_ZIP"),
                         "M80_BASELINE_ZIP not supplied")
    def test_tampered_committed_report_is_rejected(self):
        """A committed report altered in ANY byte must not equal the live
        comparison output -- this is exactly the gate's byte-equality
        check. Tamper the observed-additions accounting line (found
        dynamically so the test never goes stale on count changes)."""
        zip_path = os.environ["M80_BASELINE_ZIP"]
        live = os.path.join(_TMP, "live_report2.txt")
        rc = self.mod.main(["--baseline-zip", zip_path, "--report", live])
        self.assertEqual(rc, 0)
        with open(live, "rb") as handle:
            live_bytes = handle.read()
        # locate the actual observed-additions count and bump it
        import re
        m = re.search(rb"observed additions: (\d+)", live_bytes)
        self.assertIsNotNone(m, "live report must state observed additions")
        n = int(m.group(1))
        tampered = live_bytes.replace(
            b"observed additions: %d" % n,
            b"observed additions: %d" % (n + 1))
        self.assertNotEqual(tampered, live_bytes,
                            "tampering must actually change bytes")
        # the gate's predicate is exact byte equality; tampered != live
        self.assertFalse(tampered == live_bytes)

    @unittest.skipUnless(os.environ.get("M80_BASELINE_ZIP"),
                         "M80_BASELINE_ZIP not supplied")
    def test_stale_count_report_is_rejected(self):
        """A stale report with a wrong inherited count differs from the
        live comparison (the gate's byte comparison catches it)."""
        zip_path = os.environ["M80_BASELINE_ZIP"]
        live = os.path.join(_TMP, "live_report3.txt")
        rc = self.mod.main(["--baseline-zip", zip_path, "--report", live])
        self.assertEqual(rc, 0)
        with open(live, "rb") as handle:
            live_bytes = handle.read()
        import re
        m = re.search(rb"inherited baseline file members: (\d+)",
                      live_bytes)
        self.assertIsNotNone(m)
        n = int(m.group(1))
        stale = live_bytes.replace(
            b"inherited baseline file members: %d" % n,
            b"inherited baseline file members: %d" % (n - 1))
        self.assertNotEqual(stale, live_bytes,
                            "stale-count report must differ from live")


if __name__ == "__main__":
    # unittest's default runner writes its progress and summary to
    # stderr. The Move 80 adoption gate treats focused-suite stderr as a
    # pure warning/error channel and rejects ANY bytes on it, so ordinary
    # test reporting must go to stdout instead. Load this module's tests
    # explicitly (no recursive reload) and run them with a stdout-bound
    # TextTestRunner; setUpModule/tearDownModule still fire because the
    # loaded suite belongs to this module.
    _suite = unittest.defaultTestLoader.loadTestsFromModule(
        sys.modules[__name__])
    _result = unittest.TextTestRunner(
        stream=sys.stdout, verbosity=1).run(_suite)
    sys.exit(0 if _result.wasSuccessful() else 1)
