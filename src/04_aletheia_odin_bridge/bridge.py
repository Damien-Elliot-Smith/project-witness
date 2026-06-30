#!/usr/bin/env python3
# bridge.py
# Aletheia -> ODIN Bridge v0.1 CLI. Converts a verified Aletheia evidence bundle
# into an ODIN claim set (integrity/presence claims only), writes a deterministic
# output folder, and verifies it. Proves conversion consistency — never truth.

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from aletheia_odin_bridge.aletheia_reader import (  # noqa: E402
    read_manifest, require_verified_present, SubprocessAletheiaVerifier)
from aletheia_odin_bridge.canonical import canonical_bytes  # noqa: E402
from aletheia_odin_bridge.checksums import format_checksums  # noqa: E402
from aletheia_odin_bridge.claim_builder import build_claims  # noqa: E402
from aletheia_odin_bridge.errors import (  # noqa: E402
    ComponentPathError, AletheiaVerifyError, ManifestError, OdinValidateError,
    VerifyError)
from aletheia_odin_bridge.odin_validator import SubprocessOdinValidator  # noqa: E402
from aletheia_odin_bridge.report import build_report  # noqa: E402
from aletheia_odin_bridge.validation import sha256_bytes  # noqa: E402
from aletheia_odin_bridge.verifier import verify_run  # noqa: E402
from aletheia_odin_bridge import versions  # noqa: E402


class ConvertResult:
    __slots__ = ("out_dir", "report", "claim_set")

    def __init__(self, out_dir, report, claim_set):
        self.out_dir = out_dir
        self.report = report
        self.claim_set = claim_set


def _write_bytes(path, data: bytes):
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def convert(*, aletheia_root, odin_root, bundle_dir, out_dir,
            aletheia_verifier=None, odin_validator=None):
    """Convert a verified Aletheia bundle into an ODIN claim set. Raises a typed
    BridgeError on failure. Verifiers/validators are injectable for tests.

    odin_root may be None to skip ODIN validation (recorded as SKIPPED).
    """
    # 1-3. Path existence.
    if not (isinstance(aletheia_root, str) and os.path.isdir(aletheia_root)):
        raise ComponentPathError("ALETHEIA_ROOT_MISSING",
                                 f"Aletheia root not found: {aletheia_root!r}")
    if odin_root is not None and not os.path.isdir(odin_root):
        raise ComponentPathError("ODIN_ROOT_MISSING",
                                 f"ODIN root not found: {odin_root!r}")
    if not (isinstance(bundle_dir, str) and os.path.isdir(bundle_dir)):
        raise ComponentPathError("BUNDLE_MISSING",
                                 f"Aletheia bundle not found: {bundle_dir!r}")

    # Refuse a non-empty output dir.
    if os.path.isdir(out_dir) and os.listdir(out_dir):
        raise ComponentPathError("OUTPUT_DIR_NOT_EMPTY",
                                 f"output directory is not empty: {out_dir!r}")

    # 4-5. Verify the bundle with frozen Aletheia (injectable).
    if aletheia_verifier is None:
        aletheia_verifier = SubprocessAletheiaVerifier(aletheia_root)
    aletheia_verifier.verify(bundle_dir)  # raises AletheiaVerifyError on failure

    # 6-7. Read manifest; require VERIFIED_PRESENT.
    manifest = read_manifest(bundle_dir)
    require_verified_present(manifest)

    # 8. Generate ODIN claims (integrity/presence only).
    claim_set = build_claims(manifest)

    # 9-10. Optional ODIN validation (injectable).
    odin_validation_status = versions.ODIN_VALIDATION_SKIPPED
    if odin_root is not None:
        if odin_validator is None:
            odin_validator = SubprocessOdinValidator(odin_root)
        odin_validator.validate(claim_set)  # raises OdinValidateError on failure
        odin_validation_status = versions.ODIN_VALIDATION_VALID

    # 11. Write deterministic output files.
    os.makedirs(out_dir, exist_ok=True)
    report = build_report(
        case_id=manifest["case_id"], evidence_id=manifest["evidence_id"],
        aletheia_evidence_status=manifest["evidence_status"],
        claims=claim_set["claims"], odin_validation_status=odin_validation_status)

    claims_bytes = canonical_bytes(claim_set)
    report_bytes = canonical_bytes(report)
    manifest_copy_bytes = canonical_bytes(manifest)

    _write_bytes(os.path.join(out_dir, versions.ODIN_CLAIMS_NAME), claims_bytes)
    _write_bytes(os.path.join(out_dir, versions.BRIDGE_REPORT_NAME), report_bytes)
    _write_bytes(os.path.join(out_dir, versions.MANIFEST_COPY_NAME),
                 manifest_copy_bytes)
    checksums = format_checksums(
        claims_sha256=sha256_bytes(claims_bytes),
        report_sha256=sha256_bytes(report_bytes),
        manifest_copy_sha256=sha256_bytes(manifest_copy_bytes))
    _write_bytes(os.path.join(out_dir, versions.CHECKSUMS_NAME), checksums)

    return ConvertResult(out_dir, report, claim_set)


