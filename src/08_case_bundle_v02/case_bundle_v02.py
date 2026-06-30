#!/usr/bin/env python3
# case_bundle_v02.py
# Case Bundle v0.2 CLI. Builds a portable Project Witness case bundle from three
# verified Histor-lite case records, and verifies the bundle. Packages verified
# records only — never claims evidence contents or ODIN claims are true.

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from case_bundle_v02_lib.builder import build_bundle  # noqa: E402
from case_bundle_v02_lib.errors import (  # noqa: E402
    BuildPathError, InputCaseError, CaseIdMismatchError, VerifyError)
from case_bundle_v02_lib.verifier import verify_bundle  # noqa: E402
from case_bundle_v02_lib import versions  # noqa: E402


def cmd_build(args, input_verifier=None):
    try:
        result = build_bundle(
            sentinel_case=args.sentinel_case, aletheia_case=args.aletheia_case,
            odin_case=args.odin_case, out_dir=args.out,
            input_verifier=input_verifier)
    except BuildPathError as e:
        print(f"REFUSED [{e.reason}]: {e}", file=sys.stderr)
        return 2
    except CaseIdMismatchError as e:
        print(f"BUNDLE {e.bundle_status} [{e.reason}]: {e}", file=sys.stderr)
        return 1
    except InputCaseError as e:
        print(f"BUNDLE {e.bundle_status} [{e.reason}]: {e}", file=sys.stderr)
        return 1
    except VerifyError as e:
        print(f"BUNDLE self-verify failed [{e.reason}]: {e}", file=sys.stderr)
        return 1
    m = result.manifest
    print(f"BUNDLE {m['bundle_status']}")
    print(f"  case_id:                 {m['case_id']}")
    print(f"  included_records:        {', '.join(m['included_records'])}")
    print(f"  sentinel.action_status:  {m['sentinel']['action_status']}")
    print(f"  aletheia.evidence:       {m['aletheia']['source_evidence_status']}")
    print(f"  odin.reasoning:          {m['odin']['source_reasoning_status']}")
    print(f"  odin.claim_count:        {m['odin']['claim_count']}")
    print(f"  odin.contradiction_count:{m['odin']['contradiction_count']}")
    print(f"  output:                  {result.out_dir}")
    return 0


def cmd_verify(args):
    try:
        result = verify_bundle(args.bundle)
    except VerifyError as e:
        print(f"Bundle NOT verified [{e.reason}]: {e}", file=sys.stderr)
        return 1
    print("Bundle verified")
    print(f"  bundle_status:           {result.bundle_status}")
    print(f"  case_id:                 {result.case_id}")
    print(f"  aletheia.evidence:       {result.aletheia_status}")
    print(f"  odin.reasoning:          {result.odin_reasoning_status}")
    return 0


def cmd_selfcheck(args):
    import selfcheck
    return selfcheck.main([])


def build_parser():
    p = argparse.ArgumentParser(
        prog="case_bundle_v02",
        description="Case Bundle v0.2 — package three verified Histor-lite case "
                    "records into one portable Project Witness bundle (packages "
                    "verified records only; not a truth claim).")
    p.add_argument("--version", action="version",
                   version=f"Case Bundle v{versions.CASE_BUNDLE_VERSION}")
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="build a bundle from three case folders")
    b.add_argument("--sentinel-case", required=True)
    b.add_argument("--aletheia-case", required=True)
    b.add_argument("--odin-case", required=True)
    b.add_argument("--out", required=True)
    b.set_defaults(func=cmd_build)

    v = sub.add_parser("verify", help="verify a built bundle")
    v.add_argument("--bundle", required=True)
    v.set_defaults(func=cmd_verify)

    s = sub.add_parser("selfcheck", help="run in-process invariant gates")
    s.set_defaults(func=cmd_selfcheck)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
