#!/usr/bin/env python3
# atlas.py
# Atlas Registry v0.1 CLI — verify the registry, export a portable summary, verify an
# export, and list registry sections. Read-only: runs no workflows, calls no
# components, decides no truth.

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from atlas_registry_lib.errors import (  # noqa: E402
    RegistryError, ExportError, BuildPathError)
from atlas_registry_lib.exporter import export_registry, verify_export  # noqa: E402
from atlas_registry_lib.verifier import verify_registry, load_registry  # noqa: E402
from atlas_registry_lib import versions  # noqa: E402

_LIST_SECTIONS = ("components", "workflow_types", "action_types", "statuses",
                  "claim_predicates", "case_record_types", "known_limitations")


def cmd_verify(ns):
    try:
        result = verify_registry(ns.registry)
    except RegistryError as e:
        print(f"Registry NOT verified [{e.registry_status}/{e.reason}]: {e}",
              file=sys.stderr)
        return 1
    print("Registry verified")
    print(f"  registry_status:         {result.registry_status}")
    print(f"  registry_id:             {result.registry['registry_id']}")
    print(f"  component_count:         {result.counts['component_count']}")
    print(f"  workflow_type_count:     {result.counts['workflow_type_count']}")
    print(f"  action_type_count:       {result.counts['action_type_count']}")
    print(f"  status_count:            {result.counts['status_count']}")
    print(f"  claim_predicate_count:   {result.counts['claim_predicate_count']}")
    return 0


def cmd_export(ns):
    try:
        result = export_registry(ns.registry, ns.out)
    except BuildPathError as e:
        print(f"REFUSED [{e.reason}]: {e}", file=sys.stderr)
        return 2
    except (RegistryError, ExportError) as e:
        reason = getattr(e, "reason", "ERROR")
        print(f"Export failed [{reason}]: {e}", file=sys.stderr)
        return 1
    print("Registry exported")
    print(f"  registry_status:         {result.summary['registry_status']}")
    print(f"  component_count:         {result.summary['component_count']}")
    print(f"  status_count:            {result.summary['status_count']}")
    print(f"  output:                  {result.out_dir}")
    return 0


def cmd_verify_export(ns):
    try:
        summary = verify_export(ns.export)
    except ExportError as e:
        print(f"Export NOT verified [{e.reason}]: {e}", file=sys.stderr)
        return 1
    print("Export verified")
    print(f"  registry_status:         {summary['registry_status']}")
    print(f"  component_count:         {summary['component_count']}")
    return 0


def cmd_list(ns):
    try:
        reg = load_registry(ns.registry)
    except RegistryError as e:
        print(f"Registry NOT loadable [{e.reason}]: {e}", file=sys.stderr)
        return 1
    section = reg.get(ns.section)
    if section is None:
        print(f"unknown section {ns.section!r}; choices: {_LIST_SECTIONS}",
              file=sys.stderr)
        return 2
    # Print entries only; no inference, no calls.
    print(f"# {ns.section} ({len(section)} entries)")
    for entry in section:
        if isinstance(entry, dict):
            primary = (entry.get("component_id") or entry.get("workflow_type")
                       or entry.get("action_type") or entry.get("status")
                       or entry.get("predicate") or entry.get("record_type"))
            print(f"  - {primary}")
        else:
            print(f"  - {entry}")
    return 0


def cmd_selfcheck(ns):
    import selfcheck
    return selfcheck.main([])


def build_parser():
    p = argparse.ArgumentParser(
        prog="atlas",
        description="Atlas Registry v0.1 — read-only registry of Project Witness "
                    "vocabulary and metadata (records vocabulary; not a truth claim).")
    p.add_argument("--version", action="version",
                   version=f"Atlas Registry v{versions.ATLAS_REGISTRY_VERSION}")
    sub = p.add_subparsers(dest="command", required=True)

    v = sub.add_parser("verify", help="verify a registry file")
    v.add_argument("--registry", required=True)
    v.set_defaults(func=cmd_verify)

    e = sub.add_parser("export", help="export a verified registry summary")
    e.add_argument("--registry", required=True)
    e.add_argument("--out", required=True)
    e.set_defaults(func=cmd_export)

    ve = sub.add_parser("verify-export", help="verify an export folder")
    ve.add_argument("--export", required=True)
    ve.set_defaults(func=cmd_verify_export)

    ls = sub.add_parser("list", help="print entries of a registry section")
    ls.add_argument("--registry", required=True)
    ls.add_argument("--section", required=True, choices=_LIST_SECTIONS)
    ls.set_defaults(func=cmd_list)

    s = sub.add_parser("selfcheck", help="run in-process invariant gates")
    s.set_defaults(func=cmd_selfcheck)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
