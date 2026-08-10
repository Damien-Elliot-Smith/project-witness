#!/usr/bin/env python3
"""Move 84 — tamper-and-detect demonstration driver.

Demonstrates what the ADOPTED verifier genuinely does, including what it
does not detect. Every value in the transcript comes from executing the
adopted binaries; nothing is narrated, predicted or hand-declared.

Two modes:

* `establish` runs every case against an ADOPTED-AUTHORITY verifier —
  freshly built by the gate from a privately extracted, hash-verified copy
  of the adopted artifact — and records the exact stdout bytes, stderr
  bytes and exit code as the expectation.
* `demonstrate` runs the same cases against the candidate's verifier,
  compares byte-for-byte against those established expectations, and emits
  the transcript. It **fails closed**: exit 0 means only that every
  expected observation was genuinely reproduced.

Exit 0 does NOT mean the tested bundle is universally valid, that the Rust
verifier detects every tamper, or that it produced PASS. It cannot produce
PASS: it has no reachable PASS path.

Determinism: the transcript carries no timestamps, no hostnames, no
absolute paths and no durations. Bundles are named by case id and mutated
files by their path relative to the bundle root.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys

RUN_TIMEOUT_SECONDS = 300

# The adopted Rust verdict vocabulary. PASS is absent on purpose.
RUST_REACHABLE_VERDICTS = ("FAIL", "INCONCLUSIVE")

CASE_MEANING = {
    "clean": (
        "An unmodified bundle. The Python lane accepts it. The adopted "
        "Rust verifier reports INCONCLUSIVE with exit 3; that is its "
        "honest clean-bundle ceiling and is NOT a pass."),
    "toplevel_tamper": (
        "One byte flipped in a TOP-LEVEL declared file. This file set is "
        "covered by the adopted Rust hash stage; the Rust verifier "
        "detects the tamper and reports the exact reason below."),
    "nested_evidence_tamper": (
        "One byte flipped in the genuine nested evidence payload. The "
        "Python lane detects it. The adopted Rust verifier DOES NOT: it "
        "verifies top-level declared hashes only, so its output here is "
        "indistinguishable from the clean bundle. This is a real and "
        "currently unrepaired limit of the Rust lane."),
}


class DemoError(Exception):
    """Deterministic, message-only failure."""


def run_capture(argv):
    proc = subprocess.run(argv, capture_output=True,
                          timeout=RUN_TIMEOUT_SECONDS)
    return proc.returncode, proc.stdout, proc.stderr


def observe(case, rust_bin, python_bin, companion):
    """Execute BOTH lanes for one case and record exactly what happened."""
    root = case["root"]
    rust_rc, rust_out, rust_err = run_capture([rust_bin, "verify", root])
    py_rc, py_out, py_err = run_capture(
        [python_bin, "-B", companion, "verify", "--run", root])
    return {
        "case_id": case["case_id"],
        "rust": {"exit_code": rust_rc,
                 "stdout": rust_out.decode("utf-8", "replace"),
                 "stderr_bytes": len(rust_err)},
        "python": {"exit_code": py_rc,
                   "stdout": py_out.decode("utf-8", "replace"),
                   "stderr_bytes": len(py_err)},
    }


def _field(stdout_text, key):
    try:
        return json.loads(stdout_text.strip()).get(key)
    except (ValueError, AttributeError):
        return None


def check_observation(observation):
    """Invariants that hold regardless of which reasons are observed."""
    problems = []
    case_id = observation["case_id"]
    rust = observation["rust"]
    python_lane = observation["python"]

    if rust["stderr_bytes"]:
        problems.append("%s: the Rust lane emitted stderr" % case_id)
    if python_lane["stderr_bytes"]:
        problems.append("%s: the Python lane emitted stderr" % case_id)

    verdict = _field(rust["stdout"], "verdict")
    if verdict == "PASS" or rust["exit_code"] == 0:
        problems.append(
            "%s: the Rust lane reported a pass; the adopted verifier has "
            "no reachable PASS path" % case_id)
    elif verdict not in RUST_REACHABLE_VERDICTS:
        problems.append("%s: Rust verdict %r is not reachable"
                        % (case_id, verdict))
    if verdict == "FAIL" and rust["exit_code"] != 1:
        problems.append("%s: Rust FAIL must exit 1" % case_id)
    if verdict == "INCONCLUSIVE" and rust["exit_code"] != 3:
        problems.append("%s: Rust INCONCLUSIVE must exit 3" % case_id)
    return problems


def check_demonstration(observations):
    """The three case-specific facts this demonstration exists to show."""
    problems = []
    by_id = {o["case_id"]: o for o in observations}
    for required in ("clean", "toplevel_tamper", "nested_evidence_tamper"):
        if required not in by_id:
            problems.append("missing demonstration case: %s" % required)
    if problems:
        return problems

    clean = by_id["clean"]
    top = by_id["toplevel_tamper"]
    nested = by_id["nested_evidence_tamper"]

    # 1. clean: Python accepts, Rust is INCONCLUSIVE and never PASS
    if clean["python"]["exit_code"] != 0:
        problems.append("clean: the Python lane did not accept the "
                        "unmodified bundle")
    if _field(clean["rust"]["stdout"], "verdict") != "INCONCLUSIVE":
        problems.append("clean: the Rust lane is not INCONCLUSIVE")

    # 2. top-level tamper: Rust genuinely DETECTS it
    if _field(top["rust"]["stdout"], "verdict") != "FAIL":
        problems.append(
            "toplevel_tamper: the Rust lane did not detect a tamper to a "
            "top-level declared file")
    if top["rust"]["stdout"] == clean["rust"]["stdout"]:
        problems.append(
            "toplevel_tamper: the Rust output is identical to clean, so "
            "no detection was demonstrated")

    # 3. nested evidence tamper: Python detects, Rust does NOT
    if nested["python"]["exit_code"] == 0:
        problems.append(
            "nested_evidence_tamper: the Python lane failed to detect the "
            "nested evidence modification")
    if _field(nested["rust"]["stdout"], "verdict") != "INCONCLUSIVE":
        problems.append(
            "nested_evidence_tamper: the Rust lane is not INCONCLUSIVE; "
            "the documented limitation is not what was observed")
    if nested["rust"]["stdout"] != clean["rust"]["stdout"]:
        problems.append(
            "nested_evidence_tamper: the Rust output differs from clean, "
            "so the blindness this case documents was not observed")
    return problems


def compare_to_authority(observed, expected):
    """Byte-for-byte against the adopted authority."""
    problems = []
    by_id = {o["case_id"]: o for o in expected}
    for observation in observed:
        case_id = observation["case_id"]
        authority = by_id.get(case_id)
        if authority is None:
            problems.append("%s: no adopted-authority expectation" % case_id)
            continue
        for lane in ("rust", "python"):
            for field in ("exit_code", "stdout", "stderr_bytes"):
                if observation[lane][field] != authority[lane][field]:
                    problems.append(
                        "%s: %s %s differs from the adopted authority"
                        % (case_id, lane, field))
    missing = sorted(set(by_id) - {o["case_id"] for o in observed})
    for case_id in missing:
        problems.append("%s: expected by the authority but not observed"
                        % case_id)
    return problems


def render_transcript(observations, cases):
    """Deterministic transcript. No time, host or absolute path appears."""
    mutations = {c["case_id"]: c.get("mutation") for c in cases}
    lines = []
    add = lines.append
    add("PROJECT WITNESS -- MOVE 84 TAMPER-AND-DETECT DEMONSTRATION")
    add("=" * 70)
    add("")
    add("Every value below was produced by executing the adopted")
    add("verifiers. Nothing is narrated or predicted.")
    add("")
    add("The adopted Rust verifier has NO reachable PASS path. Its best")
    add("outcome for a clean bundle is INCONCLUSIVE with exit 3. That is")
    add("an honest ceiling and is never a pass.")
    add("")
    for observation in observations:
        case_id = observation["case_id"]
        add("-" * 70)
        add("CASE: %s" % case_id)
        add("")
        for chunk in CASE_MEANING[case_id].split(". "):
            text = chunk.strip().rstrip(".")
            if text:
                add("  %s." % text)
        mutation = mutations.get(case_id)
        add("")
        if mutation is None:
            add("  mutation           (none)")
        else:
            add("  mutated file       %s" % mutation["path"])
            add("  mutation           byte %d xor 0x%02x (0x%02x -> 0x%02x)"
                % (mutation["offset"], mutation["operand"],
                   mutation["byte_before"], mutation["byte_after"]))
        add("")
        rust = observation["rust"]
        python_lane = observation["python"]
        add("  PYTHON lane")
        add("    exit code        %d" % python_lane["exit_code"])
        add("    stdout           %s" % python_lane["stdout"].strip())
        add("    verdict          %s"
            % ("PASS" if python_lane["exit_code"] == 0 else "FAIL"))
        add("")
        add("  RUST lane (adopted witness-verify)")
        add("    exit code        %d" % rust["exit_code"])
        add("    stdout           %s" % rust["stdout"].strip())
        add("    verdict          %s"
            % (_field(rust["stdout"], "verdict") or "(unreadable)"))
        add("    reason code      %s"
            % (_field(rust["stdout"], "reason_code") or "(unreadable)"))
        add("")
    add("-" * 70)
    add("WHAT THIS DEMONSTRATION ESTABLISHES")
    add("")
    add("  The Rust verifier detects a tamper to a TOP-LEVEL declared")
    add("  file and reports an exact reason code for it.")
    add("")
    add("  The Rust verifier does NOT detect a tamper to the nested")
    add("  evidence payload. Its output there is identical to the clean")
    add("  bundle. The Python lane does detect it.")
    add("")
    add("WHAT IT DOES NOT ESTABLISH")
    add("")
    add("  That the tested bundle is universally valid.")
    add("  That the Rust verifier detects every tamper.")
    add("  That the Rust verifier produced a pass. It cannot.")
    add("")
    return "\n".join(lines) + "\n"


def load_cases(manifest_path):
    with open(manifest_path, encoding="utf-8") as handle:
        return json.load(handle)["cases"]


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Move 84 tamper-and-detect demonstration")
    parser.add_argument("--mode", required=True,
                        choices=("establish", "demonstrate"))
    parser.add_argument("--verifier", required=True)
    parser.add_argument("--python-bin", required=True)
    parser.add_argument("--companion", required=True)
    parser.add_argument("--fixtures", required=True)
    parser.add_argument("--expectations", default=None)
    parser.add_argument("--expectations-out", default=None)
    parser.add_argument("--transcript-out", default=None)
    args = parser.parse_args(argv)

    for label, path in (("--verifier", args.verifier),
                        ("--python-bin", args.python_bin),
                        ("--companion", args.companion),
                        ("--fixtures", args.fixtures)):
        if not os.path.isabs(path) or not os.path.exists(path):
            print("usage error: %s must be an absolute existing path"
                  % label)
            return 2

    try:
        cases = load_cases(args.fixtures)
    except (OSError, ValueError, KeyError) as exc:
        print("DEMO: FAIL (fixture manifest unreadable: %s)" % exc)
        return 1

    observations = [observe(case, args.verifier, args.python_bin,
                            args.companion) for case in cases]

    problems = []
    for observation in observations:
        problems.extend(check_observation(observation))
    problems.extend(check_demonstration(observations))

    if args.mode == "establish":
        if problems:
            for problem in sorted(set(problems)):
                print("DEMO_PROBLEM: %s" % problem)
            print("DEMO_AUTHORITY: FAIL (%d problem(s))"
                  % len(set(problems)))
            return 1
        payload = {"observations": observations}
        if args.expectations_out:
            if not os.path.isabs(args.expectations_out):
                print("usage error: --expectations-out must be absolute")
                return 2
            with open(args.expectations_out, "wb") as handle:
                handle.write((json.dumps(payload, sort_keys=True,
                                         separators=(",", ":"),
                                         ensure_ascii=False)
                              + "\n").encode("utf-8"))
        for observation in observations:
            print("DEMO_AUTHORITY: %-24s rust exit %d, python exit %d"
                  % (observation["case_id"],
                     observation["rust"]["exit_code"],
                     observation["python"]["exit_code"]))
        print("DEMO_AUTHORITY: PASS (%d case(s))" % len(observations))
        return 0

    # demonstrate
    if not args.expectations or not os.path.isabs(args.expectations):
        print("usage error: --expectations must be an absolute path")
        return 2
    try:
        with open(args.expectations, encoding="utf-8") as handle:
            expected = json.load(handle)["observations"]
    except (OSError, ValueError, KeyError) as exc:
        print("DEMO: FAIL (expectations unreadable: %s)" % exc)
        return 1
    problems.extend(compare_to_authority(observations, expected))

    transcript = render_transcript(observations, cases)
    if args.transcript_out:
        if not os.path.isabs(args.transcript_out):
            print("usage error: --transcript-out must be absolute")
            return 2
        with open(args.transcript_out, "wb") as handle:
            handle.write(transcript.encode("utf-8"))
    sys.stdout.write(transcript)

    for problem in sorted(set(problems)):
        print("DEMO_PROBLEM: %s" % problem)
    if problems:
        print("MOVE_84_DEMO: FAIL (%d problem(s))" % len(set(problems)))
        return 1
    print("MOVE_84_DEMO: PASS (%d case(s) reproduced exactly)"
          % len(observations))
    return 0


if __name__ == "__main__":
    sys.exit(main())
