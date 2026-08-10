"""Move 79 Python/Rust agreement harness (current candidate).

Three-way comparison per case: independently DECLARED expectation vs
PYTHON vs RUST. The expectation carries PER-IMPLEMENTATION raw behaviour
(verdict, exit code, reason class, stage). Python and Rust have DIFFERENT
raw verdicts for an accepted bundle (Python PASS/exit 0; Rust
INCONCLUSIVE/exit 3) and the harness never treats them as identical: only
the shared `normalized_outcome` (ACCEPTED / REJECTED) is comparable across
implementations, alongside mapped reason class and stage.

Everything is fail-closed. No builder-specific paths: real archives are
supplied explicitly and hash-pinned.
"""

import sys

# B1: the verification instrument must NOT mutate the baseline it
# measures. Bytecode caches were being written into adopted src/ and
# freeze_record/ during harness runs. Set this BEFORE importing any
# corpus/oracle module, and propagate it to every subprocess.
sys.dont_write_bytecode = True

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile

os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

RUST_VERIFIER_NAME = "witness-verify"
RUST_VERSION_REQUIRED = "0.0.8-step79-diagnostics"
SUBPROCESS_TIMEOUT = 180

EXIT_FOR_VERDICT = {"PASS": 0, "FAIL": 1, "INCONCLUSIVE": 3}
# BLOCKER 5: the harness itself obeys the same contract.
EXIT_STATUS = {"PASS": 0, "FAIL": 1, "USAGE": 2, "INCONCLUSIVE": 3}


class HarnessError(Exception):
    def __init__(self, code, detail=""):
        super().__init__("%s: %s" % (code, detail))
        self.code = code
        self.detail = detail


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


class ReasonMapper:
    def __init__(self, mapping):
        self.tables = {k: v for k, v in mapping.items()
                       if not k.startswith("_")}

    def map(self, table, raw):
        hits = []
        for entry in self.tables[table]:
            if entry["match_type"] == "exact":
                if raw == entry["value"]:
                    hits.append((entry["class"], entry.get("stage")))
            elif entry["match_type"] == "regex":
                if re.match(entry["value"], raw):
                    hits.append((entry["class"], entry.get("stage")))
            else:
                raise HarnessError("BAD_MATCH_TYPE", entry["match_type"])
        if not hits:
            raise HarnessError("UNMAPPED_REASON", "%s: %r" % (table, raw))
        if len(hits) > 1:
            raise HarnessError("AMBIGUOUS_REASON",
                               "%s: %r -> %s" % (table, raw, hits))
        return hits[0]


VALID_LANES = {"bundle", "archive"}
VALID_SCOPES = {"in_scope", "out_of_scope"}
VALID_CATS = {"AGREEMENT_CASE", "SINGLE_IMPLEMENTATION_CASE",
              "UNSUPPORTED_CASE", "KNOWN_DIVERGENCE_CASE"}
VALID_OUTCOMES = {"ACCEPTED", "REJECTED"}
SHARED_STAGES = {"preflight", "manifest", "hashes", "receipts",
                 "canonical_recompute"}

# Raw verdict -> normalized outcome. Python PASS and Rust INCONCLUSIVE
# both mean "the implementation did not reject"; FAIL means it did.
ACCEPTING_VERDICTS = {"PASS", "INCONCLUSIVE"}


def normalize(verdict):
    if verdict in ACCEPTING_VERDICTS:
        return "ACCEPTED"
    if verdict == "FAIL":
        return "REJECTED"
    raise HarnessError("UNKNOWN_VERDICT", str(verdict))


