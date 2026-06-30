#!/usr/bin/env python3
# histor_lite.py
# Histor-lite v0.1.2 CLI: import-sentinel, verify-case, selfcheck.
#
# Histor-lite is a narrow importer/verifier. It imports Sentinel Core v0.2.2
# CREATE_DIRECTORY runs only, verifies them with the FROZEN Sentinel verifier,
# and writes a stack-level case summary. It is NOT full Histor.

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from histor_lite.errors import ImportRefused, VerifierUnavailable, CaseError  # noqa: E402
from histor_lite.sentinel_import import import_sentinel_run  # noqa: E402
from histor_lite.case_summary import verify_case  # noqa: E402
from histor_lite.versions import HISTOR_LITE_VERSION  # noqa: E402


def cmd_import_sentinel(args):
    try:
        result = import_sentinel_run(
            sentinel_root=args.sentinel_root,
            run_path=args.run,
            out_dir=args.out,
        )
    except VerifierUnavailable as e:
        print(f"ERROR: Sentinel verifier unavailable: {e}", file=sys.stderr)
        return 3
    except ImportRefused as e:
        print(f"REFUSED [{e.reason}]: {e}", file=sys.stderr)
        return 2

    print(f"IMPORTED case into: {result.case_dir}")
    print(f"  import_status:            {result.import_status}")
    print(f"  sentinel_replay_verdict:  {result.verdict}")
    print(f"  case_id:                  {result.case_summary['case_id']}")
    return 0


def cmd_verify_case(args):
    try:
        res = verify_case(args.case)
    except CaseError as e:
        print(f"CASE INTEGRITY FAILED: {e}", file=sys.stderr)
        return 1
    print(f"CASE INTEGRITY OK: {args.case}")
    print(f"  case_id:                  {res.get('case_id')}")
    print(f"  sentinel_replay_verdict:  {res.get('sentinel_replay_verdict')}")
    print(f"  import_status:            {res.get('import_status')}")
    return 0


def cmd_selfcheck(args):
    import selfcheck
    return selfcheck.main([])


def build_parser():
    p = argparse.ArgumentParser(
        prog="histor_lite",
        description="Histor-lite v0.1.2 — imports & verifies frozen Sentinel "
                    "v0.2.2 runs (not full Histor).")
    p.add_argument("--version", action="version",
                   version=f"Histor-lite v{HISTOR_LITE_VERSION}")
    sub = p.add_subparsers(dest="command", required=True)

    imp = sub.add_parser("import-sentinel",
                         help="import & verify a Sentinel run, write a case folder")
    imp.add_argument("--sentinel-root", required=True,
                     help="path to an extracted sentinel_core_v022 directory")
    imp.add_argument("--run", required=True, help="path to a Sentinel run file")
    imp.add_argument("--out", required=True, help="case output directory to write")
    imp.set_defaults(func=cmd_import_sentinel)

    vc = sub.add_parser("verify-case", help="verify a written case folder's integrity")
    vc.add_argument("--case", required=True, help="path to a case output directory")
    vc.set_defaults(func=cmd_verify_case)

    sc = sub.add_parser("selfcheck", help="run in-process invariant gates")
    sc.set_defaults(func=cmd_selfcheck)
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
