#!/usr/bin/env python3
# histor_aletheia.py
# Histor-lite Aletheia Importer v0.1 CLI. Imports a verified Aletheia evidence
# bundle into a Histor-lite-style evidence case, and verifies the case. Records
# integrity metadata only — never claims the evidence contents are true.

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from histor_aletheia_importer.errors import (  # noqa: E402
    ComponentPathError, AletheiaVerifyError, ManifestError, VerifyError)
from histor_aletheia_importer.importer import import_evidence  # noqa: E402
from histor_aletheia_importer.verifier import verify_case  # noqa: E402
from histor_aletheia_importer import versions  # noqa: E402


def cmd_import_evidence(args, aletheia_verifier=None):
    try:
        result = import_evidence(
            aletheia_root=args.aletheia_root, bundle_dir=args.bundle,
            out_dir=args.out, aletheia_verifier=aletheia_verifier)
    except ComponentPathError as e:
        print(f"REFUSED [{e.reason}]: {e}", file=sys.stderr)
        return 2
    except AletheiaVerifyError as e:
        print(f"IMPORT {versions.FAILED_ALETHEIA_VERIFY} [{e.reason}]: {e}",
              file=sys.stderr)
        return 1
    except ManifestError as e:
        status = (versions.FAILED_STATUS_NOT_VERIFIED_PRESENT
                  if e.reason == "STATUS_NOT_VERIFIED_PRESENT"
                  else versions.FAILED_MANIFEST_INVALID)
        print(f"IMPORT {status} [{e.reason}]: {e}", file=sys.stderr)
        return 1
    s = result.summary
    print(f"IMPORT {s['import_status']}")
    print(f"  case_id:                {s['case_id']}")
    print(f"  evidence_id:            {s['evidence_id']}")
    print(f"  source_evidence_status: {s['source_evidence_status']}")
    print(f"  source_file_sha256:     {s['source_file_sha256']}")
    print(f"  bundled_file_sha256:    {s['bundled_file_sha256']}")
    print(f"  output:                 {result.out_dir}")
    return 0


def cmd_verify_case(args):
    try:
        result = verify_case(args.case)
    except VerifyError as e:
        print(f"Evidence case NOT verified [{e.reason}]: {e}", file=sys.stderr)
        return 1
    print("Evidence case verified")
    print(f"  import_status:          {result.import_status}")
    print(f"  case_id:                {result.case_id}")
    print(f"  evidence_id:            {result.evidence_id}")
    print(f"  source_evidence_status: {result.source_evidence_status}")
    return 0


def cmd_selfcheck(args):
    import selfcheck
    return selfcheck.main([])


def build_parser():
    p = argparse.ArgumentParser(
        prog="histor_aletheia",
        description="Histor-lite Aletheia Importer v0.1 — record a verified "
                    "Aletheia evidence bundle as an evidence case (integrity "
                    "metadata only; not a truth claim).")
    p.add_argument("--version", action="version",
                   version=f"Histor-lite Aletheia Importer v"
                           f"{versions.IMPORTER_VERSION}")
    sub = p.add_subparsers(dest="command", required=True)

    ie = sub.add_parser("import-evidence",
                        help="import a verified Aletheia bundle into a case")
    ie.add_argument("--aletheia-root", required=True)
    ie.add_argument("--bundle", required=True)
    ie.add_argument("--out", required=True)
    ie.set_defaults(func=cmd_import_evidence)

    vc = sub.add_parser("verify-case", help="verify an imported evidence case")
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
