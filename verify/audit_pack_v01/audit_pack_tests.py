#!/usr/bin/env python3
"""Move 85 focused test suite.

Stdout-bound runner, pinned count, warning-clean, target-portable.

Scope note, stated plainly: this environment has no Rust toolchain, so the
adopted verifier is neither built nor executed here. The Python lane IS
genuinely executed. The Rust lane is exercised end-to-end through the real
pack builder using a stand-in verifier, which proves the builder's logic
and establishes nothing about the adopted binary.

Design rule enforced throughout: `adopted_facts.json` is a CLAIM MANIFEST.
Every test below checks it AGAINST an external authority — the adopted
archive bytes, adopted gate or source bytes, or fresh execution. No test
treats a value as established because that file contains it.
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
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import build_audit_pack as packer  # noqa: E402

GATE = os.path.join(ROOT, "tools", "check_move85_audit_pack_adoption.sh")
ALLOWLIST = os.path.join(HERE, "allowlist_move85.json")
README = os.path.join(HERE, "README.md")
FACTS = os.path.join(HERE, "adopted_facts.json")
HANDOFF = os.path.join(ROOT, "HANDOFF_MOVES_71_TO_85.md")
CHANGELOG = os.path.join(ROOT, "CHANGELOG_MOVE_85.md")
PACK_TOOL = os.path.join(HERE, "build_audit_pack.py")

DEMO_FIXTURE_TOOL = os.path.join(
    ROOT, "verify", "demo_v01", "build_demo_fixtures.py")
FROZEN_BUNDLE = os.path.join(
    ROOT, "freeze_record", "python_behaviour_freeze_v01", "reference_bundle")
COMPANION = os.path.join(
    ROOT, "src", "12_companion_cli_v031", "companion.py")
MAIN_RS = os.path.join(ROOT, "rust", "witness-verify", "src", "main.rs")
MOVE79_GATE = os.path.join(
    ROOT, "tools", "check_move79_instrument_adoption.sh")

#: externally pinned; never read from the candidate
ADOPTED_M84_SHA = \
    "0c06017a871adc23b50bdfda272a30fb6843dbb50fbb4632284b037090e7e880"
ADOPTED_M84_ZIP = os.path.join(
    os.sep, "mnt", "user-data", "outputs",
    "project-witness-MOVE_84_candidate_v07.zip")

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
    supplied = os.environ.get("MOVE85_TEST_SH")
    if supplied:
        return _require_abs_exec(os.path.realpath(supplied),
                                 "MOVE85_TEST_SH (trusted shell)")
    found = shutil.which("sh")
    if not found:
        raise RuntimeError(
            "no shell available: set MOVE85_TEST_SH to the trusted shell")
    return _require_abs_exec(os.path.realpath(found), "fallback shell")


TEST_SH = _resolve_test_sh()
_TMP = None


def setUpModule():
    global _TMP
    import tempfile
    _TMP = tempfile.mkdtemp(prefix="m85_tests_")


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


LINE = ('{"verifier": "witness-verify", "version": '
        '"0.0.8-step79-diagnostics", "verdict": "%s", '
        '"reason_code": "%s", "detail": "ok"}')


def _standin(name, clean_digest, fail_reason="FILE_HASH_MISMATCH",
             clean_verdict="INCONCLUSIVE", clean_exit=3,
             fail_verdict="FAIL", fail_exit=1):
    """Reproduces the ADOPTED shape: clean and nested-tamper are
    indistinguishable; a top-level tamper is detected. A test double for
    the builder, never an authority for adopted behaviour."""
    return _write_python_exe(name, (
        "import hashlib, os, sys\n"
        "root = sys.argv[-1]\n"
        "with open(os.path.join(root, 'companion_steps.json'), 'rb') as h:\n"
        "    d = hashlib.sha256(h.read()).hexdigest()\n"
        "if d != %r:\n"
        "    sys.stdout.write(%r + chr(10))\n"
        "    sys.exit(%d)\n"
        "sys.stdout.write(%r + chr(10))\n"
        "sys.exit(%d)\n"
        % (clean_digest, LINE % (fail_verdict, fail_reason), fail_exit,
           LINE % (clean_verdict, "RECEIPT_CHAIN_HASHES_RECOMPUTED"),
           clean_exit)))


def _load(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _facts():
    return json.loads(_load(FACTS))


def _claims():
    return {c["id"]: c for c in _facts()["claims"]}


class PackHarness(unittest.TestCase):
    def _fixtures(self, tag):
        outdir = os.path.join(_TMP, "fx_" + tag)
        manifest = os.path.join(_TMP, "fx_%s.json" % tag)
        proc = _run([PYTHON_BIN, "-B", DEMO_FIXTURE_TOOL,
                     "--source", FROZEN_BUNDLE, "--outdir", outdir,
                     "--manifest-out", manifest])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        with open(manifest, encoding="utf-8") as handle:
            return manifest, json.load(handle)["cases"]

    def _clean_digest(self, cases):
        clean = [c for c in cases if c["case_id"] == "clean"][0]
        with open(os.path.join(clean["root"], "companion_steps.json"),
                  "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()

    def _build(self, tag, verifier, manifest, publish=False,
               divergences=("stage_manifest_json_invalid",
                            "stage_report_field_missing_repaired")):
        staging = os.path.join(_TMP, "stage_" + tag)
        os.makedirs(staging, exist_ok=True)
        argv = [PYTHON_BIN, "-B", PACK_TOOL, "--verifier", verifier,
                "--python-bin", PYTHON_BIN, "--companion", COMPANION,
                "--fixtures", manifest, "--staging", staging]
        for div in divergences:
            argv += ["--divergence-id", div]
        if publish:
            pub = os.path.join(_TMP, "pub_" + tag)
            os.makedirs(pub, exist_ok=True)
            argv += ["--publish-to", pub]
        return _run(argv), staging

    def _setup(self, tag, **kw):
        manifest, cases = self._fixtures(tag)
        verifier = _standin("sv_%s.py" % tag, self._clean_digest(cases),
                            **kw)
        return manifest, cases, verifier


class TestFactsManifestIsNeverAnAuthority(unittest.TestCase):
    """Correction 2: every measurable claim is checked against an
    external authority, never against the manifest."""

    def test_manifest_declares_itself_a_claim_manifest(self):
        text = _load(FACTS)
        self.assertIn("CLAIM MANIFEST ONLY", text)
        self.assertIn("never compare an authority against this file", text)

    def test_every_claim_names_an_authority_and_a_method(self):
        for claim_id, claim in _claims().items():
            self.assertIn("status", claim, claim_id)
            self.assertIn("authority", claim, claim_id)
            self.assertTrue(claim["authority"], claim_id)
            if claim["status"] not in ("not_claimed", "unestablished"):
                self.assertIn("how_verified", claim, claim_id)

    def test_every_status_is_in_the_declared_vocabulary(self):
        facts = _facts()
        vocabulary = set(facts["_status_vocabulary"])
        for claim_id, claim in _claims().items():
            self.assertIn(claim["status"], vocabulary, claim_id)

    def test_the_vocabulary_distinguishes_the_required_categories(self):
        """Correction 6: no flat 'established' label."""
        vocabulary = set(_facts()["_status_vocabulary"])
        for required in ("historically_established",
                         "freshly_reproduced_by_move_85",
                         "established_android_termux_aarch64_only",
                         "known_limitation", "unestablished",
                         "not_claimed"):
            self.assertIn(required, vocabulary, required)
        self.assertNotIn("established", vocabulary)

    def test_no_claim_uses_a_flat_established_label(self):
        for claim_id, claim in _claims().items():
            self.assertNotEqual(claim["status"], "established", claim_id)

    def test_the_baseline_hash_is_checked_against_the_real_archive(self):
        """The manifest's copy is compared to a recomputation of the
        externally supplied artifact, not the reverse."""
        if not os.path.isfile(ADOPTED_M84_ZIP):
            self.skipTest("adopted Move 84 v07 archive not available here")
        with open(ADOPTED_M84_ZIP, "rb") as handle:
            recomputed = hashlib.sha256(handle.read()).hexdigest()
        self.assertEqual(recomputed, ADOPTED_M84_SHA)
        self.assertEqual(_facts()["_baseline"]["claimed_sha256"],
                         recomputed)

    def test_the_manifest_never_claims_to_establish_anything(self):
        text = _load(FACTS)
        self.assertIn("Nothing in this file is evidence", text)


class TestNoPassClaimsAreProperlySeparated(unittest.TestCase):
    """Correction 1: source-level contract and empirical observation are
    distinct, and neither claims global reachability."""

    def _verdict_constants(self):
        """Derived from the ADOPTED Rust source, not from the manifest."""
        return set(re.findall(r"const (VERDICT_[A-Z_]+)\s*:", _load(MAIN_RS)))

    def test_adopted_source_declares_exactly_two_verdict_constants(self):
        self.assertEqual(self._verdict_constants(),
                         {"VERDICT_FAIL", "VERDICT_INCONCLUSIVE"})

    def test_no_pass_verdict_constant_exists(self):
        self.assertNotIn("VERDICT_PASS", self._verdict_constants())

    def test_the_source_level_claim_is_labelled_a_contract(self):
        claim = _claims()["rust_no_pass_verdict_constant"]
        self.assertEqual(claim["status"], "source_level_contract")
        self.assertIn("NOT a proof", claim["does_not_establish"])
        self.assertIn("reachable", claim["does_not_establish"])

    def test_the_empirical_claim_is_scoped_to_observation(self):
        claim = _claims()["rust_no_pass_observed"]
        self.assertIn("observed", claim["statement"].lower())
        self.assertIn("does not establish global reachability",
                      claim["does_not_establish"])

    def test_no_move85_material_claims_global_reachability(self):
        forbidden = re.compile(
            r"no reachable PASS path (?:exists|is possible)"
            r"|proves no PASS|PASS is unreachable anywhere",
            re.I)
        for path in (FACTS, README, HANDOFF):
            self.assertIsNone(forbidden.search(_load(path)), path)

    def test_the_handoff_states_both_claims_and_their_limit(self):
        text = _load(HANDOFF)
        self.assertIn("Source-level contract", text)
        self.assertIn("Empirical", text)
        self.assertIn("no such proof is claimed", text.lower())


class TestDivergenceIdsComeFromTheAdoptedGate(unittest.TestCase):
    """Correction 3: the adopted Move 79 gate is the authority."""

    def _adopted_ids(self):
        match = re.search(r'export EXPECT_DIV_IDS="([^"]+)"',
                          _load(MOVE79_GATE))
        self.assertIsNotNone(match, "adopted gate does not export the IDs")
        return sorted(match.group(1).split())

    def test_the_adopted_gate_declares_exactly_two_ids(self):
        self.assertEqual(self._adopted_ids(),
                         ["stage_manifest_json_invalid",
                          "stage_report_field_missing_repaired"])

    def test_the_manifest_claim_matches_the_adopted_gate(self):
        claim = _claims()["adopted_divergence_ids"]
        for div in self._adopted_ids():
            self.assertIn(div, claim["statement"])
        self.assertIn("Move 79 gate", claim["authority"])

    def test_the_handoff_names_both_ids(self):
        text = _load(HANDOFF)
        for div in self._adopted_ids():
            self.assertIn(div, text)

    def test_the_generic_markers_remain_required(self):
        text = _load(HANDOFF)
        self.assertIn("SYSTEM_AGREEMENT_RESULT: FAIL", text)
        self.assertIn("BEHAVIOURAL_DIVERGENCE_DETECTED", text)

    def test_the_gate_reads_the_ids_from_the_adopted_gate(self):
        code = _load(GATE)
        self.assertIn("EXPECT_DIV_IDS", code)
        self.assertIn("check_move79_instrument_adoption.sh", code)


class TestPublicationContract(PackHarness):
    """Correction 4: the pack is a gate-generated publication."""

    def test_the_pack_is_not_in_the_source_allowlist(self):
        data = json.loads(_load(ALLOWLIST))
        for rel in data["added_paths"]:
            self.assertNotIn("audit_pack_v1/", rel)
        self.assertIn("_pack_is_a_publication_not_a_source_artifact", data)

    def test_the_published_structure_is_exactly_as_specified(self):
        manifest, _cases, verifier = self._setup("struct")
        proc, staging = self._build("struct", verifier, manifest)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        pack = os.path.join(staging, packer.PACK_DIRNAME)
        for name in ("MANIFEST.json", "INSTRUCTIONS.md", "KNOWN_LIMITS.md",
                     "SHA256SUMS"):
            self.assertTrue(os.path.isfile(os.path.join(pack, name)), name)
        for case_id in packer.DEMO_CASES:
            self.assertTrue(os.path.isdir(
                os.path.join(pack, "bundles", case_id)), case_id)
            obs = os.path.join(pack, "observed", case_id)
            for name in ("rust.stdout", "rust.meta", "python.stdout",
                         "python.meta"):
                self.assertTrue(os.path.isfile(os.path.join(obs, name)),
                                "%s/%s" % (case_id, name))

    def test_the_manifest_labels_measurements_and_explanation(self):
        manifest, _cases, verifier = self._setup("labels")
        _proc, staging = self._build("labels", verifier, manifest)
        pack = os.path.join(staging, packer.PACK_DIRNAME)
        data = json.loads(_load(os.path.join(pack, "MANIFEST.json")))
        self.assertEqual(data["authoritative_measurements"], ["observed/"])
        self.assertEqual(sorted(data["explanatory_text"]),
                         ["INSTRUCTIONS.md", "KNOWN_LIMITS.md"])

    def test_sha256sums_covers_every_published_file(self):
        manifest, _cases, verifier = self._setup("sums")
        _proc, staging = self._build("sums", verifier, manifest)
        pack = os.path.join(staging, packer.PACK_DIRNAME)
        listed = set()
        for line in _load(os.path.join(pack, "SHA256SUMS")).splitlines():
            digest, rel = line.split("  ", 1)
            listed.add(rel)
            full = os.path.join(pack, rel)
            self.assertEqual(packer.sha256_file(full), digest, rel)
        on_disk = set()
        for dirpath, _dn, filenames in os.walk(pack):
            for name in filenames:
                if name == "SHA256SUMS":
                    continue
                rel = os.path.relpath(os.path.join(dirpath, name), pack)
                on_disk.add(rel.replace(os.sep, "/"))
        self.assertEqual(listed, on_disk)

    def test_nothing_is_published_when_a_check_fails(self):
        manifest, cases = self._fixtures("nopub")
        liar = _standin("sv_nopub.py", self._clean_digest(cases),
                        clean_verdict="PASS", clean_exit=0)
        proc, _staging = self._build("nopub", liar, manifest, publish=True)
        self.assertEqual(proc.returncode, 1)
        pub = os.path.join(_TMP, "pub_nopub")
        self.assertEqual(os.listdir(pub), [])

    def test_publication_refuses_an_existing_target(self):
        """Publishing twice into the same directory must fail the second
        time. Each generation uses its own staging root; the publication
        directory is deliberately shared."""
        manifest, _cases, verifier = self._setup("twicea")
        shared = os.path.join(_TMP, "pub_shared_target")
        if os.path.isdir(shared):
            shutil.rmtree(shared)
        os.makedirs(shared)

        def _generate(tag):
            staging = os.path.join(_TMP, "stage_" + tag)
            os.makedirs(staging, exist_ok=True)
            return _run([PYTHON_BIN, "-B", PACK_TOOL,
                         "--verifier", verifier,
                         "--python-bin", PYTHON_BIN,
                         "--companion", COMPANION,
                         "--fixtures", manifest, "--staging", staging,
                         "--publish-to", shared,
                         "--divergence-id", "stage_manifest_json_invalid",
                         "--divergence-id",
                         "stage_report_field_missing_repaired"])

        first = _generate("twicea")
        self.assertEqual(first.returncode, 0, first.stdout)
        second = _generate("twiceb")
        self.assertEqual(second.returncode, 1)
        self.assertIn(b"publication target exists", second.stdout)


class TestDeterminismBoundary(PackHarness):
    """Correction 5: the representation reproduces; builds do not."""

    def test_manifest_and_documents_regenerate_byte_identically(self):
        manifest, _cases, verifier = self._setup("det")
        _p1, s1 = self._build("det1", verifier, manifest)
        _p2, s2 = self._build("det2", verifier, manifest)
        for name in ("MANIFEST.json", "INSTRUCTIONS.md", "KNOWN_LIMITS.md",
                     "SHA256SUMS"):
            a = os.path.join(s1, packer.PACK_DIRNAME, name)
            b = os.path.join(s2, packer.PACK_DIRNAME, name)
            with open(a, "rb") as fa, open(b, "rb") as fb:
                self.assertEqual(fa.read(), fb.read(), name)

    def test_the_manifest_carries_no_volatile_data(self):
        manifest, _cases, verifier = self._setup("volatile")
        _proc, staging = self._build("volatile", verifier, manifest)
        text = _load(os.path.join(staging, packer.PACK_DIRNAME,
                                  "MANIFEST.json"))
        self.assertIsNone(re.search(r"\d{4}-\d{2}-\d{2}", text))
        self.assertIsNone(re.search(r"\d+\.\d+s", text))
        self.assertNotIn(_TMP, text)
        self.assertNotIn("/tmp/", text)
        self.assertNotIn("/home/", text)
        self.assertNotIn("/data/data/", text)

    def test_the_determinism_scope_is_stated_in_the_manifest(self):
        manifest, _cases, verifier = self._setup("scope")
        _proc, staging = self._build("scope", verifier, manifest)
        data = json.loads(_load(os.path.join(
            staging, packer.PACK_DIRNAME, "MANIFEST.json")))
        scope = data["determinism_scope"]
        self.assertIn("representation only", scope)
        self.assertIn("NOT a claim that Rust binaries or builds are "
                      "reproducible", scope)

    def test_no_move85_material_claims_reproducible_builds(self):
        forbidden = re.compile(
            r"reproducible build(?!s\b[^.]{0,40}not)", re.I)
        for path in (README, HANDOFF):
            text = _load(path)
            for match in forbidden.finditer(text):
                window = text[max(0, match.start() - 120):match.end() + 120]
                self.assertTrue(
                    re.search(r"not|does not|no ", window, re.I),
                    "%s appears to claim reproducible builds" % path)


class TestPackMeasurementsAreDerivedFromExecution(PackHarness):
    def test_a_full_pack_build_succeeds(self):
        manifest, _cases, verifier = self._setup("ok")
        proc, _s = self._build("ok", verifier, manifest)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn(b"MOVE_85_AUDIT_PACK: PASS", proc.stdout)
        self.assertEqual(proc.stderr, b"")

    def test_a_rust_pass_aborts_the_pack(self):
        manifest, cases = self._fixtures("liar")
        liar = _standin("sv_liar.py", self._clean_digest(cases),
                        clean_verdict="PASS", clean_exit=0)
        proc, _s = self._build("liar", liar, manifest)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"a Rust PASS was observed", proc.stdout)

    def test_losing_the_nested_blindness_aborts_the_pack(self):
        """If the verifier ever gains nested detection, the pack must fail
        loudly rather than keep asserting the old limitation."""
        manifest, _cases = self._fixtures("sees")
        sees = _write_python_exe("sv_sees.py", (
            "import os, sys\n"
            "root = sys.argv[-1]\n"
            "t = os.path.join(root, 'coordinator_output', "
            "'aletheia_bundle', 'evidence', 'evidence_001.bin')\n"
            "with open(t, 'rb') as h:\n"
            "    d = h.read()\n"
            "if d[5] != 0x65:\n"
            "    sys.stdout.write(%r + chr(10))\n"
            "    sys.exit(1)\n"
            "sys.stdout.write(%r + chr(10))\n"
            "sys.exit(3)\n"
            % (LINE % ("FAIL", "NESTED"),
               LINE % ("INCONCLUSIVE", "RECEIPT_CHAIN_HASHES_RECOMPUTED"))))
        proc, _s = self._build("sees", sees, manifest)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"documented blindness was not observed", proc.stdout)

    def test_a_verifier_that_never_detects_aborts_the_pack(self):
        manifest, cases = self._fixtures("blind")
        blind = _standin("sv_blind.py", self._clean_digest(cases),
                         fail_verdict="INCONCLUSIVE", fail_exit=3)
        proc, _s = self._build("blind", blind, manifest)
        self.assertEqual(proc.returncode, 1)

    def test_stderr_from_a_lane_aborts_the_pack(self):
        manifest, _cases = self._fixtures("noisy")
        noisy = _write_python_exe("sv_noisy.py", (
            "import sys\n"
            "sys.stderr.write('warning' + chr(10))\n"
            "sys.stdout.write(%r + chr(10))\n"
            "sys.exit(3)\n" % (LINE % ("INCONCLUSIVE", "R"),)))
        proc, _s = self._build("noisy", noisy, manifest)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"emitted stderr", proc.stdout)

    def test_the_verdict_is_read_from_output_not_predicted(self):
        source = _load(PACK_TOOL)
        self.assertIn("def verdict_of", source)
        self.assertIn("def reason_of", source)
        self.assertNotIn('"FILE_HASH_MISMATCH"', source)
        self.assertNotIn('"RECEIPT_CHAIN_HASHES_RECOMPUTED"', source)

    def test_the_python_lane_is_genuinely_executed(self):
        manifest, cases = self._fixtures("pylane")
        clean = [c for c in cases if c["case_id"] == "clean"][0]
        proc = _run([PYTHON_BIN, "-B", COMPANION, "verify",
                     "--run", clean["root"]])
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertTrue(json.loads(proc.stdout)["verify_ok"])

    def test_relative_paths_are_refused(self):
        proc = _run([PYTHON_BIN, "-B", PACK_TOOL, "--verifier", "rel",
                     "--python-bin", "rel", "--companion", "rel",
                     "--fixtures", "rel", "--staging", "rel"])
        self.assertEqual(proc.returncode, 2)


class TestHistoricalValuesAreVerifiedNotAsserted(unittest.TestCase):
    """Correction 7."""

    def test_the_baseline_hash_is_recomputed_from_the_real_artifact(self):
        if not os.path.isfile(ADOPTED_M84_ZIP):
            self.skipTest("adopted Move 84 v07 archive not available here")
        with open(ADOPTED_M84_ZIP, "rb") as handle:
            self.assertEqual(hashlib.sha256(handle.read()).hexdigest(),
                             ADOPTED_M84_SHA)

    def test_the_inherited_file_count_is_counted_not_asserted(self):
        if not os.path.isfile(ADOPTED_M84_ZIP):
            self.skipTest("adopted Move 84 v07 archive not available here")
        with zipfile.ZipFile(ADOPTED_M84_ZIP) as archive:
            counted = len([i for i in archive.infolist() if not i.is_dir()])
        self.assertEqual(counted, 907)
        self.assertIn("907", _load(HANDOFF))

    def test_the_gate_takes_the_expected_hash_as_an_input(self):
        code = _load(GATE)
        self.assertIn("MOVE85_CANDIDATE_SHA256", code)
        self.assertIn("REAL_MOVE84", code)
        self.assertIn(ADOPTED_M84_SHA, code)

    def test_the_handoff_says_a_self_carried_hash_proves_nothing(self):
        text = _load(HANDOFF)
        self.assertIn("supplied to you **separately**", text)
        self.assertIn("proves nothing", text)


class TestHandoffScopeIsExplicitUpFront(unittest.TestCase):
    """Correction 8."""

    def _opening(self):
        return "\n".join(_load(HANDOFF).splitlines()[:24])

    def test_it_says_it_is_supplemental_to_the_block(self):
        self.assertIn("supplemental handoff for the Moves 71\u201385",
                      self._opening())

    def test_it_names_the_part_one_documents(self):
        opening = self._opening()
        for name in ("START_HERE.md", "README.md",
                     "CURRENT_RELEASE_STATE.md", "MOVE_INDEX.md"):
            self.assertIn(name, opening, name)

    def test_it_says_they_were_deliberately_not_rewritten(self):
        self.assertIn("deliberately not been rewritten", self._opening())

    def test_it_says_it_does_not_alter_their_historical_claims(self):
        self.assertIn("retroactively alter their historical claims",
                      self._opening())

    def test_those_documents_are_not_modified(self):
        data = json.loads(_load(ALLOWLIST))
        self.assertEqual(data["modified_paths"], [])


class TestNoBinaryIsShipped(unittest.TestCase):
    def test_the_handoff_states_no_executable_is_included(self):
        self.assertIn("No executable is included", _load(HANDOFF))

    def test_no_addition_is_an_executable(self):
        data = json.loads(_load(ALLOWLIST))
        for rel in data["added_paths"]:
            with open(os.path.join(ROOT, rel), "rb") as handle:
                self.assertNotEqual(handle.read(4), b"\x7fELF", rel)

    def test_the_claim_is_recorded_as_not_claimed(self):
        self.assertEqual(_claims()["binary_is_shipped"]["status"],
                         "not_claimed")


class TestPlatformClaimsAreHonest(unittest.TestCase):
    def test_only_android_termux_is_established(self):
        claims = _claims()
        self.assertEqual(claims["binary_target_android_termux_aarch64"]
                         ["status"],
                         "established_android_termux_aarch64_only")
        for name in ("platform_linux_x86_64", "platform_linux_aarch64",
                     "platform_windows_x86_64"):
            self.assertEqual(claims[name]["status"], "unestablished", name)

    def test_the_handoff_denies_the_generic_linux_equivalence(self):
        self.assertIn("not a generic Linux AArch64", _load(HANDOFF))

    def test_no_move85_material_claims_an_untested_platform(self):
        for path in (README, HANDOFF, FACTS):
            text = _load(path)
            for token in ("Linux x86_64", "Windows x86_64"):
                for match in re.finditer(re.escape(token), text):
                    window = text[max(0, match.start() - 160):
                                  match.end() + 160]
                    self.assertTrue(
                        re.search(r"unestablished|not|NOT", window),
                        "%s may claim %s" % (path, token))


class TestInheritedBaselineIsAdditiveOnly(unittest.TestCase):
    def test_allowlist_declares_no_modifications(self):
        data = json.loads(_load(ALLOWLIST))
        self.assertEqual(data["modified_paths"], [])
        self.assertEqual(data["added_paths"], sorted(data["added_paths"]))
        self.assertEqual(len(data["added_paths"]), 10)

    def test_every_declared_addition_exists(self):
        data = json.loads(_load(ALLOWLIST))
        for rel in data["added_paths"]:
            self.assertTrue(os.path.isfile(os.path.join(ROOT, rel)), rel)

    def test_no_addition_touches_rust_or_adopted_components(self):
        data = json.loads(_load(ALLOWLIST))
        for rel in data["added_paths"]:
            self.assertFalse(rel.startswith("rust/"), rel)
            self.assertFalse(rel.startswith("src/"), rel)
            self.assertFalse(rel.startswith("freeze_record/"), rel)


class TestSuitePortability(unittest.TestCase):
    _SH = "/bin" + "/sh"
    _ENV = "/usr" + "/bin" + "/env"
    _SHEBANG = "#" + "!"

    def _sources(self):
        for name in sorted(os.listdir(HERE)):
            if name.endswith(".py"):
                yield name, _load(os.path.join(HERE, name))

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
            self.assertEqual(path, os.path.realpath(path))

    def test_every_subprocess_is_bounded(self):
        for name, src in self._sources():
            for match in re.finditer(r"subprocess\.run\((.*?)\)\n", src,
                                     re.S):
                self.assertIn("timeout", match.group(1), name)


class TestGatePurposeAndPredecessorAreCorrect(unittest.TestCase):
    """v01 was rejected because the gate, derived from the Move 84 gate,
    still described itself as the tamper-and-detect demo gate, described
    its deliverable as a standalone executable, and named Move 83 v13 as
    the Move 85 baseline and child. The hashes bound correctly; the
    statements did not.

    Legitimate references are not touched: Move 85 genuinely depends on
    and regresses Move 84, and the handoff legitimately discusses Moves
    71-84. Only statements whose SUBJECT, AUTHORITY, BASELINE or PURPOSE
    would be wrong are forbidden."""

    ADOPTED_M84_GATE = os.path.join(
        ROOT, "tools", "check_move84_demo_adoption.sh")

    #: statements that would assign this move's baseline, child-gate or
    #: purpose to something other than Move 84 v07 / the audit pack
    STALE = (
        r"MOVE 8[0-4] TAMPER-AND-DETECT",
        r"MOVE 8[0-4] [A-Z-]* ?ADOPTION GATE\\.",
        r"adopted Move 8[0-3] v\d+ zip -- the SOLE",
        r"Move 8[0-3] v\d+ (?:zip|archive) -- the SOLE",
        r"baseline immutability \(candidate vs real adopted Move 8[0-3]",
        r"supplied Move 8[0-3] v\d+ zip sha256",
        r"the adopted Move 8[0-3] v\d+ baseline \+ allowlist",
        r"Move 8[0-3] v\d+ baseline verifier",
        r"complete adopted Move 8[0-3] v\d+ adoption/regression",
        r"Move 8[0-3] child (?:gate|zip|run|output|helper)",
        r"produces ONE target-specific standalone",
    )

    def _gate(self):
        return _load(GATE)

    def _lines(self):
        return self._gate().splitlines()

    # ---- the purpose and predecessor statements ---------------------

    def test_the_header_names_this_gate(self):
        head = " ".join(self._lines()[:4])
        self.assertIn("MOVE 85", head)
        self.assertIn("AUDIT-PACK", head)
        self.assertNotIn("TAMPER-AND-DETECT", head)

    def test_the_deliverable_is_the_audit_pack_not_a_binary(self):
        text = self._gate()
        self.assertIn("deliverable is the GENERATED AUDIT PACK", text)
        self.assertIn("NOT the Move 85 roadmap deliverable", text)
        self.assertNotIn("produces ONE target-specific standalone", text)

    def test_real_move84_is_documented_as_move84_v07(self):
        text = self._gate()
        self.assertIn("adopted Move 84 v07 zip -- the SOLE Move 85", text)
        self.assertNotIn("adopted Move 83 v13 zip -- the SOLE", text)

    def test_the_baseline_hash_pin_is_move84_v07(self):
        self.assertIn(ADOPTED_M84_SHA, self._gate())

    def test_stage_b_names_the_move84_baseline(self):
        self.assertIn("baseline immutability (candidate vs real adopted "
                      "Move 84 v07 zip)", self._gate())

    def test_stage_j_reruns_the_move84_child_gate(self):
        text = self._gate()
        self.assertIn("complete adopted Move 84 v07 adoption/regression "
                      "child gate", text)
        self.assertIn("check_move84_demo_adoption.sh", text)

    def test_the_regression_marker_documents_the_move84_child(self):
        self.assertIn("MOVE_84_REGRESSION_GATE: PASS   (the complete "
                      "adopted Move 84 v07", self._gate())

    # ---- the whole-file scan ----------------------------------------

    def test_no_line_assigns_a_stale_subject_or_purpose(self):
        patterns = [re.compile(p) for p in self.STALE]
        offenders = []
        for number, line in enumerate(self._lines(), 1):
            for pattern in patterns:
                if pattern.search(line):
                    offenders.append((number, line.strip()[:80]))
                    break
        self.assertEqual(offenders, [],
                         "stale subject/purpose statements: %s" % offenders)

    def test_the_scanner_catches_the_reported_stale_wording(self):
        """Mutation check on the reported examples."""
        patterns = [re.compile(p) for p in self.STALE]
        for defective in (
                "# MOVE 84 TAMPER-AND-DETECT DEMO ADOPTION GATE.",
                "#   REAL_MOVE84  adopted Move 83 v13 zip -- the SOLE "
                "Move 85 development baseline",
                "# Move 85 produces ONE target-specific standalone "
                "witness-verify executable",
                'echo "STAGE J: complete adopted Move 83 v13 '
                'adoption/regression child gate"'):
            self.assertTrue(any(p.search(defective) for p in patterns),
                            "scanner missed: %s" % defective)

    def test_the_scanner_leaves_legitimate_references_alone(self):
        patterns = [re.compile(p) for p in self.STALE]
        for genuine in (
                "# Move 83 v13 is supplied to that child as one of ITS "
                "dependencies",
                "# sanity checker are ADOPTED Move 83 files, inherited "
                "byte-identical",
                "The Move 84 tamper-and-detect demonstration lives in "
                "verify/demo_v01/.",
                'ok "Move 84 child gate PASS"'):
            self.assertFalse(any(p.search(genuine) for p in patterns),
                             "scanner false-positived: %s" % genuine)

    # ---- the child marker set, derived from the adopted Move 84 gate --

    def _emittable(self):
        src = _load(self.ADOPTED_M84_GATE)
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

    def _required(self):
        code = "\n".join(l for l in self._lines()
                          if not l.strip().startswith("#"))
        start = code.find("for _need in")
        end = code.find("done", start)
        return set(re.findall(r'"([A-Z_0-9]+): PASS"', code[start:end]))

    def test_every_required_marker_is_emittable_by_the_adopted_gate(self):
        not_emittable = sorted(self._required() - self._emittable())
        self.assertEqual(
            not_emittable, [],
            "markers the adopted Move 84 gate never emits: %s"
            % not_emittable)

    def test_the_child_terminal_marker_is_the_move84_gate(self):
        self.assertIn("MOVE_84_DEMO_ADOPTION_GATE", self._required())

    def test_the_inherited_move83_regression_marker_is_required(self):
        required = self._required()
        self.assertEqual({r for r in required if r.startswith("MOVE_83_")},
                         {"MOVE_83_REGRESSION_GATE"})

    def test_no_move83_stage_marker_is_demanded_of_the_child(self):
        """The Move 84 gate emits MOVE_84_* stage markers; demanding
        MOVE_83_* stage markers of it would reject a successful run."""
        for name in ("MOVE_83_CANDIDATE_IDENTITY",
                     "MOVE_83_CLEAN_RELEASE_BUILD",
                     "MOVE_83_PROVENANCE"):
            self.assertNotIn(name, self._required(), name)


class TestActiveCandidateIdentityIsCurrent(unittest.TestCase):
    """v02 shipped provenance naming MOVE_85_V01_TERMUX_GATE.txt: the
    single-sourced value was carried forward unchanged when the candidate
    was rebuilt, so the candidate could not be used for a first run.

    Historical references to superseded candidates are permitted ONLY
    where they are explicitly classified as historical."""

    ACTIVE_TRANSCRIPT = "MOVE_85_V08_TERMUX_GATE.txt"
    ACTIVE_CANDIDATE = "v08"
    SUPERSEDED = ("v01", "v02", "v03", "v04", "v05", "v06",
                  "v07")

    #: every Move 85 addition
    def _additions(self):
        data = json.loads(_load(ALLOWLIST))
        return [(rel, os.path.join(ROOT, rel))
                for rel in data["added_paths"]]

    def _gate_code(self):
        return "\n".join(l for l in _load(GATE).splitlines()
                          if not l.strip().startswith("#"))

    # ---- 1: the active identity matches the current candidate -------

    def test_the_active_transcript_identity_matches_current_candidate(self):
        code = self._gate_code()
        self.assertIn('MOVE85_TRANSCRIPT_NAME="%s"' % self.ACTIVE_TRANSCRIPT,
                      code)
        self.assertEqual(code.count(self.ACTIVE_TRANSCRIPT), 1,
                         "the transcript name must appear once in code")
        # derived from, and therefore agreeing with, the candidate version
        self.assertEqual(
            self.ACTIVE_TRANSCRIPT,
            "MOVE_85_V%s_TERMUX_GATE.txt" % self.ACTIVE_CANDIDATE[1:])

    def test_provenance_uses_the_variable_not_a_literal(self):
        self.assertIn('--transcript-name "$MOVE85_TRANSCRIPT_NAME"',
                      self._gate_code())

    # ---- 2: stale identities are rejected from ACTIVE code ----------

    def test_no_superseded_transcript_identity_in_active_gate_code(self):
        code = self._gate_code()
        for old in self.SUPERSEDED:
            stale = "MOVE_85_V%s_TERMUX_GATE.txt" % old[1:]
            self.assertNotIn(stale, code,
                             "stale transcript identity %s in active code"
                             % stale)

    def test_no_addition_carries_a_stale_active_candidate_identity(self):
        """Scan every Move 85 addition. A superseded identity is allowed
        only on a line that also classifies it as historical."""
        historical = re.compile(
            r"HISTORICAL|historical|REJECTED|rejected|audit history"
            r"|preserved unchanged|superseded|earlier candidate")
        stale = re.compile(
            r"MOVE_85_V0[1234567]_TERMUX_GATE\.txt"
            r"|project-witness-MOVE_85_candidate_v0[1234567]\.zip"
            r"|candidate_v0[1234567]\b"
            r"|CANDIDATE v0[1234567]\b")
        offenders = []
        for rel, path in self._additions():
            if rel.endswith(".txt"):
                continue
            # this module is excluded: its mutation fixtures are
            # deliberately stale strings, and a scanner that matched its
            # own probes would be checking itself rather than the
            # candidate.
            if os.path.abspath(path) == os.path.abspath(__file__):
                continue
            lines = _load(path).splitlines()
            for number, line in enumerate(lines, 1):
                # MOVE_84_candidate_v07 is the ADOPTED BASELINE's own
                # version, not a superseded Move 85 candidate
                if "MOVE_84" in line or "Move 84" in line:
                    continue
                if not stale.search(line):
                    continue
                # a stale token is permitted where the line, or the
                # comment block it sits in, classifies it as historical
                window = "\n".join(lines[max(0, number - 6):number])
                if not historical.search(window):
                    offenders.append((rel, number, line.strip()[:70]))
        self.assertEqual(offenders, [],
                         "stale active candidate identity: %s" % offenders)

    def test_the_stale_identity_scanner_catches_a_reported_defect(self):
        stale = re.compile(
            r"MOVE_85_V0[1234567]_TERMUX_GATE\.txt"
            r"|project-witness-MOVE_85_candidate_v0[1234567]\.zip"
            r"|candidate_v0[1234567]\b"
            r"|CANDIDATE v0[1234567]\b")
        for defective in (
                'MOVE85_TRANSCRIPT_NAME="MOVE_85_V01_TERMUX_GATE.txt"',
                "Status: CANDIDATE v02. Not adopted.",
                "project-witness-MOVE_85_candidate_v01.zip"):
            self.assertTrue(stale.search(defective),
                            "scanner missed: %s" % defective)

    # ---- 3: identity cannot drift from the packaged version ---------

    def _changelog_candidate(self):
        match = re.search(r"^Status: CANDIDATE (v\d+)", _load(CHANGELOG),
                          re.M)
        self.assertIsNotNone(match, "the changelog states no candidate")
        return match.group(1)

    def test_the_changelog_names_the_active_candidate(self):
        self.assertEqual(self._changelog_candidate(), self.ACTIVE_CANDIDATE)

    def test_the_transcript_identity_matches_the_candidate_version(self):
        """The provenance identity is derived from, and must agree with,
        the candidate version the changelog declares."""
        candidate = self._changelog_candidate()
        expected = "MOVE_85_V%s_TERMUX_GATE.txt" % candidate[1:]
        code = self._gate_code()
        self.assertIn('MOVE85_TRANSCRIPT_NAME="%s"' % expected, code,
                      "the provenance identity has drifted from the "
                      "candidate version %s" % candidate)

    # ---- 4: historical references remain permitted, when classified --

    def test_historical_candidate_references_are_classified(self):
        """The changelog legitimately records superseded candidates; each
        such mention must sit on a line that classifies it."""
        text = _load(CHANGELOG)
        historical = re.compile(
            r"HISTORICAL|historical|REJECTED|rejected|audit history"
            r"|preserved unchanged|superseded")
        unclassified = []
        for number, line in enumerate(text.splitlines(), 1):
            if re.search(r"candidate v0[1234567]\b|CANDIDATE v0[1234567]\b", line) \
                    and not historical.search(line):
                unclassified.append((number, line.strip()[:70]))
        self.assertEqual(unclassified, [],
                         "unclassified superseded-candidate reference: %s"
                         % unclassified)

    def test_superseded_identities_are_recorded_as_rejected(self):
        text = _load(CHANGELOG)
        for digest in (
                "5dd00c805333ee151099406c5b4cce61ea41e207d67a512892e0bed129d15bc2",
                "2fba2ccec5dd616aa68fc9f52d622da25cb1210b5b17562b4e61cf5ec5a0fe64",
                "a5ca84ddcdc9c5a42a13ce9fde21397f93b5d6f8104b2bf095f8f1ff5629d854",
                "3e4724a5f42a2a93b2363d23d473fc6425bebaae4b1f120e62b5730e7aad42d5",
                "516848157ad0e1a53ebc2c1a22a90b5a92a8c0f516cfcaecc665be6761bb1b19",
                "14b4b71ec0a6612d7c00522dfee2020b0a6599aa375ec919c852ed291585160f",
                "443c66e9b79b7958779ae6eed631b41cd920f15d96b307e2c6003e36dbbb0af2"):
            self.assertIn(digest, text)
        self.assertIn("REJECTED pre-Termux", text)


class TestMove84ChildInputContract(unittest.TestCase):
    """v03 omitted REAL_MOVE83 from the Move 84 child invocation. The
    adopted Move 84 gate requires it, so a genuine child would have
    terminated on its own usage contract before establishing anything.

    The contract is READ FROM THE ADOPTED MOVE 84 GATE, never assumed."""

    ADOPTED_M84_GATE = os.path.join(
        ROOT, "tools", "check_move84_demo_adoption.sh")
    ADOPTED_M83_SHA = \
        "aa06feb870ec3d72ff7c942fe8c0752efff313cbbdab6e280302dba288975a6c"

    def _child_required_inputs(self):
        """The adopted Move 84 gate's own mandatory inputs."""
        src = _load(self.ADOPTED_M84_GATE)
        return set(re.findall(r'_missing="\$_missing ([A-Z_0-9]+)"', src))

    def _code(self):
        return "\n".join(l for l in _load(GATE).splitlines()
                          if not l.strip().startswith("#"))

    # ---- the contract, derived from the child ----------------------

    def test_the_adopted_child_requires_real_move83(self):
        self.assertIn("REAL_MOVE83", self._child_required_inputs())

    def test_every_child_required_input_is_supplied(self):
        code = self._code()
        missing = []
        for name in sorted(self._child_required_inputs()):
            if name.startswith("MOVE84_"):
                if '%s=' % name not in code:
                    missing.append(name)
            elif '%s="$%s"' % (name, name) not in code:
                missing.append(name)
        self.assertEqual(missing, [],
                         "the Move 84 child is not given: %s" % missing)

    # ---- REAL_MOVE83 is mandatory for Move 85 ----------------------

    def test_real_move83_is_a_mandatory_move85_input(self):
        code = self._code()
        self.assertIn('[ -z "${REAL_MOVE83:-}" ]', code)
        self.assertIn('_missing REAL_MOVE83', code)

    def test_real_move83_obeys_the_absolute_path_rule(self):
        self.assertIn('"REAL_MOVE83=$REAL_MOVE83"', self._code())

    def test_omitting_real_move83_is_rejected_before_child_execution(self):
        code = self._code()
        requirement = code.find('_missing REAL_MOVE83')
        invocation = code.rfind("check_move84_demo_adoption.sh")
        self.assertNotEqual(requirement, -1)
        self.assertNotEqual(invocation, -1)
        self.assertLess(requirement, invocation)

    # ---- it is the adopted authority, and only a dependency ---------

    def test_real_move83_is_pinned_to_the_adopted_move83_v13(self):
        code = self._code()
        self.assertIn(self.ADOPTED_M83_SHA, code)
        self.assertIn('"$_M83_DEP_SHA" != "$_M83_DEP_EXPECT"', code)

    def test_real_move83_is_verified_before_the_child_runs(self):
        code = self._code()
        check = code.find("_M83_DEP_SHA=$(")
        # the INVOCATION, not the earlier pre-flight existence check
        invocation = code.rfind("check_move84_demo_adoption.sh")
        self.assertNotEqual(check, -1)
        self.assertNotEqual(invocation, -1)
        self.assertLess(check, invocation)

    def test_no_candidate_copy_can_substitute_for_real_move83(self):
        """The external authority may not live inside the candidate."""
        code = self._code()
        self.assertIn('"$ROOT"/*) bad "REAL_MOVE83 must be external', code)

    def test_the_move85_baseline_remains_real_move84(self):
        code = self._code()
        self.assertIn(ADOPTED_M84_SHA, code)
        self.assertIn("adopted Move 84 v07 zip -- the SOLE Move 85",
                      _load(GATE))

    def test_real_move83_is_documented_as_a_dependency_not_baseline(self):
        text = _load(GATE)
        self.assertIn("adopted Move 83 v13 zip (a DEPENDENCY the", text)
        self.assertIn("NOT the Move 85", text)

    def test_the_stage_j_contract_documentation_is_truthful(self):
        """The documented contract must list exactly what the adopted
        Move 84 gate requires."""
        text = _load(GATE)
        start = text.find("The adopted Move 84 gate has its OWN mandatory")
        self.assertNotEqual(start, -1)
        block = text[start:start + 600]
        for name in sorted(self._child_required_inputs()):
            self.assertIn(name, block,
                          "the documented contract omits %s" % name)


