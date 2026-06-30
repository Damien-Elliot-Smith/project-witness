#!/usr/bin/env python3
# aletheia.py
# Aletheia Evidence Bundle v0.1 CLI. Bundles one local file as evidence and
# verifies the bundle. Proves preservation/hash integrity only — never truth.

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from aletheia_evidence.builder import build_bundle  # noqa: E402
from aletheia_evidence.errors import (  # noqa: E402
    ValidationError, BuildError, VerifyError)
from aletheia_evidence.verifier import verify_bundle  # noqa: E402
from aletheia_evidence import versions  # noqa: E402


def cmd_bundle_file(args):
    try:
        result = build_bundle(
            source_file=args.file, case_id=args.case_id,
            evidence_id=args.evidence_id, out_dir=args.out)
    except ValidationError as e:
        print(f"REFUSED [{e.reason}]: {e}", file=sys.stderr)
        return 2
    except BuildError as e:
        print(f"BUILD FAILED [{e.reason}]: {e}", file=sys.stderr)
        return 2
    m = result.manifest
    print("Aletheia evidence bundle created")
    print(f"  case_id:         {m['case_id']}")
    print(f"  evidence_id:     {m['evidence_id']}")
    print(f"  source_file:     {m['source_file_name']} "
          f"({m['source_file_size_bytes']} bytes)")
    print(f"  source_sha256:   {m['source_file_sha256']}")
    print(f"  bundled_sha256:  {m['bundled_file_sha256']}")
    print(f"  bundle_status:   {m['bundle_status']}")
    print(f"  evidence_status: {m['evidence_status']}")
    print(f"  output:          {result.out_dir}")
    return 0


def cmd_verify(args):
    try:
        result = verify_bundle(args.bundle)
    except VerifyError as e:
        print(f"Aletheia evidence bundle NOT verified [{e.status}]: {e}",
              file=sys.stderr)
        return 1
    print("Aletheia evidence bundle verified")
    print(f"  evidence_status = {result.evidence_status}")
    print(f"  case_id         = {result.case_id}")
    print(f"  evidence_id     = {result.evidence_id}")
    return 0


def cmd_selfcheck(args):
    import selfcheck
    return selfcheck.main([])


def build_parser():
    p = argparse.ArgumentParser(
        prog="aletheia",
        description="Aletheia Evidence Bundle v0.1 — bundle one local file as "
                    "evidence and verify it (preservation/hash integrity only; "
                    "not a truth claim).")
    p.add_argument("--version", action="version",
                   version=f"Aletheia Evidence Bundle v"
                           f"{versions.ALETHEIA_EVIDENCE_BUNDLE_VERSION}")
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("bundle-file", help="bundle one local evidence file")
    b.add_argument("--file", required=True)
    b.add_argument("--case-id", required=True)
    b.add_argument("--evidence-id", required=True)
    b.add_argument("--out", required=True)
    b.set_defaults(func=cmd_bundle_file)

    v = sub.add_parser("verify", help="verify an evidence bundle")
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