def check_corpus_lock(cases):
    """B5: the corpus may not silently shrink. Verify exact counts, the exact
    case-ID set, the exact known-divergence IDs, every required fixture, and
    the SHA256 pins of the corpus-defining files. Runs BEFORE execution."""
    import collections
    lock = load_json(os.path.join(HERE, "corpus_lock.json"))
    cats = collections.Counter(c["category"] for c in cases)
    lanes = collections.Counter(c["lane"] for c in cases)
    want = lock["counts"]
    got = {"total": len(cases), "archive": lanes["archive"],
           "bundle": lanes["bundle"],
           "AGREEMENT_CASE": cats["AGREEMENT_CASE"],
           "SINGLE_IMPLEMENTATION_CASE": cats["SINGLE_IMPLEMENTATION_CASE"],
           "KNOWN_DIVERGENCE_CASE": cats["KNOWN_DIVERGENCE_CASE"]}
    if got != want:
        raise HarnessError("CORPUS_LOCK_COUNT_MISMATCH",
                           "expected %s, got %s" % (want, got))
    ids = sorted(c["case_id"] for c in cases)
    if ids != lock["case_ids"]:
        missing = sorted(set(lock["case_ids"]) - set(ids))
        extra = sorted(set(ids) - set(lock["case_ids"]))
        raise HarnessError("CORPUS_LOCK_ID_MISMATCH",
                           "missing=%s extra=%s" % (missing, extra))
    kd = sorted(c["case_id"] for c in cases
                if c["category"] == "KNOWN_DIVERGENCE_CASE")
    if kd != lock["known_divergence_ids"]:
        raise HarnessError("CORPUS_LOCK_DIVERGENCE_MISMATCH",
                           "expected %s, got %s"
                           % (lock["known_divergence_ids"], kd))
    for req in lock["required_archive_fixtures"] + \
            lock["required_bundle_fixtures"]:
        if req not in ids:
            raise HarnessError("CORPUS_LOCK_FIXTURE_MISSING", req)
    for rel, want_hash in sorted(lock["file_pins"].items()):
        path = os.path.join(HERE, rel)
        with open(path, "rb") as handle:
            got_hash = hashlib.sha256(handle.read()).hexdigest()
        if got_hash != want_hash:
            raise HarnessError("CORPUS_LOCK_FILE_MODIFIED",
                               "%s: %s -> %s" % (rel, want_hash[:12],
                                                 got_hash[:12]))


