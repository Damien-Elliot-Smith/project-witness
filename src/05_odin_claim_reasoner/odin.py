#!/usr/bin/env python3
# odin.py
# ODIN Claim Reasoner v0.1 CLI. Validates structured claims, detects direct
# contradictions, writes a canonical reasoning report + proof trace, and verifies
# the output. Deterministic; proves structural consistency only — never truth.

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from odin_reasoner.canonical import canonical_bytes  # noqa: E402
from odin_reasoner.claims import validate_claim_set  # noqa: E402
from odin_reasoner.errors import (  # noqa: E402
    ValidationError, VerifyError, ImportError_, OdinError)
from odin_reasoner.reasoner import reason_to_dir  # noqa: E402
from odin_reasoner.verifier import verify_run  # noqa: E402
from odin_reasoner.aletheia_import import import_manifest_file  # noqa: E402
from odin_reasoner import versions  # noqa: E402


def _load_json(path, what):
    if not os.path.isfile(path):
        raise ValidationError("INPUT_MISSING", f"{what} not found: {path!r}")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:  # noqa: BLE001
        raise ValidationError("INPUT_MALFORMED",
                              f"{what} is not valid JSON: {e}")


def cmd_validate_claims(args):
    try:
        data = _load_json(args.claims, "claims file")
        validate_claim_set(data)
    except ValidationError as e:
        print(f"INVALID [{e.reason}]: {e}", file=sys.stderr)
        return 2
    print("ODIN claim set is valid")
    print(f"  case_id:     {data['case_id']}")
    print(f"  claim_count: {len(data['claims'])}")
    return 0


def cmd_reason(args):
    try:
        data = _load_json(args.claims, "claims file")
        result = reason_to_dir(data, args.out)
    except ValidationError as e:
        print(f"INVALID_INPUT [{e.reason}]: {e}", file=sys.stderr)
        return 2
    r = result.report
    print("ODIN reasoning complete")
    print(f"  case_id:             {r['case_id']}")
    print(f"  reasoning_status:    {r['reasoning_status']}")
    print(f"  claim_count:         {r['claim_count']}")
    print(f"  contradiction_count: {r['contradiction_count']}")
    print(f"  output:              {result.out_dir}")
    return 0


def cmd_verify(args):
    try:
        result = verify_run(args.run)
    except VerifyError as e:
        print(f"ODIN output NOT verified [{e.reason}]: {e}", file=sys.stderr)
        return 1
    print("ODIN output verified")
    print(f"  reasoning_status:    {result.reasoning_status}")
    print(f"  case_id:             {result.case_id}")
    print(f"  contradiction_count: {result.contradiction_count}")
    return 0


def cmd_import_aletheia(args):
    try:
        claim_set = import_manifest_file(args.manifest)
    except ImportError_ as e:
        print(f"IMPORT REFUSED [{e.reason}]: {e}", file=sys.stderr)
        return 2
    data = canonical_bytes(claim_set)
    out = args.out
    if out:
        tmp = out + ".tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, out)
        print(f"Wrote {len(claim_set['claims'])} integrity claims to {out}")
    else:
        sys.stdout.buffer.write(data)
    return 0


def cmd_selfcheck(args):
    import selfcheck
    return selfcheck.main([])


def build_parser():
    p = argparse.ArgumentParser(
        prog="odin",
        description="ODIN Claim Reasoner v0.1 — deterministic reasoning over "
                    "structured claims (direct contradictions only; not a truth "
                    "claim, no LLM).")
    p.add_argument("--version", action="version",
                   version=f"ODIN Claim Reasoner v{versions.ODIN_REASONER_VERSION}")
    sub = p.add_subparsers(dest="command", required=True)

    vc = sub.add_parser("validate-claims", help="validate a claims.json file")
    vc.add_argument("--claims", required=True)
    vc.set_defaults(func=cmd_validate_claims)

    rs = sub.add_parser("reason", help="reason over claims and write output")
    rs.add_argument("--claims", required=True)
    rs.add_argument("--out", required=True)
    rs.set_defaults(func=cmd_reason)

    vf = sub.add_parser("verify", help="verify an ODIN output folder")
    vf.add_argument("--run", required=True)
    vf.set_defaults(func=cmd_verify)

    im = sub.add_parser("import-aletheia",
                        help="convert an Aletheia manifest to integrity claims")
    im.add_argument("--manifest", required=True)
    im.add_argument("--out", required=False, default=None)
    im.set_defaults(func=cmd_import_aletheia)

    sc = sub.add_parser("selfcheck", help="run in-process invariant gates")
    sc.set_defaults(func=cmd_selfcheck)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
