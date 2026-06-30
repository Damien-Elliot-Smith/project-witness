#!/usr/bin/env python3
"""Coordinator Workflow v0.3 command-line interface.

Subcommands:
  run       -- run the one-case evidence-and-reasoning workflow with Atlas validation
  verify    -- verify a Coordinator v0.3 output folder
  selfcheck -- run small in-process self-checks

At runtime, lower components are called via subprocess (manual integration). The
default unit tests inject in-process fake runners and spawn no subprocesses.
Atlas validation is in-process and read-only.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coordinator_v03_lib import workflow, verifier, canonical
from coordinator_v03_lib.component_runners import SubprocessComponentRunner


def cmd_run(args):
    request = canonical.load_json(args.request)
    roots = request.get("component_roots", {})
    runner = SubprocessComponentRunner(roots)
    try:
        outcome = workflow.run_workflow(request, args.out, runner)
    except NotImplementedError as exc:
        print(json.dumps({"workflow_status": "MANUAL_INTEGRATION_REQUIRED",
                          "detail": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({"workflow_status": outcome.workflow_status,
                      "out": outcome.out_dir}, sort_keys=True))
    return 0 if outcome.completed else 1


def cmd_verify(args):
    try:
        result = verifier.verify(args.run)
    except Exception as exc:
        print(json.dumps({"verify_ok": False, "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({"verify_ok": result.ok,
                      "workflow_status": result.workflow_status,
                      "reason": result.reason}, sort_keys=True))
    return 0 if result.ok else 1


def cmd_selfcheck(args):
    import selfcheck
    return selfcheck.main()


def build_parser():
    parser = argparse.ArgumentParser(
        prog="coordinator_v03.py",
        description="Coordinator Workflow v0.3 (Atlas-validated; read-only Atlas).")
    sub = parser.add_subparsers(dest="command")

    p_run = sub.add_parser("run", help="run the workflow")
    p_run.add_argument("--request", required=True)
    p_run.add_argument("--out", required=True)
    p_run.set_defaults(func=cmd_run)

    p_verify = sub.add_parser("verify", help="verify a workflow output folder")
    p_verify.add_argument("--run", dest="run", required=True)
    p_verify.set_defaults(func=cmd_verify)

    p_self = sub.add_parser("selfcheck", help="run in-process self-checks")
    p_self.set_defaults(func=cmd_selfcheck)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