class TestStagingOwnershipContract(unittest.TestCase):
    """v04 failed its genuine Termux run here. The builder requires
    --staging to be an absolute, ALREADY-EXISTING root; the gate passed
    paths it never created. My off-device tests created the staging
    directory themselves, so they never exercised the gate's own
    behaviour -- the producer and the consumer had never actually met.

    The contract is now: the GATE owns creating each staging root; the
    builder keeps its fail-closed requirement and creates only its own
    audit_pack_v1/ child beneath it."""

    def _code(self):
        return "\n".join(l for l in _load(GATE).splitlines()
                          if not l.strip().startswith("#"))

    def _run_builder(self, staging, create=True):
        base = os.path.join(_TMP, "own_%s" % staging)
        if create:
            os.makedirs(base, exist_ok=True)
        return _run([PYTHON_BIN, "-B", PACK_TOOL,
                     "--verifier", PYTHON_BIN, "--python-bin", PYTHON_BIN,
                     "--companion", COMPANION,
                     "--fixtures", COMPANION,  # exists; parsed later
                     "--staging", base]), base

    # ---- 1-3: the builder's own contract, unchanged -----------------

    def test_missing_staging_argument_is_rejected(self):
        proc = _run([PYTHON_BIN, "-B", PACK_TOOL,
                     "--verifier", PYTHON_BIN, "--python-bin", PYTHON_BIN,
                     "--companion", COMPANION, "--fixtures", COMPANION])
        self.assertEqual(proc.returncode, 2)

    def test_relative_staging_path_is_rejected(self):
        proc = _run([PYTHON_BIN, "-B", PACK_TOOL,
                     "--verifier", PYTHON_BIN, "--python-bin", PYTHON_BIN,
                     "--companion", COMPANION, "--fixtures", COMPANION,
                     "--staging", "relative_dir"])
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"--staging", proc.stdout)

    def test_absolute_but_nonexistent_staging_is_rejected(self):
        """The exact v04 failure: the gate passed a path it had not
        created."""
        missing = os.path.join(_TMP, "never_created_staging")
        if os.path.isdir(missing):
            shutil.rmtree(missing)
        proc = _run([PYTHON_BIN, "-B", PACK_TOOL,
                     "--verifier", PYTHON_BIN, "--python-bin", PYTHON_BIN,
                     "--companion", COMPANION, "--fixtures", COMPANION,
                     "--staging", missing])
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"absolute existing path", proc.stdout)

    def test_existing_absolute_staging_is_accepted(self):
        """It gets past argument validation -- it fails later on the
        fixture manifest, which is a different check."""
        base = os.path.join(_TMP, "staging_ok")
        os.makedirs(base, exist_ok=True)
        proc = _run([PYTHON_BIN, "-B", PACK_TOOL,
                     "--verifier", PYTHON_BIN, "--python-bin", PYTHON_BIN,
                     "--companion", COMPANION, "--fixtures", COMPANION,
                     "--staging", base])
        self.assertNotEqual(proc.returncode, 2)

    def test_the_builder_still_fails_closed_on_staging(self):
        """The builder's own validation is unchanged: absolute AND
        already existing, refused with exit 2 otherwise."""
        source = _load(PACK_TOOL)
        self.assertIn("must be an absolute existing path", source)
        self.assertIn("not os.path.isabs(path) or not os.path.exists(path)",
                      source)
        self.assertIn('"--staging", args.staging', source)

    # ---- 4-6: the gate owns creation --------------------------------

    def test_the_gate_creates_pack_1_before_the_first_invocation(self):
        code = self._code()
        created = code.find('_ap_make_staging "$_AP_DIR/pack_1"')
        used = code.find('--staging "$_AP_DIR/pack_1"')
        self.assertNotEqual(created, -1, "pack_1 is never created")
        self.assertNotEqual(used, -1)
        self.assertLess(created, used)

    def test_the_gate_creates_pack_2_before_the_determinism_run(self):
        code = self._code()
        created = code.find('_ap_make_staging "$_AP_DIR/pack_2"')
        used = code.find('--staging "$_AP_DIR/pack_2"')
        self.assertNotEqual(created, -1, "pack_2 is never created")
        self.assertNotEqual(used, -1)
        self.assertLess(created, used)

    def test_every_staging_root_the_gate_passes_is_created_first(self):
        """Whole-file rule, so a third staging root cannot be added
        without being created."""
        code = self._code()
        used = re.findall(r'--staging "(\$_AP_DIR/[A-Za-z0-9_]+)"', code)
        self.assertTrue(used)
        for path in used:
            created = code.find('_ap_make_staging "%s"' % path)
            self.assertNotEqual(created, -1,
                                "%s is passed but never created" % path)
            self.assertLess(created, code.find('--staging "%s"' % path))

    def test_staging_roots_are_absolute_private_and_empty(self):
        code = self._code()
        self.assertIn("_ap_make_staging()", code)
        self.assertIn("staging root is not absolute", code)
        self.assertIn("staging root already exists", code)
        self.assertIn("staging root is not empty", code)
        self.assertIn("staging root is outside the gate-owned staging "
                      "area", code)

    def test_the_builder_does_not_create_the_supplied_root(self):
        """It may create its own audit_pack_v1/ child, not the parent."""
        source = _load(PACK_TOOL)
        self.assertNotIn("os.makedirs(args.staging", source)
        self.assertIn("os.makedirs(staging)", source)

    # ---- 7-8: determinism and publication ordering ------------------

    def test_the_determinism_comparison_is_still_required(self):
        code = self._code()
        self.assertIn("audit pack representation is not deterministic",
                      code)
        for name in ("MANIFEST.json", "INSTRUCTIONS.md",
                     "KNOWN_LIMITS.md", "SHA256SUMS"):
            self.assertIn(name, code, name)

    def test_publication_still_follows_the_substantive_checks(self):
        source = _load(PACK_TOOL)
        problems = source.find("problems = check_measurements")
        publish = source.find("if args.publish_to:")
        self.assertNotEqual(problems, -1)
        self.assertNotEqual(publish, -1)
        self.assertLess(problems, publish)
        self.assertIn("raise AuditPackError", source)


