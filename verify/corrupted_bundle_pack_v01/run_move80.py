"""Move 80: focused corrupted-bundle runner.

Contract (ruled at adoption-review): execute the EXACT binary supplied by
the caller and evaluate the fixture results. Nothing more.

The runner therefore:
  - REQUIRES --rust-bin as an ABSOLUTE path to an existing regular
    executable file, and refuses anything else (exit 2);
  - never searches PATH for witness-verify, never invokes Cargo, never
    builds Rust, never selects a default or previously built binary, and
    never reuses rust/target unless that exact path was supplied;
  - makes NO trust claim about the supplied binary. Proving that the
    binary is the freshly built, reviewed-source binary is the adoption
    gate's responsibility (tools/check_move80_corrupted_bundle_adoption.sh),
    which owns bootstrap, toolchain resolution, clean-target removal,
    fresh build, provenance binding, version verification and
    stale-executable rejection, then hands the resolved absolute path
    down through --rust-bin.

Evaluation: every fixture is checked against the DECLARED per-lane
expectations in expected_results.json (verdict, exit code, exact/prefix
reason, zero stderr bytes, no signal termination, no timeout). Lane
results are stored separately and never collapsed into one fake common
verdict. "required_cases: 8/8 PASS" means all declared per-lane
expectations were met; it never means the corrupted bundles verified
successfully.

Path traversal: the malicious ZIP is passed DIRECTLY to the adopted
archive-safety boundary (witness-verify inspect-archive and the Python
ZipGuard oracle). No preliminary extraction. Although the adopted
boundary is read-only by design, the runner still builds a sandbox with
an outside sentinel, snapshots the surrounding controlled filesystem
before and after each boundary execution, requires byte-identical state,
and verifies its own temporary resources are removed.

Output: ONE canonical JSON object on stdout (sorted keys, no absolute
paths, no timestamps, no order marker), so the adoption gate can require
byte-identical output across original / reversed / deterministically
shuffled execution orders. stdout carries nothing else; stderr stays
empty on a clean run. Exit codes: 0 all expectations met, 1 otherwise,
2 usage.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

sys.path.insert(0, HERE)
import generate_fixtures as gen

ORACLES = os.path.join(ROOT, "verify", "agreement_harness_v01", "oracles")
COMPANION_CLI = os.path.join(ROOT, "src", "12_companion_cli_v031",
                             "companion.py")

EXIT_FOR_VERDICT = {"PASS": 0, "FAIL": 1, "USAGE": 2, "INCONCLUSIVE": 3}
SUBPROCESS_TIMEOUT = 300
# The traversal fixture's single entry is named ../evil. Executed with the
# archive inside sandbox/work, that entry's REAL destination is
# sandbox/evil -- so the outside sentinel IS that destination.
EVIL_NAME = "evil"
EVIL_SENTINEL_BYTES = b"MOVE80 OUTSIDE SENTINEL at the ../evil destination: must never change\n"
EVIL_SENTINEL_MODE = 0o644


def load_expected():
    with open(os.path.join(HERE, "expected_results.json"), "r",
              encoding="utf-8") as handle:
        return json.load(handle)["cases"]


def validate_rust_bin(path):
    """Reject anything but an absolute path to an existing regular
    executable file. Returns an error string or None."""
    if not path:
        return "missing --rust-bin"
    if not os.path.isabs(path):
        return "--rust-bin must be an absolute path"
    if not os.path.exists(path):
        return "--rust-bin path does not exist"
    if os.path.isdir(path) or not os.path.isfile(path):
        return "--rust-bin is not a regular file"
    if not os.access(path, os.X_OK):
        return "--rust-bin is not executable"
    return None


def _exec(argv, cwd):
    """Run one verifier process. Never uses shell, never touches PATH for
    the target (argv[0] is always an absolute path supplied by the
    caller or sys.executable)."""
    try:
        proc = subprocess.run(argv, capture_output=True, text=True,
                              cwd=cwd, timeout=SUBPROCESS_TIMEOUT,
                              env=dict(os.environ,
                                       PYTHONDONTWRITEBYTECODE="1"))
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT", "exit_code": None,
                "stdout": "", "stderr_len": 0}
    if proc.returncode is not None and proc.returncode < 0:
        return {"status": "SIGNALED", "exit_code": proc.returncode,
                "stdout": proc.stdout.strip(),
                "stderr_len": len(proc.stderr)}
    return {"status": "COMPLETED", "exit_code": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr_len": len(proc.stderr)}


def observe_python(bundle):
    raw = _exec([sys.executable, "-B", COMPANION_CLI,
                 "verify", "--run", bundle], cwd=ROOT)
    obs = {"exit_code": raw["exit_code"], "status": raw["status"],
           "stderr_len": raw["stderr_len"], "verdict": None,
           "reason": None}
    if raw["status"] != "COMPLETED":
        return obs
    try:
        out = json.loads(raw["stdout"])
        if not isinstance(out, dict):
            raise ValueError("not an object")
    except ValueError:
        obs["status"] = "MALFORMED_OUTPUT"
        return obs
    if out.get("verify_ok") is True:
        obs["verdict"] = "PASS"
        obs["reason"] = out.get("reason", "")
    else:
        obs["verdict"] = "FAIL"
        obs["reason"] = out.get("error", out.get("reason", ""))
    return obs


def observe_rust(rust_bin, mode, target, cwd=None):
    raw = _exec([rust_bin, mode, target], cwd=cwd or ROOT)
    obs = {"exit_code": raw["exit_code"], "status": raw["status"],
           "stderr_len": raw["stderr_len"], "verdict": None,
           "reason": None}
    if raw["status"] != "COMPLETED":
        return obs
    try:
        out = json.loads(raw["stdout"])
        if not isinstance(out, dict):
            raise ValueError("not an object")
        obs["verdict"] = out["verdict"]
        obs["reason"] = out["reason_code"]
    except (ValueError, KeyError):
        obs["status"] = "MALFORMED_OUTPUT"
    return obs


def observe_oracle(zip_path):
    sys.path.insert(0, ORACLES)
    try:
        import zipguard_oracle
    finally:
        sys.path.remove(ORACLES)
    try:
        res = zipguard_oracle.inspect_archive(zip_path)
        return {"status": "COMPLETED", "stderr_len": 0,
                "verdict": res["verdict"],
                "reason": res["reason_code"],
                "exit_code": EXIT_FOR_VERDICT[res["verdict"]]}
    except Exception:
        return {"status": "ORACLE_ERROR", "stderr_len": 0,
                "verdict": None, "reason": None, "exit_code": None}


def evaluate(expected, observed):
    """Compare one lane observation against its declared expectation.
    Returns (met, diagnostics)."""
    diags = []
    if observed["status"] != "COMPLETED":
        return False, ["process status %s" % observed["status"]]
    if observed["stderr_len"] != 0:
        diags.append("stderr not empty (%d bytes)"
                     % observed["stderr_len"])
    if observed["verdict"] != expected["verdict"]:
        diags.append("verdict %r != expected %r"
                     % (observed["verdict"], expected["verdict"]))
    if observed["exit_code"] != expected["exit_code"]:
        diags.append("exit %r != expected %r"
                     % (observed["exit_code"], expected["exit_code"]))
    want = expected.get("reason", expected.get("reason_code"))
    got = observed["reason"] or ""
    if expected["match_type"] == "exact":
        if got != want:
            diags.append("reason %r != expected %r" % (got, want))
    elif expected["match_type"] == "prefix":
        if not got.startswith(want):
            diags.append("reason %r does not start with %r" % (got, want))
    else:
        diags.append("unknown match_type %r" % expected["match_type"])
    return (not diags), diags


def _snapshot(root):
    state = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(dirnames):
            rel = os.path.relpath(os.path.join(dirpath, name), root)
            state[rel.replace(os.sep, "/")] = ("D", "", None)
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            with open(full, "rb") as handle:
                digest = hashlib.sha256(handle.read()).hexdigest()
            state[rel] = ("F", digest, os.stat(full).st_mode & 0o777)
    return state


def _run_boundaries_in_sandbox(fixture_id, fixtures_dir, rust_bin,
                               pre_create_evil):
    """One fresh controlled sandbox: sandbox/work holds a copy of the
    malicious ZIP (passed DIRECTLY to both adopted archive boundaries,
    cwd=work, never pre-extracted); sandbox/evil is the REAL resolved
    destination of the archive's ../evil entry. If pre_create_evil, the
    destination file is created first with recorded bytes/type/mode and
    must survive byte-identically (overwrite/deletion test); otherwise
    it must remain ABSENT (creation test). The whole sandbox is
    snapshotted before and after each boundary execution and must be
    byte-identical. Returns (lane observations, checks dict)."""
    checks = {}
    sandbox = tempfile.mkdtemp(prefix="m80_sandbox_")
    try:
        work = os.path.join(sandbox, "work")
        os.makedirs(work)
        zip_src = os.path.join(fixtures_dir,
                               gen.fixture_filename(fixture_id))
        zip_in = os.path.join(work, os.path.basename(zip_src))
        shutil.copyfile(zip_src, zip_in)
        evil = os.path.join(sandbox, EVIL_NAME)
        if pre_create_evil:
            with open(evil, "wb") as handle:
                handle.write(EVIL_SENTINEL_BYTES)
            os.chmod(evil, EVIL_SENTINEL_MODE)

        before = _snapshot(sandbox)
        obs_rust = observe_rust(rust_bin, "inspect-archive", zip_in,
                                cwd=work)
        after_rust = _snapshot(sandbox)
        obs_oracle = observe_oracle(zip_in)
        after_oracle = _snapshot(sandbox)

        checks["sandbox_unchanged"] = (before == after_rust
                                       and before == after_oracle)
        if pre_create_evil:
            intact = (os.path.isfile(evil)
                      and not os.path.islink(evil))
            if intact:
                with open(evil, "rb") as handle:
                    intact = handle.read() == EVIL_SENTINEL_BYTES
                intact = intact and (
                    os.stat(evil).st_mode & 0o777 == EVIL_SENTINEL_MODE)
            checks["evil_destination_intact"] = intact
        else:
            checks["evil_destination_absent"] = not os.path.lexists(evil)
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)
    checks["temp_cleaned"] = not os.path.exists(sandbox)
    return obs_rust, obs_oracle, checks


def run_traversal_case(fixture_id, fixtures_dir, expected_case, rust_bin):
    """Sandboxed traversal execution against BOTH adopted archive
    boundaries, twice: (A) creation test with the ../evil destination
    absent, proving it is not created; (B) overwrite/deletion test with
    the destination pre-created as the outside sentinel, proving it is
    neither altered nor removed. Verdicts must match the declared
    expectations in BOTH runs."""
    obs_rust_a, obs_orc_a, checks_a = _run_boundaries_in_sandbox(
        fixture_id, fixtures_dir, rust_bin, pre_create_evil=False)
    obs_rust_b, obs_orc_b, checks_b = _run_boundaries_in_sandbox(
        fixture_id, fixtures_dir, rust_bin, pre_create_evil=True)

    lanes = {}
    met_r_a, diag_r_a = evaluate(expected_case["rust_expected"], obs_rust_a)
    met_r_b, diag_r_b = evaluate(expected_case["rust_expected"], obs_rust_b)
    met_o_a, diag_o_a = evaluate(
        expected_case["archive_oracle_expected"], obs_orc_a)
    met_o_b, diag_o_b = evaluate(
        expected_case["archive_oracle_expected"], obs_orc_b)
    lanes["rust"] = {
        "expected": expected_case["rust_expected"],
        "observed_creation_test": _public(obs_rust_a),
        "observed_overwrite_test": _public(obs_rust_b),
        "met": met_r_a and met_r_b,
        "diagnostics": diag_r_a + diag_r_b}
    lanes["archive_oracle"] = {
        "expected": expected_case["archive_oracle_expected"],
        "observed_creation_test": _public(obs_orc_a),
        "observed_overwrite_test": _public(obs_orc_b),
        "met": met_o_a and met_o_b,
        "diagnostics": diag_o_a + diag_o_b}
    sandbox_checks = {"creation_test": checks_a,
                      "overwrite_test": checks_b}
    sandbox_ok = (all(checks_a.values()) and all(checks_b.values()))
    case_met = sandbox_ok and all(l["met"] for l in lanes.values())
    return {"fixture_id": fixture_id,
            "classification": expected_case["classification"],
            "lanes": lanes, "sandbox_checks": sandbox_checks,
            "met": case_met}


def _public(observed):
    """Observation as reported in canonical output (no absolute paths,
    no timestamps are ever collected, so nothing to strip)."""
    return {"verdict": observed["verdict"],
            "exit_code": observed["exit_code"],
            "reason": observed["reason"],
            "status": observed["status"],
            "stderr_len": observed["stderr_len"]}


def run_bundle_case(fixture_id, fixtures_dir, expected_case, rust_bin):
    bundle = os.path.join(fixtures_dir, gen.fixture_filename(fixture_id))
    lanes = {}
    obs_py = observe_python(bundle)
    met_py, diag_py = evaluate(expected_case["python_expected"], obs_py)
    lanes["python"] = {"expected": expected_case["python_expected"],
                       "observed": _public(obs_py),
                       "met": met_py, "diagnostics": diag_py}
    obs_rs = observe_rust(rust_bin, "verify", bundle)
    met_rs, diag_rs = evaluate(expected_case["rust_expected"], obs_rs)
    lanes["rust"] = {"expected": expected_case["rust_expected"],
                     "observed": _public(obs_rs),
                     "met": met_rs, "diagnostics": diag_rs}
    return {"fixture_id": fixture_id,
            "classification": expected_case["classification"],
            "lanes": lanes,
            "met": all(l["met"] for l in lanes.values())}


def ordered_ids(order):
    ids = list(gen.FIXTURE_IDS)
    if order == "reversed":
        return list(reversed(ids))
    if order == "shuffled":
        return sorted(ids, key=lambda i: hashlib.sha256(
            i.encode("utf-8")).hexdigest())
    return ids


def run_all(fixtures_dir, rust_bin, order):
    expected = load_expected()
    results = []
    for fid in ordered_ids(order):
        case = expected[fid]
        if fid == "M80-PATH-TRAVERSAL-001":
            results.append(run_traversal_case(fid, fixtures_dir, case,
                                              rust_bin))
        else:
            results.append(run_bundle_case(fid, fixtures_dir, case,
                                           rust_bin))
    results.sort(key=lambda r: r["fixture_id"])
    met_count = sum(1 for r in results if r["met"])
    negative_ids = [f for f in gen.FIXTURE_IDS if f != "M80-CLEAN-001"]
    negative_ok = all(r["met"] for r in results
                      if r["fixture_id"] in negative_ids)
    overall = "PASS" if met_count == len(gen.FIXTURE_IDS) else "FAIL"
    doc = {
        "pack": "corrupted_bundle_pack_v01",
        "overall_status": overall,
        "required_cases": "%d/%d" % (met_count, len(gen.FIXTURE_IDS)),
        "negative_detection": "PASS" if negative_ok else "FAIL",
        "meaning": "required_cases counts fixtures whose DECLARED "
                   "per-lane expectations were all met; it never means "
                   "the corrupted bundles verified successfully",
        "rust_bin_sha256": gen.sha256_file(rust_bin),
        "results": results,
    }
    return doc


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run the Move 80 corrupted-bundle fixtures against "
                    "the exact supplied witness-verify binary and the "
                    "frozen Python lane, evaluating declared per-lane "
                    "expectations.")
    parser.add_argument("--rust-bin", required=True,
                        help="ABSOLUTE path to the witness-verify binary "
                             "supplied by the adoption gate. The runner "
                             "makes no trust claim about it and will not "
                             "search PATH, build, or substitute another "
                             "binary.")
    parser.add_argument("--fixtures", required=True,
                        help="directory of freshly generated fixtures")
    parser.add_argument("--order", default="original",
                        choices=("original", "reversed", "shuffled"))
    args = parser.parse_args(argv)

    err = validate_rust_bin(args.rust_bin)
    if err:
        print("usage error: %s" % err, file=sys.stderr)
        return 2
    if not os.path.isdir(args.fixtures):
        print("usage error: --fixtures is not a directory", file=sys.stderr)
        return 2

    doc = run_all(args.fixtures, args.rust_bin, args.order)
    print(json.dumps(doc, sort_keys=True, separators=(",", ":")))
    return 0 if doc["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
