#!/usr/bin/env python3
# histor_odin.py
# Histor-lite ODIN Importer v0.1 CLI. Imports a verified ODIN reasoning output into
# a Histor-lite-style reasoning case, and verifies the case. Records structural
# reasoning metadata only — never claims any claim is true.

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from histor_odin_importer.errors import (  # noqa: E402
    ComponentPathError, OdinVerifyError, OdinRunError, VerifyError)
from histor_odin_importer.importer import import_reasoning  # noqa: E402
from histor_odin_importer.verifier import verify_case  # noqa: E402
from histor_odin_importer import versions  # noqa: E402

# Map OdinRunError reasons to the spec's import_status failure codes.
_RUN_REASON_TO_STATUS = {
    "REASONING_STATUS_INVALID": versions.FAILED_REASONING_STATUS_INVALID,
    "REPORT_MISSING": versions.FAILED_REPORT_INVALID,
    "REPORT_MALFORMED": versions.FAILED_REPORT_INVALID,
    "REPORT_INVALID": versions.FAILED_REPORT_INVALID,
    "CLAIMS_MISSING": versions.FAILED_REPORT_INVALID,
    "CLAIMS_MALFORMED": versions.FAILED_REPORT_INVALID,
    "PROOF_TRACE_MISSING": versions.FAILED_PROOF_TRACE_INVALID,
    "PROOF_TRACE_MALFORMED": versions.FAILED_PROOF_TRACE_INVALID,
    "PROOF_TRACE_INVALID": versions.FAILED_PROOF_TRACE_INVALID,
}


def cmd_import_reasoning(args, odin_verifier=None):
    try:
        result = import_reasoning(
            odin_root=args.odin_root, run_dir=args.run, out_dir=args.out,
            odin_verifier=odin_verifier)
    except ComponentPathError as e:
        print(f"REFUSED [{e.reason}]: {e}", file=sys.stderr)
        return 2
    except OdinVerifyError as e:
        print(f"IMPORT {versions.FAILED_ODIN_VERIFY} [{e.reason}]: {e}",
              file=sys.stderr)
        return 1
    except OdinRunError as e:
        status = _RUN_REASON_TO_STATUS.get(e.reason, versions.FAILED_REPORT_INVALID)
        print(f"IMPORT {status} [{e.reason}]: {e}", file=sys.stderr)
        return 1
    s = result.summary
    print(f"IMPORT {s['import_status']}")
    print(f"  case_id:                 {s['case_id']}")
    print(f"  source_reasoning_status: {s['source_reasoning_status']}")
    print(f"  claim_count:             {s['claim_count']}")
    print(f"  contradiction_count:     {s['contradiction_count']}")
    print(f"  proof_step_count:        {s['proof_step_count']}")
    print(f"  output:                  {result.out_dir}")
    return 0


def cmd_verify_case(args):
    try:
        result = verify_case(args.case)
    except VerifyError as e:
        print(f"ODIN reasoning case NOT verified [{e.reason}]: {e}",
              file=sys.stderr)
        return 1
    print("ODIN reasoning case verified")
    print(f"  import_status:           {result.import_status}")
    print(f"  case_id:                 {result.case_id}")
    print(f"  source_reasoning_status: {result.source_reasoning_status}")
    print(f"  claim_count:             {result.claim_count}")
    print(f"  contradiction_count:     {result.contradiction_count}")
    print(f"  proof_step_count:        {result.proof_step_count}")
    return 0


def cmd_selfcheck(args):
    import selfcheck
    return selfcheck.main([])


def build_parser():
    p = argparse.ArgumentParser(
        prog="histor_odin",
        description="Histor-lite ODIN Importer v0.1 — record a verified ODIN "
                    "reasoning output as a reasoning case (structural metadata "
                    "only; not a truth claim).")
    p.add_argument("--version", action="version",
                   version=f"Histor-lite ODIN Importer v{versions.IMPORTER_VERSION}")
    sub = p.add_subparsers(dest="command", required=True)

    ir = sub.add_parser("import-reasoning",
                        help="import a verified ODIN run into a reasoning case")
    ir.add_argument("--odin-root", required=True)
    ir.add_argument("--run", required=True)
    ir.add_argument("--out", required=True)
    ir.set_defaults(func=cmd_import_reasoning)

    vc = sub.add_parser("verify-case", help="verify an imported reasoning case")
    vc.add_argument("--case", required=True)
    vc.set_defaults(func=cmd_verify_case)

    sc = sub.add_parser("selfcheck", help="run in-process invariant gates")
    sc.set_defaults(func=cmd_selfcheck)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