class TestAuditPackIsPublished(unittest.TestCase):
    """v05 could report the terminal PASS marker while the actual Move 85
    roadmap deliverable stayed in temporary staging and was discarded at
    cleanup. The gate published only the supporting binary and its
    provenance."""

    def _code(self):
        return "\n".join(l for l in _load(GATE).splitlines()
                          if not l.strip().startswith("#"))

    def _staged_pack(self, tag):
        """A small stand-in pack with a correct SHA256SUMS."""
        root = os.path.join(_TMP, "pub_%s" % tag, "audit_pack_v1")
        if os.path.isdir(root):
            shutil.rmtree(root)
        os.makedirs(os.path.join(root, "observed", "clean"))
        with open(os.path.join(root, "MANIFEST.json"), "wb") as handle:
            handle.write(b'{"schema_version":"witness-audit-pack/1"}\n')
        for name in ("INSTRUCTIONS.md", "KNOWN_LIMITS.md"):
            with open(os.path.join(root, name), "wb") as handle:
                handle.write(b"text\n")
        with open(os.path.join(root, "observed", "clean", "rust.stdout"),
                  "wb") as handle:
            handle.write(b"line\n")
        lines = []
        for dirpath, _dn, filenames in os.walk(root):
            for name in sorted(filenames):
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, root).replace(os.sep, "/")
                lines.append("%s  %s" % (packer.sha256_file(full), rel))
        lines.sort(key=lambda line: line.split("  ", 1)[1])
        with open(os.path.join(root, "SHA256SUMS"), "wb") as handle:
            handle.write(("\n".join(lines) + "\n").encode("utf-8"))
        return root

    def _publish(self, source, dest):
        os.makedirs(dest, exist_ok=True)
        return _run([PYTHON_BIN, "-B", PACK_TOOL,
                     "--publish-verified-from", source,
                     "--publish-to", dest])

    # ---- the gate publishes, and only after everything ---------------

    def test_the_gate_publishes_the_audit_pack(self):
        code = self._code()
        self.assertIn('--publish-verified-from "$_AP_DIR/pack_1/'
                      'audit_pack_v1"', code)
        self.assertIn('--publish-to "$OUT_DIR"', code)

    def test_publication_follows_every_substantive_check(self):
        code = self._code()
        publish = code.find("--publish-verified-from")
        for earlier in ('check_move85_inherited.py', 'cargo',
                        'MOVE_84_REGRESSION', 'audit_pack_tests.py',
                        'check_package_hygiene.sh'):
            position = code.find(earlier)
            self.assertNotEqual(position, -1, earlier)
            self.assertLess(position, publish,
                            "%s runs after publication" % earlier)

    def test_pack_2_is_never_published(self):
        code = self._code()
        self.assertEqual(code.count("--publish-verified-from"), 1)
        self.assertNotIn("pack_2/audit_pack_v1\"\n    --publish-to", code)
        publish_args = code[code.find("--publish-verified-from"):
                            code.find("--publish-to") + 40]
        self.assertNotIn("pack_2", publish_args)

    def test_nothing_is_regenerated_during_publication(self):
        """Publication copies the verified representation; it must not
        rebuild one."""
        code = self._code()
        block = code[code.find("STAGE P"):]
        self.assertNotIn("--verifier", block.split("ok \"audit pack "
                                                   "published")[0])

    # ---- the terminal marker is guarded ------------------------------

    def test_pass_is_unreachable_without_verified_publication(self):
        code = self._code()
        guard = code.find('"${AUDIT_PACK_PUBLISHED:-}" != "PASS"')
        terminal = code.find('MOVE_85_AUDIT_PACK_ADOPTION_GATE: PASS"')
        self.assertNotEqual(guard, -1, "the terminal marker is unguarded")
        self.assertLess(guard, terminal)

    def test_the_gate_cannot_pass_with_only_the_binary_present(self):
        code = self._code()
        self.assertIn('[ ! -d "$OUT_DIR/audit_pack_v1" ]', code)
        self.assertIn("the published audit pack is absent after "
                      "publication", code)

    def test_the_gate_verifies_the_published_tree_after_publication(self):
        code = self._code()
        self.assertIn("published SHA256SUMS does not verify against the "
                      "published bytes", code)
        self.assertIn("the published pack differs from the verified "
                      "staged pack_1", code)

    def test_a_preexisting_publication_target_is_rejected_by_the_gate(self):
        code = self._code()
        self.assertIn('[ -e "$OUT_DIR/audit_pack_v1" ]', code)

    # ---- the publisher itself, exercised for real -------------------

    def test_publication_produces_an_identical_tree(self):
        source = self._staged_pack("ok")
        dest = os.path.join(_TMP, "pubdest_ok")
        proc = self._publish(source, dest)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn(b"MOVE_85_AUDIT_PACK_PUBLICATION: PASS", proc.stdout)
        published = os.path.join(dest, "audit_pack_v1")
        for dirpath, _dn, filenames in os.walk(source):
            for name in filenames:
                a = os.path.join(dirpath, name)
                rel = os.path.relpath(a, source)
                b = os.path.join(published, rel)
                self.assertTrue(os.path.isfile(b), rel)
                with open(a, "rb") as fa, open(b, "rb") as fb:
                    self.assertEqual(fa.read(), fb.read(), rel)

    def test_a_preexisting_target_is_rejected_by_the_publisher(self):
        source = self._staged_pack("twice")
        dest = os.path.join(_TMP, "pubdest_twice")
        self.assertEqual(self._publish(source, dest).returncode, 0)
        proc = self._publish(source, dest)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"already exists", proc.stdout)

    def test_published_sha256sums_covers_and_verifies_the_pack(self):
        source = self._staged_pack("sums")
        dest = os.path.join(_TMP, "pubdest_sums")
        self.assertEqual(self._publish(source, dest).returncode, 0)
        published = os.path.join(dest, "audit_pack_v1")
        listed = {}
        with open(os.path.join(published, "SHA256SUMS"),
                  encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    digest, rel = line.rstrip("\n").split("  ", 1)
                    listed[rel] = digest
        on_disk = {}
        for dirpath, _dn, filenames in os.walk(published):
            for name in filenames:
                if name == "SHA256SUMS":
                    continue
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, published).replace(os.sep, "/")
                on_disk[rel] = packer.sha256_file(full)
        self.assertEqual(set(listed), set(on_disk))
        self.assertEqual(listed, on_disk)

    def test_a_corrupt_source_rolls_back_and_fails(self):
        source = self._staged_pack("bad")
        with open(os.path.join(source, "MANIFEST.json"), "ab") as handle:
            handle.write(b"tampered")
        dest = os.path.join(_TMP, "pubdest_bad")
        proc = self._publish(source, dest)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"rolled back", proc.stdout)
        self.assertFalse(os.path.exists(
            os.path.join(dest, "audit_pack_v1")))

    def test_publication_mode_refuses_relative_paths(self):
        proc = _run([PYTHON_BIN, "-B", PACK_TOOL,
                     "--publish-verified-from", "rel",
                     "--publish-to", "rel2"])
        self.assertEqual(proc.returncode, 2)

    # ---- documentation says which is the deliverable ----------------

    def test_the_docs_name_the_pack_as_the_deliverable(self):
        for path in (README, HANDOFF):
            text = _load(path)
            self.assertIn("roadmap deliverable", text)
        self.assertIn("supporting measurement", _load(HANDOFF))
        self.assertIn("the binary is not", _load(HANDOFF).lower())


