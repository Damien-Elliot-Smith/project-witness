#!/usr/bin/env python3
"""Stack Verifier v0.1 -- read-only structural verifier for one completed Project
Witness case (Coordinator v0.3 or Companion v0.3 output), optionally cross-checked
against its Unified Case Manifest v0.1 output.

Subcommands:
  check      -- verify a source case (and optional manifest) and write a report
  verify     -- verify a stack verifier output folder
  selfcheck  -- run small in-process self-checks
  summary    -- print fixed fields from a stack verification report (read-only)

It does not run workflows; does not call Sentinel, Aletheia, ODIN, Histor-lite,
Bridge, Case Bundle, Coordinator, Companion, Atlas, or Unified Manifest; does not
modify the source; does not copy evidence contents; and does not prove truth.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stack_verifier_lib import (canonical, validation, report as report_mod,
                              steps as steps_mod, checksums, verifier, versions)
from stack_verifier_lib.errors import CheckError, FAILED_SOURCE_TYPE_INVALID

REPORT_FILE = "stack_verification_report.json"
STEPS_FILE = "stack_verification_steps.json"
CHECKSUMS_FILE = "stack_verification_checksums.txt"


def cmd_check(args):
    if not validation.is_valid_source_type(args.source_type):
        print(json.dumps({"stack_verification_status": FAILED_SOURCE_TYPE_INVALID,
                          "error": "invalid source-type"}, sort_keys=True))
        return 1
    if not validation.output_dir_ok(args.out):
        print(json.dumps({"stack_verification_status": "FAILED_SOURCE_STRUCTURE_INVALID",
                          "error": "output directory is not empty"}, sort_keys=True))
        return 1
    try:
        report, _checked = report_mod.build_stack_report(
            args.source_type, args.source_run, args.manifest_run)
    except CheckError as exc:
        print(json.dumps({"stack_verification_status": exc.stack_status,
                          "error": exc.message}, sort_keys=True))
        return 1
    os.makedirs(args.out, exist_ok=True)
    canonical.write_canonical(os.path.join(args.out, REPORT_FILE), report)
    canonical.write_canonical(os.path.join(args.out, STEPS_FILE),
                              steps_mod.build_steps(steps_mod.all_completed()))
    canonical.atomic_write_bytes(os.path.join(args.out, CHECKSUMS_FILE),
                                 checksums.build_checksums_text(args.out))
    result = verifier.verify(args.out)
    print(json.dumps({"stack_verification_status": report["stack_verification_status"],
                      "source_status": report["source_status"],
                      "manifest_status": report["manifest_status"],
                      "case_id": report["case_id"], "verify_ok": result.ok,
                      "out": args.out}, sort_keys=True))
    return 0 if result.ok else 1


def cmd_verify(args):
    try:
        result = verifier.verify(args.run)
    except Exception as exc:
        print(json.dumps({"verify_ok": False, "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({"verify_ok": result.ok, "stack_verification_status": result.stack_status,
                      "reason": result.reason}, sort_keys=True))
    return 0 if result.ok else 1


def cmd_selfcheck(args):
    import selfcheck
    return selfcheck.main()


_SUMMARY_FIELDS = (
    "stack_verifier_version", "source_type", "stack_verification_status",
    "source_status", "manifest_status", "case_id", "requested_case_id",
    "evidence_id", "workflow_type", "action_type", "companion_status",
    "coordinator_workflow_status", "atlas_validation_status", "atlas_registry_status",
    "sentinel_status", "aletheia_status", "bridge_status", "odin_reasoning_status",
    "case_bundle_status", "case_id_consistent", "evidence_id_consistent",
    "checksums_valid", "atlas_vocabulary_valid", "manifest_consistent",
    "truth_boundary_valid", "source_artifact_count",
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
        prog="stack_verify.py", description="Stack Verifier v0.1 (read-only).")
    sub = parser.add_subparsers(dest="command")

    c = sub.add_parser("check", help="verify a source case and optional manifest")
    c.add_argument("--source-type", required=True, dest="source_type")
    c.add_argument("--source-run", required=True, dest="source_run")
    c.add_argument("--manifest-run", default=None, dest="manifest_run")
    c.add_argument("--out", required=True)
    c.set_defaults(func=cmd_check)

    v = sub.add_parser("verify", help="verify a stack verifier output")
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
