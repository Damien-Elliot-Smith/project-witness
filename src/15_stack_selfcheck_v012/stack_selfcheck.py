#!/usr/bin/env python3
"""Stack Selfcheck v0.1 -- read-only health check for the frozen Project Witness
Local v1 stack inventory.

Subcommands:
  check      -- check a stack inventory (and optional Stack Verifier output)
  verify     -- verify a stack selfcheck output folder
  selfcheck  -- run small in-process self-checks
  summary    -- print fixed fields from a stack selfcheck report (read-only)

It does not run workflows; does not call Sentinel, Histor-lite, Aletheia, ODIN,
the Bridge, Case Bundle, Coordinator, Companion, Atlas, Unified Manifest, or Stack
Verifier during the freeze gate; does not copy evidence contents; and does not
prove truth.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stack_selfcheck_lib import (canonical, report as report_mod, steps as steps_mod,
                               checksums, verifier)
from stack_selfcheck_lib.errors import CheckError

REPORT_FILE = "stack_selfcheck_report.json"
STEPS_FILE = "stack_selfcheck_steps.json"
CHECKSUMS_FILE = "stack_selfcheck_checksums.txt"


def cmd_check(args):
    from stack_selfcheck_lib.validation import output_dir_ok
    if not output_dir_ok(args.out):
        print(json.dumps({"stack_selfcheck_status": "FAILED_INVENTORY_INVALID",
                          "error": "output directory is not empty"}, sort_keys=True))
        return 1
    try:
        report, _checked = report_mod.build_selfcheck_report(
            args.inventory, args.stack_verifier_run)
    except CheckError as exc:
        print(json.dumps({"stack_selfcheck_status": exc.stack_status,
                          "error": exc.message}, sort_keys=True))
        return 1
    os.makedirs(args.out, exist_ok=True)
    canonical.write_canonical(os.path.join(args.out, REPORT_FILE), report)
    canonical.write_canonical(os.path.join(args.out, STEPS_FILE),
                              steps_mod.build_steps(steps_mod.all_completed()))
    canonical.atomic_write_bytes(os.path.join(args.out, CHECKSUMS_FILE),
                                 checksums.build_checksums_text(args.out))
    result = verifier.verify(args.out)
    print(json.dumps({"stack_selfcheck_status": report["stack_selfcheck_status"],
                      "inventory_status": report["inventory_status"],
                      "documentation_boundary_status": report["documentation_boundary_status"],
                      "stack_verifier_status": report["stack_verifier_status"],
                      "component_count": report["component_count"],
                      "legacy_documentation_allowance_count":
                          len(report["legacy_documentation_allowances"]),
                      "verify_ok": result.ok, "out": args.out}, sort_keys=True))
    return 0 if result.ok else 1


def cmd_verify(args):
    try:
        result = verifier.verify(args.run)
    except Exception as exc:
        print(json.dumps({"verify_ok": False, "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({"verify_ok": result.ok, "stack_selfcheck_status": result.stack_status,
                      "reason": result.reason}, sort_keys=True))
    return 0 if result.ok else 1


def cmd_selfcheck(args):
    import selfcheck
    return selfcheck.main()


_SUMMARY_FIELDS = (
    "stack_selfcheck_version", "stack_name", "stack_selfcheck_status",
    "inventory_status", "required_components_present", "component_versions_consistent",
    "component_roots_present", "zip_sidecars_valid", "documentation_boundaries_present",
    "documentation_boundary_status", "truth_boundary_valid", "stack_verifier_status",
    "component_count",
)


def cmd_summary(args):
    path = os.path.join(args.run, REPORT_FILE)
    if not os.path.isfile(path):
        print(json.dumps({"error": "report not found"}, sort_keys=True))
        return 1
    report = canonical.load_json(path)
    summary = {k: report.get(k) for k in _SUMMARY_FIELDS}
    print(json.dumps(summary, sort_keys=True, indent=2))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="stack_selfcheck.py", description="Stack Selfcheck v0.1 (read-only).")
    sub = parser.add_subparsers(dest="command")

    c = sub.add_parser("check", help="check a stack inventory")
    c.add_argument("--inventory", required=True, dest="inventory")
    c.add_argument("--stack-verifier-run", default=None, dest="stack_verifier_run")
    c.add_argument("--out", required=True)
    c.set_defaults(func=cmd_check)

    v = sub.add_parser("verify", help="verify a stack selfcheck output")
    v.add_argument("--run", required=True, dest="run")
    v.set_defaults(func=cmd_verify)

    s = sub.add_parser("selfcheck", help="run in-process self-checks")
    s.set_defaults(func=cmd_selfcheck)

    m = sub.add_parser("summary", help="print fixed report fields (read-only)")
    m.add_argument("--run", required=True, dest="run")
    m.set_defaults(func=cmd_summary)
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