class TestTerminalMarkerOrdering(unittest.TestCase):
    """v06 had no possible successful execution path: the guard

        if [ "${AUDIT_PACK_PUBLISHED:-}" != "PASS" ]; then ... die

    ran BEFORE the only assignment of that variable, which happened after
    Stage P. The terminal PASS marker was also emitted before publication.

    These tests read the gate as an ordered sequence of statements, so an
    unreachable or out-of-order success path fails off device."""

    def _lines(self):
        return _load(GATE).split("\n")

    def _line_of(self, needle, code_only=True):
        """1-based line number of the first matching STATEMENT."""
        for number, line in enumerate(self._lines(), 1):
            if needle in line:
                if code_only and line.strip().startswith("#"):
                    continue
                return number
        return -1

    def _order(self):
        return {
            "stage_p": self._line_of("STAGE P: publish"),
            "assignment": self._line_of("AUDIT_PACK_PUBLISHED=PASS"),
            "guard": self._line_of('"${AUDIT_PACK_PUBLISHED:-}"'),
            "terminal": self._line_of(
                'echo "MOVE_85_AUDIT_PACK_ADOPTION_GATE: PASS"'),
        }

    def test_every_ordering_anchor_exists(self):
        for name, line in self._order().items():
            self.assertNotEqual(line, -1, "missing anchor: %s" % name)

    def test_the_guard_cannot_run_before_the_assignment(self):
        """The exact v06 defect: an unreachable success path."""
        order = self._order()
        self.assertLess(order["assignment"], order["guard"],
                        "AUDIT_PACK_PUBLISHED is checked before it is "
                        "ever assigned; no successful path exists")

    def test_the_assignment_follows_stage_p(self):
        order = self._order()
        self.assertLess(order["stage_p"], order["assignment"])

    def test_the_assignment_follows_post_publication_verification(self):
        """It is set only after the published tree and its SHA256SUMS
        have been verified."""
        sums = self._line_of("published SHA256SUMS does not verify")
        tree = self._line_of("differs from the verified")
        assignment = self._order()["assignment"]
        for name, line in (("SHA256SUMS check", sums),
                           ("tree comparison", tree)):
            self.assertNotEqual(line, -1, name)
            self.assertLess(line, assignment,
                            "%s runs after the success assignment" % name)

    def test_the_terminal_marker_follows_publication(self):
        order = self._order()
        self.assertLess(order["stage_p"], order["terminal"],
                        "the terminal PASS marker is emitted before the "
                        "audit pack is published")
        self.assertLess(order["assignment"], order["terminal"])
        self.assertLess(order["guard"], order["terminal"])

    def test_no_adoption_success_marker_precedes_publication(self):
        """No line may announce adoption success before Stage P."""
        stage_p = self._order()["stage_p"]
        offenders = []
        for number, line in enumerate(self._lines(), 1):
            if number >= stage_p or line.strip().startswith("#"):
                continue
            if "ADOPTION_GATE: PASS" in line and "echo" in line:
                offenders.append((number, line.strip()[:70]))
        self.assertEqual(offenders, [],
                         "adoption success announced before publication: "
                         "%s" % offenders)

    def test_the_final_marker_block_follows_stage_p(self):
        stage_p = self._order()["stage_p"]
        markers = self._line_of('echo "MOVE_85_CANDIDATE_IDENTITY: $CANDIDATE_IDENTITY"')
        self.assertNotEqual(markers, -1)
        self.assertLess(stage_p, markers,
                        "the final-marker block precedes publication")

    def test_the_gate_exits_zero_only_after_the_terminal_marker(self):
        terminal = self._order()["terminal"]
        exits = [n for n, l in enumerate(self._lines(), 1)
                 if l.strip() == "exit 0"]
        self.assertTrue(exits)
        self.assertTrue(all(n > terminal for n in exits),
                        "an exit 0 precedes the terminal marker")

    # ---- failure paths cannot reach the terminal marker -------------

    def test_publication_failure_dies_before_the_terminal_marker(self):
        """Every publication failure path calls die, which exits 1."""
        lines = self._lines()
        stage_p = self._order()["stage_p"]
        terminal = self._order()["terminal"]
        region = lines[stage_p - 1:terminal - 1]
        text = "\n".join(region)
        for failure in ("audit pack publication failed",
                        "the published audit pack is absent after "
                        "publication",
                        "published SHA256SUMS does not verify against the "
                        "published bytes",
                        "the published pack differs from the verified "
                        "staged pack_1"):
            self.assertIn(failure, text, failure)
        # each of those is followed by a die
        self.assertGreaterEqual(text.count('die "publication"'), 4)

    def test_die_is_fail_closed(self):
        text = _load(GATE)
        self.assertIn('die(){', text)
        self.assertIn("exit 1", text)