def validate_corpus(cases):
    """Schema + category/scope contradictions. Runs BEFORE any execution."""
    seen = set()
    for case in cases:
        cid = case.get("case_id")
        if not cid:
            raise HarnessError("SCHEMA_INVALID", "case without case_id")
        if cid in seen:
            raise HarnessError("DUPLICATE_CASE_ID", cid)
        seen.add(cid)
        if case.get("lane") not in VALID_LANES:
            raise HarnessError("SCHEMA_INVALID", "%s: bad lane" % cid)
        cat = case.get("category")
        if cat not in VALID_CATS:
            raise HarnessError("SCHEMA_INVALID", "%s: bad category" % cid)
        ps, rs = case.get("python_scope"), case.get("rust_scope")
        if ps not in VALID_SCOPES or rs not in VALID_SCOPES:
            raise HarnessError("SCHEMA_INVALID", "%s: bad scope" % cid)
        py_in, rs_in = ps == "in_scope", rs == "in_scope"
        if cat == "AGREEMENT_CASE" and not (py_in and rs_in):
            raise HarnessError("CATEGORY_SCOPE_CONTRADICTION",
                               "%s: AGREEMENT needs both in scope" % cid)
        if cat == "SINGLE_IMPLEMENTATION_CASE" and py_in == rs_in:
            raise HarnessError("CATEGORY_SCOPE_CONTRADICTION",
                               "%s: SINGLE needs exactly one in scope" % cid)
        if cat == "UNSUPPORTED_CASE" and (py_in or rs_in):
            raise HarnessError("CATEGORY_SCOPE_CONTRADICTION",
                               "%s: UNSUPPORTED needs neither" % cid)
        if cat == "KNOWN_DIVERGENCE_CASE":
            if not (py_in and rs_in):
                raise HarnessError("CATEGORY_SCOPE_CONTRADICTION",
                                   "%s: KNOWN_DIVERGENCE needs both in "
                                   "scope" % cid)
            dv = case.get("expected_divergence")
            if not isinstance(dv, dict):
                raise HarnessError("SCHEMA_INVALID",
                                   "%s: KNOWN_DIVERGENCE needs "
                                   "expected_divergence" % cid)
            for key in ("python_class", "python_stage", "rust_class",
                        "rust_stage"):
                if not isinstance(dv.get(key), str) or not dv[key]:
                    raise HarnessError("SCHEMA_INVALID",
                                       "%s: expected_divergence.%s "
                                       "missing" % (cid, key))
        if cat != "KNOWN_DIVERGENCE_CASE" and "expected_divergence" in case:
            raise HarnessError("SCHEMA_INVALID",
                               "%s: expected_divergence only allowed on "
                               "KNOWN_DIVERGENCE_CASE" % cid)
        exp = case.get("expected", {})
        if exp.get("normalized_outcome") not in VALID_OUTCOMES:
            raise HarnessError("SCHEMA_INVALID",
                               "%s: bad normalized_outcome" % cid)
        for side, in_scope in (("python", py_in), ("rust", rs_in)):
            if not in_scope:
                continue
            spec = exp.get(side, {})
            for key in ("verdict", "exit_code", "reason_class", "stage"):
                if key not in spec:
                    raise HarnessError("SCHEMA_INVALID",
                                       "%s: %s.%s missing" % (cid, side, key))
            if EXIT_FOR_VERDICT.get(spec["verdict"]) != spec["exit_code"]:
                raise HarnessError(
                    "SCHEMA_INVALID",
                    "%s: %s verdict %s inconsistent with exit %s"
                    % (cid, side, spec["verdict"], spec["exit_code"]))
            # BLOCKER 1: the declared raw verdict must PRODUCE the
            # declared normalized outcome. ACCEPTED with a FAIL verdict
            # (or REJECTED with PASS/INCONCLUSIVE) is a contradiction.
            if normalize(spec["verdict"]) != exp["normalized_outcome"]:
                raise HarnessError(
                    "NORMALIZED_OUTCOME_CONTRADICTION",
                    "%s: %s verdict %s normalizes to %s, declared %s"
                    % (cid, side, spec["verdict"],
                       normalize(spec["verdict"]),
                       exp["normalized_outcome"]))
        if cat == "SINGLE_IMPLEMENTATION_CASE":
            obs_key = "rust_observed" if py_in else "python_observed"
            spec = exp.get(obs_key)
            if not isinstance(spec, dict):
                raise HarnessError("SCHEMA_INVALID",
                                   "%s: missing expected.%s"
                                   % (cid, obs_key))
            for key in ("verdict", "exit_code", "reason_class", "stage"):
                if key not in spec:
                    raise HarnessError("SCHEMA_INVALID",
                                       "%s: expected.%s.%s missing"
                                       % (cid, obs_key, key))
            if EXIT_FOR_VERDICT.get(spec["verdict"]) != spec["exit_code"]:
                raise HarnessError("SCHEMA_INVALID",
                                   "%s: %s verdict/exit inconsistent"
                                   % (cid, obs_key))
        prov = case.get("provenance", {})
        for field in ("source_contract", "reference", "justification"):
            if not prov.get(field):
                raise HarnessError("SCHEMA_INVALID",
                                   "%s: provenance.%s missing/empty"
                                   % (cid, field))


