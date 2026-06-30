#!/usr/bin/env python3
"""Project Witness Connected Demo v0.1.

A thin, deterministic orchestrator that runs the top-level Project Witness chain
end to end and records the terminal statuses:

  DEMO_COMPLETED, COMPANION_COMPLETED, WORKFLOW_COMPLETED, ATLAS_VALIDATED,
  SOURCE_VERIFIED, STACK_VERIFIED, STACK_SELFCHECK_PASSED

It drives the frozen Companion v0.3.1, Unified Case Manifest v0.1, Stack Verifier
v0.1, and Stack Selfcheck v0.1.2 CLIs (Companion in turn drives Coordinator
v0.3.2 and the lower stack). It is standard-library only. It does not modify any
frozen component, does not copy evidence contents, and does not prove truth: it
only records the statuses the frozen components already report.

Subcommands:
  run        -- run the real chain and write a connected demo report
  verify     -- verify a connected demo output folder
  selfcheck  -- run in-process self-checks (no subprocess, no frozen components)
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from connected_demo_lib import canonical, engine
from connected_demo_lib.canonical import DemoError
from connected_demo_lib.runners import RealRunner, FixtureRunner

_ROOT_KEYS = ("companion", "coordinator", "atlas_registry", "sentinel",
              "histor_lite", "aletheia", "bridge", "odin", "histor_aletheia",
              "histor_odin", "case_bundle_v02", "unified_manifest",
              "stack_verifier", "stack_selfcheck")


def cmd_run(args):
    roots = {k: getattr(args, k + "_root") for k in _ROOT_KEYS}
    params = {
        "case_id": args.case_id, "evidence_id": args.evidence_id,
        "evidence_file": args.evidence_file, "allowed_root": args.allowed_root,
        "case_directory_name": args.case_directory_name, "inventory": args.inventory,
    }
    try:
        report = engine.run_demo(params, RealRunner(roots), args.out)
    except DemoError as exc:
        print(json.dumps({"demo_status": canonical.DEMO_FAILED, "error": str(exc)},
                         sort_keys=True))
        return 1
    print(json.dumps({"demo_status": report["demo_status"], "out": args.out},
                     sort_keys=True))
    return 0 if report["demo_status"] == canonical.DEMO_COMPLETED else 1


def cmd_verify(args):
    path = os.path.join(args.run, engine.REPORT_FILE)
    if not os.path.isfile(path):
        print(json.dumps({"verify_ok": False, "error": "missing report"}, sort_keys=True))
        return 1
    report = canonical.load_json(path)
    ok = report.get("demo_status") == canonical.DEMO_COMPLETED and all(
        report.get("observed_statuses", {}).get(k) == v
        for k, v in canonical.REQUIRED.items())
    print(json.dumps({"verify_ok": bool(ok),
                      "demo_status": report.get("demo_status")}, sort_keys=True))
    return 0 if ok else 1


def cmd_selfcheck(args):
    import tempfile
    failures = []
    # honest fixture chain reaches DEMO_COMPLETED
    work = tempfile.mkdtemp(prefix="demo_selfcheck_")
    params = {"case_id": "C", "evidence_id": "E", "evidence_file": "x",
              "allowed_root": "x", "case_directory_name": "c", "inventory": "x"}
    rep = engine.run_demo(params, FixtureRunner(honest=True), os.path.join(work, "ok"))
    if rep["demo_status"] != canonical.DEMO_COMPLETED:
        failures.append("honest fixture did not reach DEMO_COMPLETED")
    # a failing stage short-circuits to DEMO_FAILED
    rep2 = engine.run_demo(params, FixtureRunner(honest=False), os.path.join(work, "bad"))
    if rep2["demo_status"] != canonical.DEMO_FAILED:
        failures.append("dishonest fixture did not fail")
    for f in failures:
        print("FAIL  " + f)
    if failures:
        return 1
    print("selfcheck: all gates passed")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description="Project Witness Connected Demo v0.1")
    sub = parser.add_subparsers(dest="command")
    run = sub.add_parser("run", help="run the real chain")
    for k in _ROOT_KEYS:
        run.add_argument("--" + k.replace("_", "-") + "-root", required=True)
    run.add_argument("--case-id", required=True)
    run.add_argument("--evidence-id", required=True)
    run.add_argument("--evidence-file", required=True)
    run.add_argument("--allowed-root", required=True)
    run.add_argument("--case-directory-name", required=True)
    run.add_argument("--inventory", required=True)
    run.add_argument("--out", required=True)
    run.set_defaults(func=cmd_run)
    ver = sub.add_parser("verify", help="verify a demo output")
    ver.add_argument("--run", required=True)
    ver.set_defaults(func=cmd_verify)
    sc = sub.add_parser("selfcheck", help="in-process self-checks")
    sc.set_defaults(func=cmd_selfcheck)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not getattr(args, "func", None):
        build_parser().print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