def cmd_convert(args, aletheia_verifier=None, odin_validator=None):
    try:
        result = convert(
            aletheia_root=args.aletheia_root, odin_root=args.odin_root,
            bundle_dir=args.bundle, out_dir=args.out,
            aletheia_verifier=aletheia_verifier, odin_validator=odin_validator)
    except ComponentPathError as e:
        print(f"REFUSED [{e.reason}]: {e}", file=sys.stderr)
        return 2
    except AletheiaVerifyError as e:
        print(f"BRIDGE {versions.BRIDGE_FAILED_ALETHEIA_VERIFY} [{e.reason}]: {e}",
              file=sys.stderr)
        return 1
    except ManifestError as e:
        status = (versions.BRIDGE_FAILED_STATUS_NOT_VERIFIED_PRESENT
                  if e.reason == "STATUS_NOT_VERIFIED_PRESENT"
                  else versions.BRIDGE_FAILED_MANIFEST_INVALID)
        print(f"BRIDGE {status} [{e.reason}]: {e}", file=sys.stderr)
        return 1
    except OdinValidateError as e:
        print(f"BRIDGE {versions.BRIDGE_FAILED_ODIN_VALIDATE} [{e.reason}]: {e}",
              file=sys.stderr)
        return 1
    r = result.report
    print(f"BRIDGE {r['bridge_status']}")
    print(f"  case_id:                 {r['case_id']}")
    print(f"  evidence_id:             {r['evidence_id']}")
    print(f"  aletheia_evidence_status:{r['aletheia_evidence_status']}")
    print(f"  odin_claim_count:        {r['odin_claim_count']}")
    print(f"  odin_validation_status:  {r['odin_validation_status']}")
    print(f"  generated_claims:        {', '.join(r['generated_claims'])}")
    print(f"  output:                  {result.out_dir}")
    return 0


def cmd_verify(args):
    try:
        result = verify_run(args.run)
    except VerifyError as e:
        print(f"Bridge output NOT verified [{e.reason}]: {e}", file=sys.stderr)
        return 1
    print("Bridge output verified")
    print(f"  bridge_status: {result.bridge_status}")
    print(f"  case_id:       {result.case_id}")
    print(f"  evidence_id:   {result.evidence_id}")
    print(f"  claim_count:   {result.claim_count}")
    return 0


def cmd_selfcheck(args):
    import selfcheck
    return selfcheck.main([])


def build_parser():
    p = argparse.ArgumentParser(
        prog="bridge",
        description="Aletheia -> ODIN Bridge v0.1 — convert a verified Aletheia "
                    "evidence bundle into ODIN integrity/presence claims (not a "
                    "truth claim).")
    p.add_argument("--version", action="version",
                   version=f"Aletheia->ODIN Bridge v{versions.BRIDGE_VERSION}")
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("convert", help="convert an Aletheia bundle to ODIN claims")
    c.add_argument("--aletheia-root", required=True)
    c.add_argument("--odin-root", required=False, default=None)
    c.add_argument("--bundle", required=True)
    c.add_argument("--out", required=True)
    c.set_defaults(func=cmd_convert)

    v = sub.add_parser("verify", help="verify a bridge output folder")
    v.add_argument("--run", required=True)
    v.set_defaults(func=cmd_verify)

    s = sub.add_parser("selfcheck", help="run in-process invariant gates")
    s.set_defaults(func=cmd_selfcheck)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
