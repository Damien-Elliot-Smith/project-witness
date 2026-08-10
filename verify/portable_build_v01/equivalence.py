#!/usr/bin/env python3
"""Move 82 debug/release behavioural equivalence and standalone proof.

Two jobs, both about OBSERVABLE BEHAVIOUR only. Binary bytes are never
compared: separate builds are not claimed to be byte-reproducible, so a
hash comparison would be a false requirement.

1. Equivalence. Run the freshly built release binary and the freshly built
   debug binary over the same controlled cases and require, per case,
   identical exit code, byte-identical stdout and byte-identical stderr.
   Any mismatch is reported and fails; it is never repaired or
   reinterpreted here.

2. Standalone proof. Execute the release binary from a private directory
   OUTSIDE the candidate source tree, by absolute path, with an empty
   PATH and private HOME and TMPDIR, with only the controlled input
   copied in beside it. No Cargo, rustc, Python, shell script or Rust
   source is placed in that directory, and no source-relative path is
   used. The surrounding harness is trusted Python; the point is that the
   BINARY INVOCATION does not require it.

The adopted CLI grammar is used exactly as it is. No `--version` flag or
any other new CLI behaviour is introduced: the emitted version and the
usage behaviour are established through the existing invocations.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys


RUN_TIMEOUT_SECONDS = 300


class EquivalenceError(Exception):
    """Deterministic, message-only failure."""


def _require_abs_exec(path, what):
    if not path or not os.path.isabs(path):
        raise EquivalenceError("%s must be an absolute path" % what)
    if not os.path.isfile(path):
        raise EquivalenceError("%s is not a regular file" % what)
    if not os.access(path, os.X_OK):
        raise EquivalenceError("%s is not executable" % what)
    return path


def run_binary(binary, args, cwd, env=None, timeout=RUN_TIMEOUT_SECONDS):
    """Invoke the binary by absolute path. Returns (rc, stdout, stderr)."""
    argv = [binary] + list(args)
    try:
        proc = subprocess.run(argv, cwd=cwd, capture_output=True,
                              env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise EquivalenceError("binary invocation timed out")
    except OSError:
        raise EquivalenceError("binary could not be launched")
    return proc.returncode, proc.stdout, proc.stderr


def standalone_env(home, tmp):
    """An environment with an EMPTY PATH and private HOME/TMPDIR. Nothing
    can be resolved through PATH from inside this environment."""
    return {"PATH": "", "HOME": home, "TMPDIR": tmp}


def compare_case(release_bin, debug_bin, args, cwd, env=None):
    """One controlled case run through both profiles."""
    r_rc, r_out, r_err = run_binary(release_bin, args, cwd, env)
    d_rc, d_out, d_err = run_binary(debug_bin, args, cwd, env)
    problems = []
    if r_rc != d_rc:
        problems.append("exit code differs: release=%d debug=%d"
                        % (r_rc, d_rc))
    if r_out != d_out:
        problems.append("stdout differs")
    if r_err != d_err:
        problems.append("stderr differs")
    return {
        "args": list(args),
        "exit_code": r_rc,
        "stdout_bytes": len(r_out),
        "stderr_bytes": len(r_err),
        "problems": problems,
    }, r_out, r_err


def require_empty_stderr(stderr, label):
    """Non-usage invocations must produce completely empty stderr."""
    if stderr:
        raise EquivalenceError("%s emitted stderr" % label)


def standalone_proof(release_bin, workdir, input_path, args):
    """Copy the binary and only the controlled input into a private
    directory outside the source tree, then execute by absolute path with
    an empty PATH and private HOME/TMPDIR."""
    os.makedirs(workdir, exist_ok=True)
    home = os.path.join(workdir, "home")
    tmp = os.path.join(workdir, "tmp")
    bindir = os.path.join(workdir, "run")
    for path in (home, tmp, bindir):
        os.makedirs(path, exist_ok=True)

    staged_bin = os.path.join(bindir, "witness-verify")
    shutil.copyfile(release_bin, staged_bin)
    os.chmod(staged_bin, 0o755)

    staged_input = None
    if input_path is not None:
        base = os.path.basename(input_path.rstrip(os.sep))
        staged_input = os.path.join(bindir, base)
        if os.path.isdir(input_path):
            shutil.copytree(input_path, staged_input)
        else:
            shutil.copyfile(input_path, staged_input)

    # nothing that could satisfy a toolchain dependency may be present
    present = set(os.listdir(bindir))
    forbidden = {"cargo", "rustc", "python3", "python", "sh", "Cargo.toml",
                 "src", "rust"}
    intruders = sorted(present & forbidden)
    if intruders:
        raise EquivalenceError(
            "standalone directory contains toolchain material: %s"
            % ", ".join(intruders))

    env = standalone_env(home, tmp)
    call_args = [a if a != "@INPUT@" else staged_input for a in args]
    rc, out, err = run_binary(staged_bin, call_args, cwd=bindir, env=env)
    return rc, out, err, staged_bin


def parse_verifier_stdout(stdout):
    """The adopted verifier emits exactly one JSON object and one trailing
    newline. Anything else is a framing failure, not a verdict."""
    try:
        text = stdout.decode("utf-8")
    except UnicodeDecodeError:
        raise EquivalenceError("verifier stdout is not UTF-8")
    if text == "" or text[0] != "{":
        raise EquivalenceError("verifier stdout is not a single JSON object")
    if not text.endswith("\n") or text.endswith("\n\n"):
        raise EquivalenceError(
            "verifier stdout does not end with exactly one newline")
    if text.count("\n") != 1:
        raise EquivalenceError("verifier stdout is not exactly one line")
    try:
        return json.loads(text)
    except ValueError:
        raise EquivalenceError("verifier stdout is not valid JSON")


ADOPTED_VERIFIER = "witness-verify"
ADOPTED_VERSION = "0.0.8-step79-diagnostics"

# The exact field set the adopted verifier emits. Anything more or less is a
# framing failure: checking only verdict/reason_code/exit would accept a
# record with a wrong version, a wrong stage or an extra field.
BASE_RECORD_FIELDS = frozenset(
    ("verifier", "version", "verdict", "reason_code", "detail"))
ARCHIVE_EXTRA_FIELDS = frozenset(("entry_count",))


def verify_corpus_pins(harness_dir):
    """Verify the adopted corpus files against corpus_lock.json before any
    fixture is generated from them. Building fixtures from an unverified
    generator would make every downstream comparison meaningless."""
    import hashlib
    lock_path = os.path.join(harness_dir, "corpus_lock.json")
    if not os.path.isfile(lock_path):
        raise EquivalenceError("corpus_lock.json is missing")
    with open(lock_path, encoding="utf-8") as handle:
        lock = json.load(handle)
    problems = []
    for rel, want in sorted(lock.get("file_pins", {}).items()):
        target = os.path.join(harness_dir, rel)
        if not os.path.isfile(target):
            problems.append("pinned corpus file missing: %s" % rel)
            continue
        with open(target, "rb") as handle:
            got = hashlib.sha256(handle.read()).hexdigest()
        if got != want:
            problems.append("pinned corpus file changed: %s" % rel)
    if problems:
        raise EquivalenceError("; ".join(problems))
    return lock


def build_archive_fixtures(corpus_dir, outdir, lock):
    """Build every adopted archive fixture with the ADOPTED builder, then
    require the set to cover exactly the fixtures the lock declares."""
    import importlib.util
    os.makedirs(outdir, exist_ok=True)
    builder_path = os.path.join(corpus_dir, "build_archives.py")
    spec = importlib.util.spec_from_file_location(
        "adopted_build_archives", builder_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    archives = module.build_all()
    # The lock's required set also names three cases whose input is a REAL
    # adopted artifact supplied to the gate (real_705, real_move78,
    # real_v20) rather than something the builder synthesises. Those are
    # provided separately; everything else must come from the adopted
    # builder.
    required = set(lock.get("required_archive_fixtures", []))
    missing = sorted(required - set(archives) - EXTERNAL_ARCHIVE_CASES)
    if missing:
        raise EquivalenceError(
            "adopted builder did not produce required fixtures: %s"
            % ", ".join(missing))
    written = {}
    for name in sorted(archives):
        path = os.path.join(outdir, name + ".zip")
        with open(path, "wb") as handle:
            handle.write(archives[name])
        written[name] = path
    return written


EXTERNAL_ARCHIVE_CASES = frozenset(
    ("real_705", "real_move78", "real_v20"))

# The three adopted archive cases whose input is a REAL artifact. Their
# hashes are pinned: Move 79 must never be substituted for real_v20, and a
# wrong artifact must fail BEFORE any verifier is executed.
EXTERNAL_ARCHIVE_SHA256 = {
    "real_v20":
        "1248bc46fa555cc50ed7b63c9284baffd1e95a6972cdfbc4a40a0201fea81aba",
    "real_705":
        "72e38ffd8338a978bf5d59d2fc9f0f06847092eab5f6a828077adef709c0f348",
    "real_move78":
        "6030148c2c1bb373ad69393563e8e2e3078dff93e9f446d728edd18ea3c45252",
}


def _sha256_path(path):
    import hashlib
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def load_archive_cases(archive_cases_path, archives, external=None):
    """Every adopted archive case whose Rust lane is in scope."""
    with open(archive_cases_path, encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("lane") != "archive":
        raise EquivalenceError("archive corpus lane is not 'archive'")
    cases = []
    for case in data["cases"]:
        if case.get("rust_scope") != "in_scope":
            continue
        case_id = case["case_id"]
        archive_file = case.get("archive_file")
        if archive_file is None:
            # a REAL adopted artifact supplied to the gate as an input
            path = (external or {}).get(case_id)
            if path is None:
                raise EquivalenceError(
                    "adopted archive case %s needs a real supplied "
                    "artifact and none was provided" % case_id)
            want = case.get("expected_sha256") \
                or EXTERNAL_ARCHIVE_SHA256.get(case_id)
            if want is None:
                raise EquivalenceError(
                    "no pinned hash for external archive case %s" % case_id)
            if not os.path.isfile(path):
                raise EquivalenceError(
                    "supplied artifact for %s is not a regular file"
                    % case_id)
            got = _sha256_path(path)
            if got != want:
                raise EquivalenceError(
                    "supplied artifact for %s has sha256 %s; the adopted "
                    "case requires %s (a different adopted archive must "
                    "never be substituted)" % (case_id, got, want))
            expected_sha = want
        else:
            stem = archive_file
            if stem.endswith(".zip"):
                stem = stem[: -len(".zip")]
            if stem not in archives:
                raise EquivalenceError(
                    "adopted archive case %s has no built fixture (%s)"
                    % (case_id, stem))
            path = archives[stem]
            expected_sha = None
        # The adopted entry_count is a SIBLING of expected.rust, so
        # taking the nested object alone silently discarded it and left the
        # checker unable to require the adopted count.
        expectation = dict(case["expected"]["rust"])
        if "entry_count" in case["expected"]:
            expectation["entry_count"] = case["expected"]["entry_count"]
        cases.append({
            "case_id": case_id,
            "argv": ["inspect-archive", path],
            "expected": expectation,
            "expected_kind": "reason_class",
            "expected_sha256": expected_sha,
            "path": path,
        })
    return cases


def load_reason_map(reason_map_path):
    with open(reason_map_path, encoding="utf-8") as handle:
        return json.load(handle)


def resolve_reason_class(reason_map, lane, raw_reason):
    """Map a RAW emitted reason_code to its adopted class. Archive
    expectations are expressed as classes, so comparing a raw code against
    a class would be comparing two different vocabularies."""
    import re as _re
    entries = reason_map.get(lane, [])
    for entry in entries:
        if entry.get("match_type") == "exact" \
                and entry.get("value") == raw_reason:
            return entry.get("class"), entry.get("stage")
    for entry in entries:
        if entry.get("match_type") == "regex":
            try:
                if _re.search(entry["value"], raw_reason):
                    return entry.get("class"), entry.get("stage")
            except _re.error:
                continue
    return None, None


def check_edge_contract(stdout, stderr, rc, fixture, reason_map, label):
    """Enforce the FULL frozen edge contract for one fixture.

    Recording an expected verdict and exit code without enforcing them let
    a stand-in emitting PASS/0 through, as long as its reason happened to
    map to the right stage. Every declared field is now compared
    independently, so release and debug agreeing on the same false result
    cannot pass."""
    problems = []
    if stderr:
        problems.append("%s produced stderr (%d bytes)"
                        % (label, len(stderr)))
    try:
        obj = parse_verifier_stdout(stdout)
    except EquivalenceError as exc:
        problems.append("%s: %s" % (label, exc))
        return problems

    if obj.get("verifier") != ADOPTED_VERIFIER:
        problems.append("%s verifier is %r, adopted identity is %r"
                        % (label, obj.get("verifier"), ADOPTED_VERIFIER))
    if obj.get("version") != ADOPTED_VERSION:
        problems.append("%s version is %r, adopted version is %r"
                        % (label, obj.get("version"), ADOPTED_VERSION))

    want_verdict = fixture.get("expect_verdict")
    if want_verdict is not None and obj.get("verdict") != want_verdict:
        problems.append(
            "%s verdict is %r, the fixture contract requires %r"
            % (label, obj.get("verdict"), want_verdict))
    want_exit = fixture.get("expect_exit_code")
    if want_exit is not None and rc != want_exit:
        problems.append(
            "%s exit code is %r, the fixture contract requires %r"
            % (label, rc, want_exit))

    raw = obj.get("reason_code")
    want_raw = fixture.get("expect_reason_code")
    if want_raw is not None and raw != want_raw:
        problems.append(
            "%s raw reason_code is %r, the fixture contract requires %r"
            % (label, raw, want_raw))

    lane = "archive" if fixture.get("kind") == "archive" else "rust_bundle"
    got_class, got_stage = resolve_reason_class(reason_map, lane, raw or "")
    if got_class is None:
        problems.append(
            "%s reason %r is not in the adopted reason map" % (label, raw))
        return problems
    want_class = fixture.get("expect_reason_class")
    if want_class is not None and got_class != want_class:
        problems.append(
            "%s reason class is %r, the fixture contract requires %r"
            % (label, got_class, want_class))
    want_stage = fixture.get("expect_stage")
    if want_stage is not None and got_stage != want_stage:
        problems.append(
            "%s was answered at stage %r; the fixture contract requires "
            "%r, so the targeted %s arithmetic was not reached"
            % (label, got_stage, want_stage, fixture.get("surface")))
    return problems


def check_exact_record(stdout, stderr, rc, expected, label, reason_map=None,
                       expect_kind="reason_code", allow_entry_count=False):
    """Assert the EXACT record, not three selected fields.

    Requires the adopted verifier identity and version, the exact field
    set (no extra and no missing fields), the expected verdict, the
    expected reason (raw code or adopted class depending on the corpus),
    the exact exit code, and zero stderr bytes."""
    problems = []
    if stderr:
        problems.append(
            "%s produced stderr (%d bytes); the adopted contract requires "
            "zero stderr bytes" % (label, len(stderr)))
    try:
        obj = parse_verifier_stdout(stdout)
    except EquivalenceError as exc:
        problems.append("%s: %s" % (label, exc))
        return problems

    if obj.get("verifier") != ADOPTED_VERIFIER:
        problems.append("%s verifier is %r, adopted identity is %r"
                        % (label, obj.get("verifier"), ADOPTED_VERIFIER))
    if obj.get("version") != ADOPTED_VERSION:
        problems.append("%s version is %r, adopted version is %r"
                        % (label, obj.get("version"), ADOPTED_VERSION))

    allowed = set(BASE_RECORD_FIELDS)
    # BLOCKER 5: entry_count is part of the ACCEPTED archive record only.
    # The adopted verifier emits it from verdict_line_with_count on an
    # accepted archive and from verdict_line otherwise, so permitting it
    # broadly let an invented count ride along on a FAIL record.
    entry_count_expected = (allow_entry_count
                            and expected.get("verdict") == "INCONCLUSIVE")
    if entry_count_expected:
        allowed |= set(ARCHIVE_EXTRA_FIELDS)
        # An ACCEPTED archive reports how many entries it inspected. That
        # count is part of the adopted record, not an optional extra, so a
        # missing, non-integer or wrong count must fail even when the
        # reason class is right.
        got_count = obj.get("entry_count")
        if "entry_count" not in obj:
            problems.append(
                "%s is an accepted archive but reports no entry_count"
                % label)
        elif isinstance(got_count, bool) \
                or not isinstance(got_count, int):
            problems.append(
                "%s entry_count is not an integer: %r"
                % (label, got_count))
        elif expected.get("entry_count") is None:
            problems.append(
                "%s is an accepted archive but the adopted corpus "
                "declares no entry_count to compare against" % label)
        elif got_count != expected["entry_count"]:
            problems.append(
                "%s entry_count is %r, adopted expectation is %r"
                % (label, got_count, expected["entry_count"]))
    elif "entry_count" in obj:
        problems.append(
            "%s carries entry_count, which is not part of this record "
            "contract (verdict %r)" % (label, expected.get("verdict")))
    present = set(obj)
    extra = sorted(present - allowed)
    if extra:
        problems.append("%s has unexpected field(s): %s"
                        % (label, ", ".join(extra)))
    missing = sorted(BASE_RECORD_FIELDS - present)
    if missing:
        problems.append("%s is missing field(s): %s"
                        % (label, ", ".join(missing)))

    want_verdict = expected.get("verdict")
    if want_verdict is not None and obj.get("verdict") != want_verdict:
        problems.append("%s verdict is %r, adopted expectation is %r"
                        % (label, obj.get("verdict"), want_verdict))

    if expect_kind == "reason_code":
        want = expected.get("reason_code")
        if want is not None and obj.get("reason_code") != want:
            problems.append("%s reason_code is %r, adopted expectation is %r"
                            % (label, obj.get("reason_code"), want))
    else:
        want_class = expected.get("reason_class")
        want_stage = expected.get("stage")
        raw = obj.get("reason_code")
        got_class, got_stage = resolve_reason_class(
            reason_map or {}, "archive", raw or "")
        if got_class is None:
            problems.append(
                "%s reason_code %r is not in the adopted reason map"
                % (label, raw))
        else:
            if want_class is not None and got_class != want_class:
                problems.append(
                    "%s reason class is %r, adopted expectation is %r"
                    % (label, got_class, want_class))
            if want_stage is not None and got_stage != want_stage:
                problems.append(
                    "%s stage is %r, adopted expectation is %r"
                    % (label, got_stage, want_stage))

    want_exit = expected.get("exit_code")
    if want_exit is not None and rc != want_exit:
        problems.append("%s exit code is %r, adopted expectation is %r"
                        % (label, rc, want_exit))
    return problems


def check_against_expectation(stdout, stderr, rc, expected, label):
    """Assert the ADOPTED expectation, not merely internal consistency.

    Correctness is never derived from two newly built binaries agreeing:
    each profile is checked against the adopted expected verdict, reason
    code and exit code first."""
    problems = []
    if stderr:
        problems.append(
            "%s produced stderr (%d bytes); the adopted contract requires "
            "zero stderr bytes" % (label, len(stderr)))
    try:
        obj = parse_verifier_stdout(stdout)
    except EquivalenceError as exc:
        problems.append("%s: %s" % (label, exc))
        return problems
    for field, key in (("verdict", "verdict"),
                       ("reason_code", "reason_code")):
        want = expected.get(key)
        if want is None:
            continue
        got = obj.get(field)
        if got != want:
            problems.append("%s %s is %r, adopted expectation is %r"
                            % (label, field, got, want))
    want_exit = expected.get("exit_code")
    if want_exit is not None and rc != want_exit:
        problems.append("%s exit code is %r, adopted expectation is %r"
                        % (label, rc, want_exit))
    return problems


def load_controlled_cases(expected_results, fixture_manifest, fixtures_dir):
    """Build the controlled case list from the ADOPTED authorities."""
    with open(expected_results, encoding="utf-8") as handle:
        expected = json.load(handle)["cases"]
    with open(fixture_manifest, encoding="utf-8") as handle:
        fixtures = json.load(handle)["fixtures"]
    cases = []
    for case_id in sorted(expected):
        if case_id not in fixtures:
            raise EquivalenceError(
                "adopted expectation %s has no fixture entry" % case_id)
        entry = fixtures[case_id]
        filename = entry.get("filename")
        kind = entry.get("kind")
        if not filename or kind not in ("dir", "zip"):
            raise EquivalenceError(
                "adopted fixture entry %s is malformed" % case_id)
        path = os.path.join(fixtures_dir, filename)
        subcommand = "verify" if kind == "dir" else "inspect-archive"
        cases.append({
            "case_id": case_id,
            "argv": [subcommand, path],
            "expected": expected[case_id].get("rust_expected", {}),
            "path": path,
        })
    return cases


USAGE_CASES = (
    {"case_id": "USAGE-NO-ARGUMENTS", "argv": []},
    {"case_id": "USAGE-UNKNOWN-COMMAND", "argv": ["not-a-command"]},
    {"case_id": "USAGE-WRONG-ARG-COUNT", "argv": ["verify"]},
)


def pin_edge_contract(baseline_bin, fixtures, reason_map):
    """Establish each edge fixture's contract from the ADOPTED BASELINE
    verifier: verdict, process exit code, raw reason code, reason class
    and stage.

    Nothing is asserted against a hand-written expectation. v06 declared
    edge_control.zip as INCONCLUSIVE/3 by assumption and the genuine
    adopted verifier answered FAIL/1, so the gate failed on device for a
    contradiction I had invented rather than any defect in the verifier.
    The adopted implementation is the only authority for what a hostile
    input produces; the design intent recorded by the generator is kept as
    evidence and never enforced as an expectation."""
    problems = []
    pinned = []
    for fixture in fixtures:
        name = os.path.basename(fixture["path"])
        sub = ("inspect-archive" if fixture["kind"] == "archive"
               else "verify")
        rc, out, err = run_binary(baseline_bin, [sub, fixture["path"]],
                                  None)
        if err:
            problems.append("baseline emitted stderr on edge %s" % name)
            continue
        try:
            obj = parse_verifier_stdout(out)
        except EquivalenceError as exc:
            problems.append("baseline output for edge %s: %s"
                            % (name, exc))
            continue
        if obj.get("verifier") != ADOPTED_VERIFIER \
                or obj.get("version") != ADOPTED_VERSION:
            problems.append(
                "baseline identity or version wrong on edge %s" % name)
            continue
        verdict = obj.get("verdict")
        if verdict not in ("FAIL", "INCONCLUSIVE"):
            problems.append(
                "baseline produced verdict %r on edge %s; the adopted "
                "verifier has no other reachable verdict"
                % (verdict, name))
            continue
        raw = obj.get("reason_code")
        lane = ("archive" if fixture["kind"] == "archive"
                else "rust_bundle")
        got_class, got_stage = resolve_reason_class(reason_map, lane,
                                                    raw or "")
        if got_class is None:
            problems.append(
                "baseline reason %r on edge %s is not in the adopted map"
                % (raw, name))
            continue
        entry = dict(fixture)
        entry["expect_verdict"] = verdict
        entry["expect_exit_code"] = rc
        entry["expect_reason_code"] = raw
        entry["expect_reason_class"] = got_class
        entry["expect_stage"] = got_stage
        entry["baseline_stdout_sha256"] = _sha256_bytes(out)
        pinned.append(entry)
    return problems, pinned


def _sha256_bytes(data):
    import hashlib
    return hashlib.sha256(data).hexdigest()


def run_usage_contract(release_bin, debug_bin, baseline_bin,
                       standalone_dir=None):
    """The adopted USAGE behaviour, executed rather than assumed.

    Usage results are not verification verdicts, so they are not checked
    against the verdict corpora. What must hold is that both candidate
    profiles reproduce the adopted baseline's usage bytes and exit code
    exactly -- and that the staged standalone binary does too."""
    problems = []
    checked = 0
    for case in USAGE_CASES:
        label = case["case_id"]
        r_rc, r_out, r_err = run_binary(release_bin, case["argv"], None)
        d_rc, d_out, d_err = run_binary(debug_bin, case["argv"], None)
        if (d_rc, d_out, d_err) != (r_rc, r_out, r_err):
            problems.append("candidate profiles diverge on %s" % label)
        if baseline_bin is not None:
            b_rc, b_out, b_err = run_binary(baseline_bin, case["argv"],
                                            None)
            if (r_rc, r_out, r_err) != (b_rc, b_out, b_err):
                problems.append(
                    "release usage differs from the adopted baseline on %s"
                    % label)
            if (d_rc, d_out, d_err) != (b_rc, b_out, b_err):
                problems.append(
                    "debug usage differs from the adopted baseline on %s"
                    % label)
        if standalone_dir is not None:
            s_rc, s_out, s_err, _ = standalone_proof(
                release_bin, os.path.join(standalone_dir, label), None,
                case["argv"])
            if (s_rc, s_out, s_err) != (r_rc, r_out, r_err):
                problems.append(
                    "staged standalone usage differs from the in-tree run "
                    "on %s" % label)
        checked += 1
    return problems, checked


def run_full_corpus(release_bin, debug_bin, baseline_bin, cases,
                    reason_map, standalone_dir=None):
    """Run every adopted case through candidate release, candidate debug
    and the adopted BASELINE authority.

    Three independent requirements, all of which must hold:

      1. each candidate profile matches the adopted SEMANTIC expectation
         (verdict, reason, stage, exit) from the frozen corpora;
      2. each candidate profile matches the baseline authority's exact
         stdout bytes, stderr bytes and exit code -- so correctness is
         anchored to the adopted implementation, not to two newly built
         candidate binaries agreeing with each other;
      3. the two candidate profiles match each other exactly.

    When standalone_dir is supplied the RELEASE binary is additionally
    staged and run for every case from a private directory outside the
    source tree with an empty PATH, so the standalone proof covers the
    complete corpus rather than one clean bundle."""
    problems = []
    seen = {}
    results = []
    for case in cases:
        case_id = case["case_id"]
        seen[case_id] = seen.get(case_id, 0) + 1
        if not os.path.exists(case["path"]):
            problems.append("adopted fixture missing: %s (%s)"
                            % (case_id, case["path"]))
            continue
        kind = case.get("expected_kind", "reason_code")
        allow_count = case["argv"][0] == "inspect-archive"

        r_rc, r_out, r_err = run_binary(release_bin, case["argv"], None)
        problems.extend(check_exact_record(
            r_out, r_err, r_rc, case["expected"], "release/%s" % case_id,
            reason_map=reason_map, expect_kind=kind,
            allow_entry_count=allow_count))

        d_rc, d_out, d_err = run_binary(debug_bin, case["argv"], None)
        problems.extend(check_exact_record(
            d_out, d_err, d_rc, case["expected"], "debug/%s" % case_id,
            reason_map=reason_map, expect_kind=kind,
            allow_entry_count=allow_count))

        if (d_rc, d_out, d_err) != (r_rc, r_out, r_err):
            problems.append("candidate profiles diverge on %s" % case_id)

        if baseline_bin is not None:
            b_rc, b_out, b_err = run_binary(baseline_bin, case["argv"], None)
            if (r_rc, r_out, r_err) != (b_rc, b_out, b_err):
                problems.append(
                    "release differs from the adopted baseline authority "
                    "on %s" % case_id)
            if (d_rc, d_out, d_err) != (b_rc, b_out, b_err):
                problems.append(
                    "debug differs from the adopted baseline authority "
                    "on %s" % case_id)

        if standalone_dir is not None:
            s_rc, s_out, s_err, _ = standalone_proof(
                release_bin, os.path.join(standalone_dir, case_id),
                case["path"], [case["argv"][0], "@INPUT@"])
            if (s_rc, s_out, s_err) != (r_rc, r_out, r_err):
                problems.append(
                    "staged standalone run differs from the in-tree run "
                    "on %s" % case_id)
            problems.extend(check_exact_record(
                s_out, s_err, s_rc, case["expected"],
                "standalone/%s" % case_id, reason_map=reason_map,
                expect_kind=kind, allow_entry_count=allow_count))

        results.append({"case_id": case_id, "exit_code": r_rc,
                        "stdout_bytes": len(r_out),
                        "stderr_bytes": len(r_err)})
    for case_id, count in sorted(seen.items()):
        if count != 1:
            problems.append("case %s present %d times, expected exactly once"
                            % (case_id, count))
    return problems, results


def check_canonical_json_bytes(raw, label):
    """BLOCKER 3: canonical JSON must be byte-exact.

    Parsing and comparing semantic values permits non-canonical formatting,
    so the bytes themselves are checked: exactly one JSON line, exactly one
    trailing newline, no duplicate keys, and a byte-for-byte match against
    the canonical re-serialisation (sorted keys, compact separators)."""
    problems = []
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return ["%s output is not UTF-8" % label]
    if text == "":
        return ["%s produced no output" % label]
    if not text.endswith("\n"):
        problems.append("%s output has no trailing newline" % label)
    if text.endswith("\n\n"):
        problems.append("%s output has more than one trailing newline"
                        % label)
    if text.count("\n") != 1:
        problems.append("%s output is not exactly one JSON line" % label)
    body = text[:-1] if text.endswith("\n") else text
    if body != body.strip():
        problems.append("%s output has leading or trailing whitespace"
                        % label)

    seen = []

    def _pairs(pairs):
        seen.append([k for k, _v in pairs])
        return dict(pairs)

    try:
        record = json.loads(body, object_pairs_hook=_pairs)
    except ValueError:
        problems.append("%s output is not valid JSON" % label)
        return problems
    for keys in seen:
        if len(keys) != len(set(keys)):
            problems.append("%s output contains duplicate keys" % label)
            break
    if not isinstance(record, dict):
        problems.append("%s output is not a JSON object" % label)
        return problems
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False) + "\n"
    if text != canonical:
        problems.append(
            "%s output is not canonical JSON bytes (key order, separators "
            "or spacing differ from the canonical form)" % label)
    return problems


def run_adapter_equivalence(adapter, python_bin, release_bin, debug_bin,
                            reason_map_path, cases, baseline_bin=None):
    """BLOCKERS 1 and 2: the ADOPTED adapter is the authority.

    Earlier versions reimplemented the Move 81 schema from memory. That
    approximation omitted the mandatory `operation` field and compared the
    adapter's NORMALIZED reason_code against the RAW Rust reason, so it
    rejected genuine adopted records: a real clean-bundle run emits
    operation=verify_bundle and reason_code=OK where the raw Rust reason
    is RECEIPT_CHAIN_HASHES_RECOMPUTED.

    No schema is reconstructed here. For every case the genuine inherited
    adapter is run against the ADOPTED BASELINE verifier, and its exact
    stdout bytes, stderr bytes and process exit become the authority. Both
    candidate profiles must reproduce that result byte-for-byte."""
    if baseline_bin is None:
        raise EquivalenceError(
            "adapter equivalence requires the adopted baseline verifier: "
            "the genuine adapter output is the only valid authority")
    problems = []
    checked = 0
    for case in cases:
        lane = ("archive" if case["argv"][0] == "inspect-archive"
                else "rust_bundle")
        label = case["case_id"]
        common = [python_bin, "-B", adapter, "verdict", "--lane", lane,
                  "--input", case["path"], "--reason-map", reason_map_path]

        base = subprocess.run(common + ["--rust-bin", baseline_bin],
                              capture_output=True,
                              timeout=RUN_TIMEOUT_SECONDS)
        if base.stderr:
            problems.append(
                "baseline adapter emitted stderr on %s" % label)
            continue
        problems.extend(check_canonical_json_bytes(
            base.stdout, "baseline adapter/%s" % label))

        for profile, binary in (("release", release_bin),
                                ("debug", debug_bin)):
            run = subprocess.run(common + ["--rust-bin", binary],
                                 capture_output=True,
                                 timeout=RUN_TIMEOUT_SECONDS)
            tag = "%s adapter/%s" % (profile, label)
            problems.extend(check_canonical_json_bytes(run.stdout, tag))
            if run.stdout != base.stdout:
                problems.append(
                    "%s stdout is not byte-identical to the adopted "
                    "baseline adapter result" % tag)
            if run.stderr != base.stderr:
                problems.append(
                    "%s stderr is not byte-identical to the adopted "
                    "baseline adapter result" % tag)
            if run.returncode != base.returncode:
                problems.append(
                    "%s process exit %r differs from the adopted baseline "
                    "adapter exit %r" % (tag, run.returncode,
                                         base.returncode))
        checked += 1
    return problems, checked


def run_controlled(release_bin, debug_bin, cases):
    """For every adopted case: assert the release binary meets the adopted
    expectation, then require the debug binary to behave byte-identically.
    Both halves are required -- two identically WRONG binaries must not
    pass, and identical non-empty stderr must fail."""
    problems = []
    seen = {}
    results = []
    for case in cases:
        case_id = case["case_id"]
        seen[case_id] = seen.get(case_id, 0) + 1
        if not os.path.exists(case["path"]):
            problems.append("adopted fixture missing: %s (%s)"
                            % (case_id, case["path"]))
            continue
        r_rc, r_out, r_err = run_binary(release_bin, case["argv"], None)
        problems.extend(check_against_expectation(
            r_out, r_err, r_rc, case["expected"], "release/%s" % case_id))
        d_rc, d_out, d_err = run_binary(debug_bin, case["argv"], None)
        if (d_rc, d_out, d_err) != (r_rc, r_out, r_err):
            detail = []
            if d_rc != r_rc:
                detail.append("exit %d vs %d" % (r_rc, d_rc))
            if d_out != r_out:
                detail.append("stdout differs")
            if d_err != r_err:
                detail.append("stderr differs")
            problems.append("profiles diverge on %s: %s"
                            % (case_id, "; ".join(detail)))
        results.append({"case_id": case_id, "exit_code": r_rc,
                        "stdout_bytes": len(r_out),
                        "stderr_bytes": len(r_err)})
    for case_id, count in sorted(seen.items()):
        if count != 1:
            problems.append("case %s present %d times, expected exactly once"
                            % (case_id, count))
    return problems, results


REQUIRED_EDGE_SURFACES = (
    "zip_control", "zip_offset", "zip_size", "zip_count",
    "json_numeric", "json_length", "json_depth",
    "manifest_index", "receipt_index",
)

# Files the adopted Rust verifier actually reads, established from
# rust/witness-verify/src: manifest::MANIFEST_FILE is companion_report.json
# and is parsed at the MANIFEST stage; receipts::RUN_RECORD is
# coordinator_output/sentinel_run/sentinel_run.json and is read at the
# RECEIPTS stage. Stage order in main.rs is manifest -> hashes -> receipts.
MANIFEST_FILE = "companion_report.json"
RUN_RECORD = os.path.join("coordinator_output", "sentinel_run",
                          "sentinel_run.json")
# companion_checksums.txt declares eight files; sentinel_run.json is NOT
# among them, so mutating the run record does not disturb the hash stage
# and no checksum repair is required to reach the receipts stage.
CHECKSUMS_FILE = "companion_checksums.txt"


def make_edge_fixtures(outdir, clean_bundle=None):
    """Hostile edge fixtures for every required arithmetic surface, built
    from the REAL adopted frozen bundle.

    Earlier versions mutated a top-level `case_manifest.json`, which does
    not exist in the adopted reference bundle, so four surfaces were
    silently omitted and the receipt fixture never reached the receipts
    stage. This generator uses only files the verifier genuinely reads,
    and REQUIRES the complete surface set: if any required fixture cannot
    be created it raises rather than silently producing a short set."""
    import shutil
    import struct
    import zipfile

    os.makedirs(outdir, exist_ok=True)
    made = []

    # ---- ZIP offset / size / count arithmetic --------------------------
    def _zip(name, surface, mutate=None):
        path = os.path.join(outdir, name)
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("a.txt", "payload")
        if mutate is not None:
            with open(path, "rb") as handle:
                data = bytearray(handle.read())
            mutate(data)
            with open(path, "wb") as handle:
                handle.write(bytes(data))
        # Only design INTENT is declared here. Verdict, exit code, reason
        # code, class and stage are ESTABLISHED from the adopted baseline
        # verifier by pin_edge_contract -- never assumed. Hand-declaring
        # them is exactly what made edge_control.zip claim INCONCLUSIVE/3
        # when the adopted verifier genuinely answers FAIL/1.
        made.append({"kind": "archive", "path": path, "surface": surface,
                     "stage_intent": "archive"})
        return path

    def _patch_eocd(data, offset, value, width=4):
        idx = data.rfind(b"PK\x05\x06")
        if idx == -1:
            raise EquivalenceError("edge archive has no end-of-central-dir")
        struct.pack_into("<I" if width == 4 else "<H", data,
                         idx + offset, value)

    def _patch_local_size(data, value):
        idx = data.find(b"PK\x03\x04")
        if idx == -1:
            raise EquivalenceError("edge archive has no local header")
        struct.pack_into("<I", data, idx + 18, value)
        struct.pack_into("<I", data, idx + 22, value)

    _zip("edge_control.zip", "zip_control")
    _zip("edge_cd_offset_max.zip", "zip_offset",
         lambda d: _patch_eocd(d, 16, 0xFFFFFFFF))
    _zip("edge_cd_size_max.zip", "zip_size",
         lambda d: _patch_eocd(d, 12, 0xFFFFFFFF))
    _zip("edge_entry_count_max.zip", "zip_count",
         lambda d: (_patch_eocd(d, 8, 0xFFFF, 2),
                    _patch_eocd(d, 10, 0xFFFF, 2)))
    _zip("edge_local_size_max.zip", "zip_size",
         lambda d: _patch_local_size(d, 0xFFFFFFFF))

    if not (clean_bundle and os.path.isdir(clean_bundle)):
        raise EquivalenceError(
            "a real frozen bundle is required to build the bundle edge "
            "surfaces; none was supplied")

    manifest_src = os.path.join(clean_bundle, MANIFEST_FILE)
    run_src = os.path.join(clean_bundle, RUN_RECORD)
    if not os.path.isfile(manifest_src):
        raise EquivalenceError(
            "the supplied bundle has no %s, so the manifest-stage surfaces "
            "cannot be built" % MANIFEST_FILE)
    if not os.path.isfile(run_src):
        raise EquivalenceError(
            "the supplied bundle has no %s, so the receipt-stage surface "
            "cannot be built" % RUN_RECORD)

    def _copy(name):
        dest = os.path.join(outdir, name)
        if os.path.isdir(dest):
            shutil.rmtree(dest)
        shutil.copytree(clean_bundle, dest)
        return dest

    def _manifest_edge(name, surface, mutate_text=None, mutate_obj=None):
        """Mutate companion_report.json, which the verifier parses at the
        MANIFEST stage -- the stage that runs before hashes, so a
        manifest-stage answer is reached without any checksum repair."""
        dest = _copy(name)
        target = os.path.join(dest, MANIFEST_FILE)
        if mutate_text is not None:
            with open(target, "w", encoding="utf-8") as handle:
                handle.write(mutate_text)
        else:
            with open(target, encoding="utf-8") as handle:
                data = json.load(handle)
            mutate_obj(data)
            with open(target, "w", encoding="utf-8") as handle:
                json.dump(data, handle, sort_keys=True,
                          separators=(",", ":"))
        made.append({"kind": "bundle", "path": dest, "surface": surface,
                     "stage_intent": "manifest"})
        return dest

    # ---- JSON numeric limits (a valid but extreme number) --------------
    _manifest_edge(
        "edge_json_numeric", "json_numeric",
        mutate_obj=lambda d: d.__setitem__(
            "edge_probe_numeric", 99999999999999999999999999999999))
    # ---- JSON length --------------------------------------------------
    _manifest_edge(
        "edge_json_length", "json_length",
        mutate_obj=lambda d: d.__setitem__("edge_probe_length",
                                           "x" * 200000))
    # ---- JSON depth ---------------------------------------------------
    _manifest_edge("edge_json_depth", "json_depth",
                   mutate_text="[" * 400 + "]" * 400)

    # ---- manifest / index arithmetic ----------------------------------
    def _many_entries(data):
        for key in ("steps", "files", "components", "artifacts",
                    "checks", "results"):
            value = data.get(key)
            if isinstance(value, list) and value:
                data[key] = [value[0]] * 20000
                return
        data["edge_probe_index"] = list(range(20000))

    _manifest_edge("edge_manifest_index", "manifest_index",
                   mutate_obj=_many_entries)

    # ---- receipt-chain / index arithmetic ------------------------------
    # The REAL run record carries real receipts. An extreme receipt_id is
    # inserted into an actual receipt field. sentinel_run.json is not one
    # of the eight declared checksummed files, so the hash stage is
    # untouched and the receipts stage is genuinely reached.
    dest = _copy("edge_receipt_index")
    target = os.path.join(dest, RUN_RECORD)
    with open(target, encoding="utf-8") as handle:
        run_record = json.load(handle)
    receipts = run_record.get("receipts")
    if not isinstance(receipts, list) or not receipts:
        shutil.rmtree(dest)
        raise EquivalenceError(
            "the supplied run record carries no receipts, so the "
            "receipt-index surface cannot be built honestly")
    if "receipt_id" not in receipts[0]:
        shutil.rmtree(dest)
        raise EquivalenceError(
            "the run record's receipts have no receipt_id field")
    receipts[0]["receipt_id"] = 2 ** 63 - 1
    with open(target, "w", encoding="utf-8") as handle:
        json.dump(run_record, handle, sort_keys=True,
                  separators=(",", ":"))
    made.append({"kind": "bundle", "path": dest, "surface": "receipt_index",
                 "stage_intent": "receipts"})

    # The complete surface set is REQUIRED. A short set is a generator
    # failure, never a silently smaller run.
    produced = {item["surface"] for item in made}
    missing = sorted(set(REQUIRED_EDGE_SURFACES) - produced)
    if missing:
        raise EquivalenceError(
            "edge generation did not produce required surface(s): %s"
            % ", ".join(missing))
    return sorted(made, key=lambda item: item["path"])


# The six arithmetic surfaces the Phase 1 inventory identified. Every edge
# fixture declares one, and every fixture must be answered at the exact
# adopted stage it targets.
EDGE_SURFACES = (
    "zip_control", "zip_offset", "zip_size", "zip_count",
    "json_numeric", "json_length", "json_depth",
    "manifest_index", "receipt_index",
)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Move 82 equivalence / standalone proof")
    parser.add_argument("--release-bin", required=False)
    parser.add_argument("--debug-bin", required=False)
    parser.add_argument("--baseline-bin", required=False)
    parser.add_argument("--mode", required=True,
                        choices=("controlled", "standalone",
                                 "make-edge-fixtures", "edge-equivalence",
                                 "build-archives", "full-corpus",
                                 "adapter-equivalence", "usage-contract"))
    parser.add_argument("--cwd", default=None)
    parser.add_argument("--workdir", default=None)
    parser.add_argument("--input", default=None)
    parser.add_argument("--outdir", default=None)
    parser.add_argument("--clean-bundle", default=None)
    parser.add_argument("--expected-results", default=None)
    parser.add_argument("--fixture-manifest", default=None)
    parser.add_argument("--fixtures-dir", default=None)
    parser.add_argument("--harness-dir", default=None)
    parser.add_argument("--archives-dir", default=None)
    parser.add_argument("--real-705", default=None)
    parser.add_argument("--real-move78", default=None)
    parser.add_argument("--real-v20", default=None)
    parser.add_argument("--reason-map", default=None)
    parser.add_argument("--adapter", default=None)
    parser.add_argument("--python-bin", default=None)
    parser.add_argument("--edge-manifest", default=None)
    parser.add_argument("--standalone-dir", default=None)
    parser.add_argument("--expect-verdict", default=None)
    parser.add_argument("--expect-reason-code", default=None)
    parser.add_argument("--expect-exit-code", type=int, default=None)
    parser.add_argument("--json-out", default=None)
    args = parser.parse_args(argv)

    def _abs(value, what):
        if not value or not os.path.isabs(value):
            raise EquivalenceError("%s must be an absolute path" % what)
        return value

    def _emit(payload):
        if args.json_out and os.path.isabs(args.json_out):
            with open(args.json_out, "wb") as handle:
                handle.write((json.dumps(
                    payload, sort_keys=True, separators=(",", ":"),
                    ensure_ascii=False) + "\n").encode("utf-8"))

    def _assemble_cases():
        """The COMPLETE adopted corpus: the clean frozen bundle, all eight
        Move 80 fixtures and all in-scope adopted archive cases."""
        cases = []
        if args.expected_results and args.fixture_manifest \
                and args.fixtures_dir:
            cases.extend(load_controlled_cases(
                _abs(args.expected_results, "--expected-results"),
                _abs(args.fixture_manifest, "--fixture-manifest"),
                _abs(args.fixtures_dir, "--fixtures-dir")))
        if args.clean_bundle:
            cases.append({
                "case_id": "FROZEN-CLEAN-BUNDLE",
                "argv": ["verify", args.clean_bundle],
                "expected": {"verdict": "INCONCLUSIVE",
                             "reason_code":
                                 "RECEIPT_CHAIN_HASHES_RECOMPUTED",
                             "exit_code": 3},
                "expected_kind": "reason_code",
                "path": args.clean_bundle,
            })
        if args.harness_dir and args.archives_dir:
            harness = _abs(args.harness_dir, "--harness-dir")
            lock = verify_corpus_pins(harness)
            archives = build_archive_fixtures(
                os.path.join(harness, "corpus"),
                _abs(args.archives_dir, "--archives-dir"), lock)
            external = {}
            for case_id, value in (("real_705", args.real_705),
                                   ("real_move78", args.real_move78),
                                   ("real_v20", args.real_v20)):
                if value:
                    external[case_id] = _abs(value, "--" + case_id)
            cases.extend(load_archive_cases(
                os.path.join(harness, "corpus", "archive_cases.json"),
                archives, external))
        return cases

    try:
        if args.mode == "build-archives":
            harness = _abs(args.harness_dir, "--harness-dir")
            lock = verify_corpus_pins(harness)
            archives = build_archive_fixtures(
                os.path.join(harness, "corpus"),
                _abs(args.archives_dir, "--archives-dir"), lock)
            _emit({"archives": sorted(archives)})
            print("CORPUS_FIXTURES_BUILT: %d" % len(archives))
            print("CORPUS_PINS: PASS")
            print("BUILD_ARCHIVES: PASS (%d)" % len(archives))
            return 0

        if args.mode == "make-edge-fixtures":
            made = make_edge_fixtures(_abs(args.outdir, "--outdir"),
                                     args.clean_bundle)
            _emit({"fixtures": made})
            surfaces = sorted({f["surface"] for f in made})
            print("EDGE_SURFACES: %s" % ",".join(surfaces))
            print("EDGE_FIXTURES: PASS (%d)" % len(made))
            return 0

        release_bin = _require_abs_exec(args.release_bin, "--release-bin")

        if args.mode == "full-corpus":
            debug_bin = _require_abs_exec(args.debug_bin, "--debug-bin")
            baseline_bin = None
            if args.baseline_bin:
                baseline_bin = _require_abs_exec(args.baseline_bin,
                                                 "--baseline-bin")
            reason_map = load_reason_map(
                _abs(args.reason_map, "--reason-map"))
            cases = _assemble_cases()
            if not cases:
                raise EquivalenceError("no adopted cases were assembled")
            problems, results = run_full_corpus(
                release_bin, debug_bin, baseline_bin, cases, reason_map,
                standalone_dir=args.standalone_dir)
            for problem in problems:
                print("CORPUS_MISMATCH: %s" % problem)
            _emit({"cases": results})
            if problems:
                print("FULL_CORPUS: FAIL (%d problem(s))" % len(problems))
                return 1
            print("FULL_CORPUS: PASS (%d case(s))" % len(results))
            return 0

        if args.mode == "usage-contract":
            debug_bin = _require_abs_exec(args.debug_bin, "--debug-bin")
            baseline_bin = None
            if args.baseline_bin:
                baseline_bin = _require_abs_exec(args.baseline_bin,
                                                 "--baseline-bin")
            problems, checked = run_usage_contract(
                release_bin, debug_bin, baseline_bin,
                standalone_dir=args.standalone_dir)
            for problem in problems:
                print("USAGE_MISMATCH: %s" % problem)
            if problems:
                print("USAGE_CONTRACT: FAIL (%d problem(s))"
                      % len(problems))
                return 1
            print("USAGE_CONTRACT: PASS (%d case(s))" % checked)
            return 0

        if args.mode == "adapter-equivalence":
            debug_bin = _require_abs_exec(args.debug_bin, "--debug-bin")
            adapter = _abs(args.adapter, "--adapter")
            python_bin = _require_abs_exec(args.python_bin, "--python-bin")
            reason_map_path = _abs(args.reason_map, "--reason-map")
            cases = _assemble_cases()
            baseline_bin = None
            if args.baseline_bin:
                baseline_bin = _require_abs_exec(args.baseline_bin,
                                                 "--baseline-bin")
            problems, checked = run_adapter_equivalence(
                adapter, python_bin, release_bin, debug_bin,
                reason_map_path, cases, baseline_bin=baseline_bin)
            for problem in problems:
                print("ADAPTER_MISMATCH: %s" % problem)
            if problems:
                print("ADAPTER_EQUIVALENCE: FAIL (%d problem(s))"
                      % len(problems))
                return 1
            print("ADAPTER_EQUIVALENCE: PASS (%d case(s))" % checked)
            return 0

        if args.mode == "controlled":
            debug_bin = _require_abs_exec(args.debug_bin, "--debug-bin")
            cases = _assemble_cases()
            problems, results = run_controlled(release_bin, debug_bin,
                                               cases)
            for problem in problems:
                print("CONTROLLED_MISMATCH: %s" % problem)
            _emit({"cases": results})
            if problems:
                print("CONTROLLED: FAIL (%d problem(s))" % len(problems))
                return 1
            print("CONTROLLED: PASS (%d case(s))" % len(results))
            return 0

        if args.mode == "edge-equivalence":
            debug_bin = _require_abs_exec(args.debug_bin, "--debug-bin")
            reason_map = load_reason_map(
                _abs(args.reason_map, "--reason-map"))
            with open(_abs(args.edge_manifest, "--edge-manifest"),
                      encoding="utf-8") as handle:
                fixtures = json.load(handle)["fixtures"]

            # every required surface must be present
            surfaces = {f.get("surface") for f in fixtures}
            missing = sorted(set(REQUIRED_EDGE_SURFACES) - surfaces)
            if missing:
                raise EquivalenceError(
                    "edge manifest is missing required surface(s): %s"
                    % ", ".join(missing))

            problems = []
            if args.baseline_bin:
                baseline_bin = _require_abs_exec(args.baseline_bin,
                                                 "--baseline-bin")
                pin_problems, fixtures = pin_edge_contract(
                    baseline_bin, fixtures, reason_map)
                problems.extend(pin_problems)
                if args.json_out and os.path.isabs(args.json_out):
                    _emit({"fixtures": fixtures})
            else:
                # Without a baseline the manifest must already carry a
                # COMPLETE pinned contract. A partially pinned fixture
                # would silently skip whichever field was absent.
                required_pins = ("expect_verdict", "expect_exit_code",
                                 "expect_reason_code",
                                 "expect_reason_class", "expect_stage")
                for fixture in fixtures:
                    missing_pins = [k for k in required_pins
                                    if fixture.get(k) is None]
                    if missing_pins:
                        raise EquivalenceError(
                            "edge fixture %s has no baseline-established "
                            "contract for %s, and no baseline was supplied "
                            "to establish one"
                            % (os.path.basename(fixture["path"]),
                               ", ".join(missing_pins)))

            for fixture in fixtures:
                name = os.path.basename(fixture["path"])
                sub = ("inspect-archive" if fixture["kind"] == "archive"
                       else "verify")
                argv_case = [sub, fixture["path"]]
                r_rc, r_out, r_err = run_binary(release_bin, argv_case,
                                                None)
                d_rc, d_out, d_err = run_binary(debug_bin, argv_case, None)
                # EACH profile is checked against the frozen contract
                # independently: agreeing with each other is not evidence.
                problems.extend(check_edge_contract(
                    r_out, r_err, r_rc, fixture, reason_map,
                    "release/%s" % name))
                problems.extend(check_edge_contract(
                    d_out, d_err, d_rc, fixture, reason_map,
                    "debug/%s" % name))
                if (d_rc, d_out, d_err) != (r_rc, r_out, r_err):
                    problems.append("profiles diverge on edge fixture %s"
                                    % name)
            for problem in problems:
                print("EDGE_MISMATCH: %s" % problem)
            if problems:
                print("EDGE_EQUIVALENCE: FAIL (%d problem(s))"
                      % len(problems))
                return 1
            for fixture in fixtures:
                intent = fixture.get("stage_intent")
                stage = fixture.get("expect_stage")
                print("EDGE_ESTABLISHED: %-26s surface=%-14s "
                      "verdict=%-12s exit=%s stage=%s%s"
                      % (os.path.basename(fixture["path"]),
                         fixture.get("surface"),
                         fixture.get("expect_verdict"),
                         fixture.get("expect_exit_code"), stage,
                         "" if intent in (None, stage)
                         else " (design intent was %s)" % intent))
            print("EDGE_SURFACES_COVERED: %s"
                  % ",".join(sorted(s for s in surfaces if s)))
            print("EDGE_EQUIVALENCE: PASS (%d fixture(s))" % len(fixtures))
            return 0

        # standalone (single explicit case)
        workdir = _abs(args.workdir, "--workdir")
        expected = {}
        if args.expect_verdict:
            expected["verdict"] = args.expect_verdict
        if args.expect_reason_code:
            expected["reason_code"] = args.expect_reason_code
        if args.expect_exit_code is not None:
            expected["exit_code"] = args.expect_exit_code
        if not expected:
            raise EquivalenceError(
                "standalone mode requires explicit expected behaviour")
        rc, out, err, _staged = standalone_proof(
            release_bin, workdir, args.input, ["verify", "@INPUT@"])
        problems = check_exact_record(out, err, rc, expected, "standalone")
        for problem in problems:
            print("STANDALONE_MISMATCH: %s" % problem)
        if problems:
            print("STANDALONE: FAIL (%d problem(s))" % len(problems))
            return 1
        print("STANDALONE: PASS")
        return 0
    except EquivalenceError as exc:
        print("%s: FAIL (%s)" % (args.mode.upper().replace("-", "_"), exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