class TestNoActiveIdentifierNamesASupersededCandidate(unittest.TestCase):
    """v07 shipped a test named `test_the_active_transcript_identity_is_v03`
    under a heading reading "the active identity is exactly v03". The test
    BODY checked the right value, so nothing failed functionally — but the
    name and heading asserted that a superseded candidate was current, and
    at Move 85 that would be frozen into adopted handoff evidence.

    Active identifiers are checked separately from active VALUES: a name
    can lie while the body tells the truth."""

    CURRENT = "v08"

    def _additions(self):
        data = json.loads(_load(ALLOWLIST))
        return [(rel, os.path.join(ROOT, rel))
                for rel in data["added_paths"]
                if not rel.endswith(".txt")]

    #: an ACTIVE identifier: a def or class name, or a comment that
    #: asserts current identity. Historical fixtures and Move 84's own
    #: version are not matched.
    def _offenders(self, path, current):
        offenders = []
        superseded = r"v0[1-9]"
        patterns = (
            re.compile(r"def\s+(\w*_%s\w*)\s*\(" % superseded),
            re.compile(r"class\s+(\w*V0[1-9]\w*)\s*[:(]"),
            re.compile(r"#[^\n]*\b(?:active|current)\b[^\n]*"
                       r"\b(v0[1-9])\b", re.I),
        )
        for number, line in enumerate(_load(path).splitlines(), 1):
            # a reference to MOVE 84's own version is not this move's
            if "move84" in line.lower() or "Move 84" in line:
                continue
            # historical fixtures are named as such
            if re.search(r"reported|historical|superseded|rejected|stale",
                         line, re.I):
                continue
            for pattern in patterns:
                match = pattern.search(line)
                if match and current not in match.group(0):
                    offenders.append((number, line.strip()[:78]))
                    break
        return offenders

    def test_no_active_identifier_names_a_superseded_candidate(self):
        found = []
        for rel, path in self._additions():
            # this module is excluded: its probe fixtures are deliberately
            # stale identifier strings, and a scanner matching its own
            # probes would be checking itself rather than the candidate.
            if os.path.abspath(path) == os.path.abspath(__file__):
                continue
            for number, line in self._offenders(path, self.CURRENT):
                found.append((rel, number, line))
        self.assertEqual(found, [],
                         "active identifiers name a superseded candidate: "
                         "%s" % found)

    def test_this_module_has_no_stale_active_identifier(self):
        """The suite's own def and class names are checked here, with
        quoted probe fixtures excluded."""
        offenders = []
        for number, line in enumerate(_load(__file__).splitlines(), 1):
            stripped = line.strip()
            # probe fixtures are quoted string literals, not definitions
            if stripped.startswith('"') or stripped.startswith("'"):
                continue
            if "move84" in line.lower() or "Move 84" in line:
                continue
            if re.search(r"reported|historical|superseded|rejected|stale",
                         line, re.I):
                continue
            match = re.search(r"def\s+(\w*_v0[1-9]\w*)\s*\(|"
                              r"class\s+(\w*V0[1-9]\w*)\s*[:(]", line)
            if match and self.CURRENT not in match.group(0):
                offenders.append((number, stripped[:78]))
        self.assertEqual(offenders, [],
                         "this module names a superseded candidate: %s"
                         % offenders)

    def test_the_identifier_scanner_catches_the_reported_defect(self):
        """The exact v07 wording must be flagged."""
        probe = os.path.join(_TMP, "identifier_probe.py")
        with open(probe, "w", encoding="utf-8") as handle:
            handle.write(
                "    # ---- 1: the active identity is exactly v03 ----\n"
                "    def test_the_active_transcript_identity_is_v03(s):\n"
                "        pass\n")
        self.assertTrue(self._offenders(probe, self.CURRENT),
                        "the scanner missed the reported v07 defect")

    def test_the_scanner_leaves_legitimate_names_alone(self):
        probe = os.path.join(_TMP, "identifier_ok.py")
        with open(probe, "w", encoding="utf-8") as handle:
            handle.write(
                "    def test_the_baseline_hash_pin_is_move84_v07(s):\n"
                "        pass\n"
                "    def test_the_scanner_catches_the_reported_wording(s):\n"
                "        pass\n"
                "    # historical: candidate v02 shipped a stale value\n")
        self.assertEqual(self._offenders(probe, self.CURRENT), [])

    def test_the_active_constants_agree_with_each_other(self):
        """The constants the suite treats as current must be internally
        consistent and match the changelog."""
        import audit_pack_tests as module
        active = module.TestActiveCandidateIdentityIsCurrent
        self.assertEqual(active.ACTIVE_CANDIDATE, self.CURRENT)
        self.assertEqual(
            active.ACTIVE_TRANSCRIPT,
            "MOVE_85_V%s_TERMUX_GATE.txt" % self.CURRENT[1:])
        match = re.search(r"^Status: CANDIDATE (v\d+)", _load(CHANGELOG),
                          re.M)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), self.CURRENT)


if __name__ == "__main__":
    _suite = unittest.defaultTestLoader.loadTestsFromModule(
        sys.modules[__name__])
    _result = unittest.TextTestRunner(
        stream=sys.stdout, verbosity=1).run(_suite)
    sys.exit(0 if _result.wasSuccessful() else 1)
