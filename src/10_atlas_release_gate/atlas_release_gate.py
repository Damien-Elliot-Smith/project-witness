#!/usr/bin/env python3
"""Atlas Release Gate v0.1 command-line interface.

Subcommands:
  check     -- run the release gate against an Atlas Registry v0.1 release folder
  verify    -- verify a previously produced release-gate output folder
  selfcheck -- run small in-process self-checks

At runtime, 'check' calls a frozen Atlas v0.1 via subprocess. The default unit
tests inject an in-process fake Atlas runner instead.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from atlas_release_gate_lib import gate, verifier
from atlas_release_gate_lib.atlas_runner import SubprocessAtlasRunner


def cmd_check(args):
    runner = SubprocessAtlasRunner()
    outcome = gate.run_check(args.atlas_root, args.out, runner)
    print(json.dumps({"release_gate_status": outcome.status,
                      "out": outcome.out_dir}, sort_keys=True))
    return 0 if outcome.passed else 1


def cmd_verify(args):
    try:
        result = verifier.verify(args.run)
    except Exception as exc:  # surfaced as a clean non-zero exit
        print(json.dumps({"verify_ok": False, "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({"verify_ok": result.ok,
                      "release_gate_status": result.status,
                      "reason": result.reason}, sort_keys=True))
    return 0 if result.ok else 1


def cmd_selfcheck(args):
    import selfcheck
    return selfcheck.main()


def build_parser():
    parser = argparse.ArgumentParser(
        prog="atlas_release_gate.py",
        description="Atlas Release Gate v0.1 (read-only; does not prove truth).")
    sub = parser.add_subparsers(dest="command")

    p_check = sub.add_parser("check", help="run the release gate")
    p_check.add_argument("--atlas-root", dest="atlas_root", required=True)
    p_check.add_argument("--out", dest="out", required=True)
    p_check.set_defaults(func=cmd_check)

    p_verify = sub.add_parser("verify", help="verify a release-gate output folder")
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
