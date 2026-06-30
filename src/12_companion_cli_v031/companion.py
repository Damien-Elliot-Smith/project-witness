#!/usr/bin/env python3
"""Companion CLI v0.3 -- human-facing wrapper around Coordinator Workflow v0.3.

Subcommands:
  create-evidence-case  -- run one Atlas-validated evidence-and-reasoning case
  verify                -- verify a Companion v0.3 output folder
  selfcheck             -- run small in-process self-checks
  list-atlas-terms      -- read-only display of copied Atlas terms

At runtime, Companion calls the frozen Coordinator Workflow v0.3 via subprocess.
The default unit tests inject an in-process fake Coordinator runner and spawn no
subprocesses. Companion never calls lower components directly and never modifies
Atlas.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from companion_lib import engine, verifier, canonical
from companion_lib.coordinator_runner import SubprocessCoordinatorRunner


def cmd_create(args):
    params = {
        "case_id": args.case_id,
        "evidence_id": args.evidence_id,
        "evidence_file": args.evidence_file,
        "allowed_root": args.allowed_root,
        "case_directory_name": args.case_directory_name,
        "coordinator_root": args.coordinator_root,
        "out": args.out,
        "component_roots": {
            "atlas_registry_root": args.atlas_registry_root,
            "sentinel_root": args.sentinel_root,
            "histor_lite_root": args.histor_lite_root,
            "aletheia_root": args.aletheia_root,
            "bridge_root": args.bridge_root,
            "odin_root": args.odin_root,
            "histor_aletheia_root": args.histor_aletheia_root,
            "histor_odin_root": args.histor_odin_root,
            "case_bundle_v02_root": args.case_bundle_v02_root,
        },
    }
    runner = SubprocessCoordinatorRunner(args.coordinator_root)
    outcome = engine.create_evidence_case(params, runner)
    print(json.dumps({"companion_status": outcome.companion_status,
                      "out": outcome.out_dir}, sort_keys=True))
    return 0 if outcome.completed else 1


def cmd_verify(args):
    try:
        result = verifier.verify(args.run)
    except Exception as exc:
        print(json.dumps({"verify_ok": False, "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({"verify_ok": result.ok,
                      "companion_status": result.companion_status,
                      "reason": result.reason}, sort_keys=True))
    return 0 if result.ok else 1


def cmd_selfcheck(args):
    import selfcheck
    return selfcheck.main()


def cmd_list_atlas_terms(args):
    path = os.path.join(args.run, "coordinator_output", "atlas_registry_copy.json")
    if not os.path.isfile(path):
        print(json.dumps({"error": "atlas_registry_copy.json not found"},
                         sort_keys=True))
        return 1
    registry = canonical.load_json(path)
    section = args.section
    key_map = {
        "statuses": ("statuses", "status"),
        "components": ("components", "component_id"),
        "workflow_types": ("workflow_types", "workflow_type"),
        "action_types": ("action_types", "action_type"),
        "predicates": ("claim_predicates", "predicate"),
    }
    if section not in key_map:
        print(json.dumps({"error": "unknown section"}, sort_keys=True))
        return 1
    field, item_key = key_map[section]
    terms = [it[item_key] for it in registry.get(field, [])
             if isinstance(it, dict) and item_key in it]
    print(json.dumps({"section": section, "terms": sorted(terms)}, sort_keys=True))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="companion.py",
        description="Companion CLI v0.3 (wraps Coordinator Workflow v0.3).")
    sub = parser.add_subparsers(dest="command")

    c = sub.add_parser("create-evidence-case", help="run one Atlas-validated case")
    c.add_argument("--case-id", required=True, dest="case_id")
    c.add_argument("--evidence-id", required=True, dest="evidence_id")
    c.add_argument("--evidence-file", required=True, dest="evidence_file")
    c.add_argument("--allowed-root", required=True, dest="allowed_root")
    c.add_argument("--case-directory-name", required=True, dest="case_directory_name")
    c.add_argument("--coordinator-root", required=True, dest="coordinator_root")
    c.add_argument("--atlas-registry-root", required=True, dest="atlas_registry_root")
    c.add_argument("--sentinel-root", required=True, dest="sentinel_root")
    c.add_argument("--histor-lite-root", required=True, dest="histor_lite_root")
    c.add_argument("--aletheia-root", required=True, dest="aletheia_root")
    c.add_argument("--bridge-root", required=True, dest="bridge_root")
    c.add_argument("--odin-root", required=True, dest="odin_root")
    c.add_argument("--histor-aletheia-root", required=True, dest="histor_aletheia_root")
    c.add_argument("--histor-odin-root", required=True, dest="histor_odin_root")
    c.add_argument("--case-bundle-v02-root", required=True, dest="case_bundle_v02_root")
    c.add_argument("--out", required=True)
    c.set_defaults(func=cmd_create)

    v = sub.add_parser("verify", help="verify a Companion output folder")
    v.add_argument("--run", dest="run", required=True)
    v.set_defaults(func=cmd_verify)

    s = sub.add_parser("selfcheck", help="run in-process self-checks")
    s.set_defaults(func=cmd_selfcheck)

    l = sub.add_parser("list-atlas-terms", help="read-only display of copied Atlas terms")
    l.add_argument("--run", dest="run", required=True)
    l.add_argument("--section", default="statuses")
    l.set_defaults(func=cmd_list_atlas_terms)
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
