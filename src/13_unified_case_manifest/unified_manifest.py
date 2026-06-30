#!/usr/bin/env python3
"""Unified Case Manifest v0.1 -- read-only summariser for one completed Project
Witness case (Coordinator v0.3 or Companion v0.3 output).

Subcommands:
  build      -- read a source case output and write a unified manifest package
  verify     -- verify a unified manifest output folder
  selfcheck  -- run small in-process self-checks
  summary    -- print fixed fields from a unified manifest (read-only)

This tool reads existing verified outputs only. It does not run workflows; does
not call Sentinel, Aletheia, ODIN, Histor-lite, Bridge, Case Bundle, Coordinator,
Companion, or Atlas; does not modify the source; does not copy evidence contents;
and does not prove truth.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unified_manifest_lib import (canonical, validation, manifest as manifest_mod,
                                 checksums, verifier, versions)
from unified_manifest_lib.errors import BuildError, FAILED_SOURCE_TYPE_INVALID

MANIFEST_FILE = "unified_case_manifest.json"
SOURCE_INDEX_FILE = "source_index.json"
CHECKSUMS_FILE = "unified_manifest_checksums.txt"


def cmd_build(args):
    if not validation.is_valid_source_type(args.source_type):
        print(json.dumps({"source_status": FAILED_SOURCE_TYPE_INVALID,
                          "error": "invalid source-type"}, sort_keys=True))
        return 1
    if not validation.output_dir_ok(args.out):
        print(json.dumps({"source_status": "FAILED_SOURCE_STRUCTURE_INVALID",
                          "error": "output directory is not empty"}, sort_keys=True))
        return 1
    try:
        manifest, source_index = manifest_mod.build_manifest_data(
            args.source_type, args.source_run)
    except BuildError as exc:
        print(json.dumps({"source_status": exc.source_status,
                          "error": exc.message}, sort_keys=True))
        return 1
    os.makedirs(args.out, exist_ok=True)
    canonical.write_canonical(os.path.join(args.out, MANIFEST_FILE), manifest)
    canonical.write_canonical(os.path.join(args.out, SOURCE_INDEX_FILE), source_index)
    canonical.atomic_write_bytes(os.path.join(args.out, CHECKSUMS_FILE),
                                 checksums.build_checksums_text(args.out))
    result = verifier.verify(args.out)
    print(json.dumps({"source_status": manifest["source_status"],
                      "case_id": manifest["case_id"],
                      "evidence_id": manifest["evidence_id"],
                      "verify_ok": result.ok, "out": args.out}, sort_keys=True))
    return 0 if result.ok else 1


def cmd_verify(args):
    try:
        result = verifier.verify(args.run)
    except Exception as exc:
        print(json.dumps({"verify_ok": False, "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({"verify_ok": result.ok, "source_status": result.source_status,
                      "reason": result.reason}, sort_keys=True))
    return 0 if result.ok else 1


def cmd_selfcheck(args):
    import selfcheck
    return selfcheck.main()


_SUMMARY_FIELDS = (
    "unified_case_manifest_version", "source_type", "case_id", "requested_case_id",
    "evidence_id", "workflow_type", "action_type", "source_status",
    "companion_status", "coordinator_workflow_status", "atlas_validation_status",
    "atlas_registry_status", "sentinel_status", "aletheia_status", "bridge_status",
    "odin_reasoning_status", "case_bundle_status",
)


def cmd_summary(args):
    path = os.path.join(args.run, MANIFEST_FILE)
    if not os.path.isfile(path):
        print(json.dumps({"error": "manifest not found"}, sort_keys=True))
        return 1
    manifest = canonical.load_json(path)
    summary = {k: manifest.get(k) for k in _SUMMARY_FIELDS}
    summary["source_artifacts_count"] = len(manifest.get("source_artifacts", []))
    print(json.dumps(summary, sort_keys=True, indent=2))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="unified_manifest.py",
        description="Unified Case Manifest v0.1 (read-only case summariser).")
    sub = parser.add_subparsers(dest="command")

    b = sub.add_parser("build", help="build a unified manifest from a source case")
    b.add_argument("--source-type", required=True, dest="source_type")
    b.add_argument("--source-run", required=True, dest="source_run")
    b.add_argument("--out", required=True)
    b.set_defaults(func=cmd_build)

    v = sub.add_parser("verify", help="verify a unified manifest output")
    v.add_argument("--run", required=True, dest="run")
    v.set_defaults(func=cmd_verify)

    s = sub.add_parser("selfcheck", help="run in-process self-checks")
    s.set_defaults(func=cmd_selfcheck)

    m = sub.add_parser("summary", help="print fixed manifest fields (read-only)")
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