class PythonRunner:
    def bundle(self, target):
        proc = subprocess.run(
            [sys.executable, "-B",
             os.path.join(ROOT, "src", "12_companion_cli_v031",
                          "companion.py"), "verify", "--run", target],
            capture_output=True, text=True, cwd=ROOT,
            timeout=SUBPROCESS_TIMEOUT,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        text = proc.stdout.strip()
        if not text:
            raise HarnessError("PYTHON_STDERR_ONLY_FAILURE",
                               proc.stderr.strip()[:160])
        try:
            out = json.loads(text)
        except ValueError:
            raise HarnessError("PYTHON_MALFORMED_JSON", text[:160])
        if not isinstance(out, dict):
            raise HarnessError("PYTHON_PROTOCOL_INVALID",
                               "expected a JSON object, got %s"
                               % type(out).__name__)
        if out.get("verify_ok") is True:
            verdict, raw = "PASS", out.get("reason", "companion completed")
        else:
            verdict = "FAIL"
            raw = out.get("error", out.get("reason", ""))
        want = EXIT_FOR_VERDICT[verdict]
        if proc.returncode != want:
            raise HarnessError("PYTHON_EXIT_CODE_MISMATCH",
                               "verdict %s -> expected %d, got %d"
                               % (verdict, want, proc.returncode))
        return {"verdict": verdict, "exit_code": proc.returncode,
                "raw": raw, "entry_count": None}

    def archive(self, target):
        sys.path.insert(0, os.path.join(HERE, "oracles"))
        import zipguard_oracle
        res = zipguard_oracle.inspect_archive(target)
        return {"verdict": res["verdict"],
                "exit_code": EXIT_FOR_VERDICT[res["verdict"]],
                "raw": res["reason_code"], "entry_count": res.get("entries")}


class RustRunner:
    def __init__(self, binary):
        self.binary = binary

    def _run(self, subcmd, target):
        try:
            proc = subprocess.run([self.binary, subcmd, target],
                                  capture_output=True, text=True,
                                  timeout=SUBPROCESS_TIMEOUT)
        except PermissionError as err:
            raise HarnessError("RUST_BIN_NOT_EXECUTABLE", str(err))
        except OSError as err:
            raise HarnessError("RUST_BIN_UNUSABLE", str(err))
        text = proc.stdout.strip()
        if not text:
            raise HarnessError("RUST_STDERR_ONLY_FAILURE",
                               proc.stderr.strip()[:160])
        try:
            out = json.loads(text)
        except ValueError:
            raise HarnessError("RUST_MALFORMED_JSON", text[:160])
        if not isinstance(out, dict):
            raise HarnessError("RUST_PROTOCOL_INVALID",
                               "expected a JSON object, got %s"
                               % type(out).__name__)
        if out.get("verifier") != RUST_VERIFIER_NAME:
            raise HarnessError("RUST_IDENTITY_MISMATCH",
                               str(out.get("verifier")))
        if out.get("version") != RUST_VERSION_REQUIRED:
            raise HarnessError("RUST_VERSION_MISMATCH",
                               "%s != %s" % (out.get("version"),
                                             RUST_VERSION_REQUIRED))
        verdict = out.get("verdict")
        want = EXIT_FOR_VERDICT.get(verdict)
        if want is None:
            raise HarnessError("RUST_UNKNOWN_VERDICT", str(verdict))
        if proc.returncode != want:
            raise HarnessError("RUST_EXIT_CODE_MISMATCH",
                               "verdict %s -> expected %d, got %d"
                               % (verdict, want, proc.returncode))
        return {"verdict": verdict, "exit_code": proc.returncode,
                "raw": out.get("reason_code", ""),
                "entry_count": out.get("entry_count")}

    def bundle(self, target):
        return self._run("verify", target)

    def archive(self, target):
        return self._run("inspect-archive", target)


def _check_side(cid, side, res, spec, mapper, table, outcome):
    cls, stage = mapper.map(table, res["raw"])
    up = side.upper()
    # BLOCKER 1: actual raw behaviour must normalize to the declared
    # outcome, not merely match a reason class.
    if normalize(res["verdict"]) != outcome:
        raise HarnessError("NORMALIZED_OUTCOME_DISAGREE",
                           "%s: %s verdict %s normalizes to %s, expected %s"
                           % (cid, side, res["verdict"],
                              normalize(res["verdict"]), outcome))
    if res["verdict"] != spec["verdict"]:
        raise HarnessError("EXPECTED_%s_VERDICT_DISAGREE" % up,
                           "%s: expected %s, got %s"
                           % (cid, spec["verdict"], res["verdict"]))
    if res["exit_code"] != spec["exit_code"]:
        raise HarnessError("EXPECTED_%s_EXIT_DISAGREE" % up,
                           "%s: expected %s, got %s"
                           % (cid, spec["exit_code"], res["exit_code"]))
    if cls != spec["reason_class"]:
        raise HarnessError("EXPECTED_%s_CLASS_DISAGREE" % up,
                           "%s: expected %s, got %s (%r)"
                           % (cid, spec["reason_class"], cls, res["raw"]))
    if stage != spec["stage"]:
        raise HarnessError("EXPECTED_%s_STAGE_DISAGREE" % up,
                           "%s: expected %s, got %s"
                           % (cid, spec["stage"], stage))
    return cls, stage


def compare_case(case, mapper, py_runner, rs_runner, paths):
    lane = case["lane"]
    cid = case["case_id"]
    table_py = "python_bundle" if lane == "bundle" else "archive"
    table_rs = "rust_bundle" if lane == "bundle" else "archive"
    py_in = case["python_scope"] == "in_scope"
    rs_in = case["rust_scope"] == "in_scope"
    exp = case["expected"]
    target = paths[cid]

    rec = {"case_id": cid, "lane": lane, "category": case["category"],
           "expected_normalized_outcome": exp["normalized_outcome"],
           "python_scope": case["python_scope"],
           "rust_scope": case["rust_scope"]}

    def run(runner):
        return runner.bundle(target) if lane == "bundle" \
            else runner.archive(target)

    py_res = None
    if py_in:
        py_res = run(py_runner)
        cls, stage = _check_side(cid, "python", py_res, exp["python"],
                                 mapper, table_py,
                                 exp["normalized_outcome"])
        rec.update(python_verdict=py_res["verdict"],
                   python_exit=py_res["exit_code"], python_raw=py_res["raw"],
                   python_class=cls, python_stage=stage,
                   python_entry_count=py_res["entry_count"])
        if lane == "archive" and py_res["verdict"] == "INCONCLUSIVE":
            want = exp.get("entry_count")
            if want is not None and py_res["entry_count"] != want:
                raise HarnessError("ENTRY_COUNT_PYTHON_DISAGREE",
                                   "%s: expected %s, got %s"
                                   % (cid, want, py_res["entry_count"]))
    else:
        rec["python_class"] = "OUT_OF_SCOPE"
        # BLOCKER 3: observations are MAPPED and STAGE-CHECKED, symmetric
        # with the Rust side. An out-of-scope implementation that rejects
        # at an earlier SHARED stage means the case is not isolated.
        obs = run(py_runner)
        ocls, ostage = mapper.map(table_py, obs["raw"])
        rec["python_observed"] = {
            "verdict": obs["verdict"],
            "exit_code": obs["exit_code"],
            "raw_reason": obs["raw"],
            "mapped_reason_class": ocls,
            "stage": ostage,
            "normalized_outcome": normalize(obs["verdict"]),
        }
        if case["category"] == "SINGLE_IMPLEMENTATION_CASE" \
                and obs["verdict"] == "FAIL" and ostage in SHARED_STAGES:
            raise HarnessError(
                "CAPABILITY_GAP_CASE_NOT_ISOLATED",
                "%s: out-of-scope Python rejected at shared stage %r (%s)"
                % (cid, ostage, ocls))
        want = exp.get("python_observed")
        if want is not None:
            if (obs["verdict"] != want["verdict"]
                    or obs["exit_code"] != want["exit_code"]
                    or ocls != want["reason_class"]
                    or ostage != want["stage"]):
                raise HarnessError(
                    "OBSERVATION_DISAGREE",
                    "%s: python observation expected %s/%s/%s/%s, got "
                    "%s/%s/%s/%s"
                    % (cid, want["verdict"], want["exit_code"],
                       want["reason_class"], want["stage"], obs["verdict"],
                       obs["exit_code"], ocls, ostage))

    if rs_in:
        if rs_runner is None:
            rec["rust_class"] = "TOOLCHAIN_UNAVAILABLE"
        else:
            rs_res = run(rs_runner)
            cls, stage = _check_side(cid, "rust", rs_res, exp["rust"],
                                     mapper, table_rs,
                                     exp["normalized_outcome"])
            rec.update(rust_verdict=rs_res["verdict"],
                       rust_exit=rs_res["exit_code"], rust_raw=rs_res["raw"],
                       rust_class=cls, rust_stage=stage,
                       rust_entry_count=rs_res["entry_count"])
            if lane == "archive" and rs_res["verdict"] == "INCONCLUSIVE":
                if not isinstance(rs_res["entry_count"], int):
                    raise HarnessError("MISSING_RUST_ENTRY_COUNT", cid)
                want = exp.get("entry_count")
                if want is not None and rs_res["entry_count"] != want:
                    raise HarnessError("ENTRY_COUNT_RUST_DISAGREE",
                                       "%s: expected %s, got %s"
                                       % (cid, want, rs_res["entry_count"]))
    else:
        rec["rust_class"] = "OUT_OF_SCOPE"
        if rs_runner is not None:
            # never silently accept ERROR: a failing observation is a
            # harness failure, not a shrug.
            obs = run(rs_runner)
            ocls, ostage = mapper.map(table_rs, obs["raw"])
            rec["rust_observed"] = {
                "verdict": obs["verdict"],
                "exit_code": obs["exit_code"],
                "raw_reason": obs["raw"],
                "mapped_reason_class": ocls,
                "stage": ostage,
                "normalized_outcome": normalize(obs["verdict"]),
            }
            if case["category"] == "SINGLE_IMPLEMENTATION_CASE" \
                    and obs["verdict"] == "FAIL" and ostage in SHARED_STAGES:
                raise HarnessError(
                    "CAPABILITY_GAP_CASE_NOT_ISOLATED",
                    "%s: out-of-scope Rust rejected at shared stage %r (%s)"
                    % (cid, ostage, ocls))
            want = exp.get("rust_observed")
            if want is not None:
                if (obs["verdict"] != want["verdict"]
                        or obs["exit_code"] != want["exit_code"]
                        or ocls != want["reason_class"]
                        or ostage != want["stage"]):
                    raise HarnessError(
                        "OBSERVATION_DISAGREE",
                        "%s: rust observation expected %s/%s/%s/%s, got "
                        "%s/%s/%s/%s"
                        % (cid, want["verdict"], want["exit_code"],
                           want["reason_class"], want["stage"],
                           obs["verdict"], obs["exit_code"], ocls, ostage))

    if py_in and rs_in and rs_runner is not None:
        classes_differ = rec["python_class"] != rec["rust_class"]
        stages_differ = rec["python_stage"] != rec["rust_stage"]
        rec["divergent"] = bool(classes_differ or stages_differ)

        if case["category"] == "KNOWN_DIVERGENCE_CASE":
            # A documented divergence is REPORTED. It is NEVER agreement,
            # and it can never produce PASS (see main()). It must match the
            # declaration exactly; anything else is an undeclared drift.
            want = case["expected_divergence"]
            if not rec["divergent"]:
                raise HarnessError(
                    "DECLARED_DIVERGENCE_NOT_OBSERVED",
                    "%s: declared a divergence but the implementations "
                    "agreed" % cid)
            if (rec["python_class"] != want["python_class"]
                    or rec["rust_class"] != want["rust_class"]
                    or rec["python_stage"] != want["python_stage"]
                    or rec["rust_stage"] != want["rust_stage"]):
                raise HarnessError(
                    "UNDECLARED_DIVERGENCE",
                    "%s: observed py=%s/%s rust=%s/%s, declared differs"
                    % (cid, rec["python_class"], rec["python_stage"],
                       rec["rust_class"], rec["rust_stage"]))
        else:
            if classes_differ:
                raise HarnessError("PYTHON_RUST_CLASS_DISAGREE",
                                   "%s: python %s, rust %s"
                                   % (cid, rec["python_class"],
                                      rec["rust_class"]))
            if stages_differ:
                raise HarnessError("PYTHON_RUST_STAGE_DISAGREE",
                                   "%s: python %s, rust %s"
                                   % (cid, rec["python_stage"],
                                      rec["rust_stage"]))
        if lane == "archive" and rec.get("python_entry_count") is not None:
            if rec["python_entry_count"] != rec.get("rust_entry_count"):
                raise HarnessError("PYTHON_RUST_ENTRY_COUNT_DISAGREE",
                                   "%s: python %s, rust %s"
                                   % (cid, rec["python_entry_count"],
                                      rec.get("rust_entry_count")))
    return rec


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_paths(cases, workdir, real_paths):
    sys.path.insert(0, os.path.join(HERE, "corpus"))
    import build_archives
    arch_dir = os.path.join(workdir, "archives")
    build_archives.write_corpus(arch_dir)

    freeze = os.path.join(ROOT, "freeze_record",
                          "python_behaviour_freeze_v01")
    sys.path.insert(0, freeze)
    import generate_failure_cases as gen
    bundle_dir = os.path.join(workdir, "bundles")
    os.makedirs(bundle_dir)
    ref = os.path.join(freeze, "reference_bundle")
    gen.generate(ref, bundle_dir)
    import build_bundle_cases
    build_bundle_cases.build(ref, bundle_dir)

    paths = {}
    for case in cases:
        cid = case["case_id"]
        if case["lane"] == "bundle":
            paths[cid] = os.path.join(bundle_dir, cid)
        elif case.get("real_archive_key"):
            key = case["real_archive_key"]
            supplied = real_paths.get(key)
            if not supplied or not os.path.isfile(supplied):
                raise HarnessError("REQUIRED_CORPUS_UNAVAILABLE",
                                   "%s (supply --%s)"
                                   % (cid, key.replace("_", "-")))
            got = sha256_file(supplied)
            want = case["expected_sha256"]
            if got != want:
                raise HarnessError("REAL_CORPUS_HASH_MISMATCH",
                                   "%s: expected %s..., got %s..."
                                   % (cid, want[:16], got[:16]))
            paths[cid] = supplied
        else:
            paths[cid] = os.path.join(arch_dir, case["archive_file"])
    return paths


def canonical(results):
    return json.dumps(results, sort_keys=True, separators=(",", ":"))


def run_once(cases, mapper, py_runner, rs_runner, paths, order):
    ordered = list(cases)
    if order == "reversed":
        ordered = list(reversed(ordered))
    elif order == "shuffled":
        ordered = sorted(ordered, key=lambda c: hashlib.sha256(
            c["case_id"].encode()).hexdigest())
    out = [compare_case(c, mapper, py_runner, rs_runner, paths)
           for c in ordered]
    out.sort(key=lambda r: (r["lane"], r["case_id"]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--order", choices=("original", "reversed", "shuffled"),
                    default="original",
                    help="execute the corpus ONCE in this order. The "
                         "checker launches three processes, one per order, "
                         "and compares the complete canonical responses.")
    ap.add_argument("--rust-bin", default=None)
    ap.add_argument("--real-v20", default=None)
    ap.add_argument("--real-705", default=None)
    ap.add_argument("--real-move78", default=None)
    args = ap.parse_args()

    mapper = ReasonMapper(load_json(os.path.join(HERE, "reason_map.json")))
    cases = (load_json(os.path.join(HERE, "corpus", "bundle_cases.json"))
             ["cases"]
             + load_json(os.path.join(HERE, "corpus", "archive_cases.json"))
             ["cases"])

    default_v20 = os.path.join(
        ROOT, "releases", "roadmap_one_complete", "move_70_final",
        "Project_Witness_WORKING_STACK_v20_MOVE_70.zip")
    real_paths = {
        "real_v20": args.real_v20
        or (default_v20 if os.path.isfile(default_v20) else None),
        "real_705": args.real_705,
        "real_move78": args.real_move78,
    }

    rs_runner = None
    if args.rust_bin:
        if not os.path.isfile(args.rust_bin):
            print(json.dumps({"overall_status": "USAGE",
                              "reason_code": "RUST_BIN_NOT_FOUND",
                              "detail": args.rust_bin}, indent=1,
                             sort_keys=True))
            return EXIT_STATUS["USAGE"]
        # B5: an existing but NON-EXECUTABLE file produced an uncaught
        # PermissionError (traceback, exit 0). Check the bit up front and
        # guard the subprocess call as well.
        if not os.access(args.rust_bin, os.X_OK):
            print(json.dumps({"overall_status": "USAGE",
                              "reason_code": "RUST_BIN_NOT_EXECUTABLE",
                              "detail": args.rust_bin}, indent=1,
                             sort_keys=True))
            return EXIT_STATUS["USAGE"]
        rs_runner = RustRunner(args.rust_bin)
    py_runner = PythonRunner()

    with tempfile.TemporaryDirectory(prefix="move79_") as workdir:
        try:
            check_corpus_lock(cases)
            validate_corpus(cases)
            paths = prepare_paths(cases, workdir, real_paths)
            # B2: exactly ONE corpus pass per process, in the selected
            # order. Determinism across orders/processes is verified by the
            # checker comparing the three complete canonical responses -
            # NOT by re-running the corpus six times inside every process.
            results = run_once(cases, mapper, py_runner, rs_runner, paths,
                               args.order)
        except HarnessError as err:
            status = "INCONCLUSIVE" \
                if err.code == "REQUIRED_CORPUS_UNAVAILABLE" else "FAIL"
            print(json.dumps({"overall_status": status,
                              "reason_code": err.code,
                              "detail": err.detail}, indent=1,
                             sort_keys=True))
            return EXIT_STATUS[status]
        except subprocess.TimeoutExpired:
            print(json.dumps({"overall_status": "FAIL",
                              "reason_code": "IMPLEMENTATION_TIMEOUT"},
                             indent=1))
            return EXIT_STATUS["FAIL"]

    rust_ran = rs_runner is not None

    shared = [r for r in results if r["category"] == "AGREEMENT_CASE"]
    known_div = [r for r in results
                 if r["category"] == "KNOWN_DIVERGENCE_CASE"]
    single = [r for r in results
              if r["category"] == "SINGLE_IMPLEMENTATION_CASE"]
    unsupported = [r for r in results if r["category"] == "UNSUPPORTED_CASE"]
    py_only = [r for r in single if r["python_scope"] == "in_scope"]
    rs_only = [r for r in single if r["rust_scope"] == "in_scope"]

    # B1: divergences are COMPUTED from the records, never hardcoded.
    divergent = [r for r in results if r.get("divergent")]

    summary = {
        "shared_cases_declared": len(shared),
        "shared_cases_executed": len(shared) if rust_ran else 0,
        "shared_agreement_cases_passed": len(shared) if rust_ran else 0,
        "known_divergence_cases_declared": len(known_div),
        "known_divergence_cases_executed": len(known_div) if rust_ran else 0,
        "python_only_cases_declared": len(py_only),
        "python_only_cases_executed": len(py_only),
        "python_only_cases_passed": len(py_only),
        "rust_only_cases_declared": len(rs_only),
        "rust_only_cases_executed": len(rs_only) if rust_ran else 0,
        "rust_only_cases_passed": len(rs_only) if rust_ran else 0,
        "unsupported_cases": len(unsupported),
        "capability_gaps": {
            "python_only": sorted(r["case_id"] for r in py_only),
            "rust_only": sorted(r["case_id"] for r in rs_only),
        },
        "divergences": len(divergent),
        "divergent_cases": sorted(r["case_id"] for r in divergent),
        "unmapped_reasons": 0,
        "missing_diagnostics": 0,
        "total_cases": len(results),
        "python_lane_validated": True,
        "rust_lane_validated": rust_ran,
    }

    if not rust_ran:
        status = {"overall_status": "INCONCLUSIVE",
                  "reason_code": "RUST_TOOLCHAIN_UNAVAILABLE",
                  "note": "Rust lane NOT executed: no shared-agreement, "
                          "known-divergence or rust-only case has been "
                          "evaluated. Supply --rust-bin.",
                  "summary": summary}
    elif divergent:
        # B1: a confirmed in-scope divergence can NEVER produce PASS and can
        # never yield a global agreement reason code.
        status = {"overall_status": "FAIL",
                  "reason_code": "BEHAVIOURAL_DIVERGENCE_DETECTED",
                  "note": "%d in-scope divergence(s) observed: %s. Documented "
                          "divergences are reported, never counted as "
                          "agreement." % (len(divergent),
                                          ", ".join(sorted(r["case_id"]
                                                           for r in divergent))),
                  "summary": summary}
    else:
        status = {"overall_status": "PASS",
                  "reason_code":
                      "IN_SCOPE_AGREEMENT_CONFIRMED_WITH_CAPABILITY_GAPS"
                      if single else "IN_SCOPE_AGREEMENT_CONFIRMED",
                  "summary": summary}
    status["results"] = results
    # execution-order metadata is NON-semantic: the checker
    # compares the semantic response, and the order field is
    # excluded by an explicit, documented normalization rule.
    status["execution_order"] = args.order
    print(json.dumps(status, indent=1, sort_keys=True))
    return EXIT_STATUS[status["overall_status"]]


if __name__ == "__main__":
    sys.exit(main())
