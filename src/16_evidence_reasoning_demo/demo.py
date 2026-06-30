#!/usr/bin/env python3
# demo.py
# Evidence Reasoning Demo v0.1 CLI. Runs the local chain
#   evidence file -> Aletheia bundle -> Bridge -> ODIN -> verified demo report
# using the frozen components, then verifies the demo output. Proves the chain
# executes and verifies — never that the evidence contents are true.

import argparse
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from evidence_reasoning_demo.canonical import canonical_bytes  # noqa: E402
from evidence_reasoning_demo.checksums import format_checksums  # noqa: E402
from evidence_reasoning_demo.component_runner import (  # noqa: E402
    SubprocessComponentRunner)
from evidence_reasoning_demo.errors import (  # noqa: E402
    ValidationError, ComponentPathError, StepError, VerifyError)
from evidence_reasoning_demo.report import build_report  # noqa: E402
from evidence_reasoning_demo.steps import all_completed_steps  # noqa: E402
from evidence_reasoning_demo.validation import (  # noqa: E402
    validate_id, validate_source_file, sha256_bytes, sha256_file)
from evidence_reasoning_demo.verifier import verify_run  # noqa: E402
from evidence_reasoning_demo import versions  # noqa: E402

import json  # noqa: E402


class RunResult:
    __slots__ = ("out_dir", "report")

    def __init__(self, out_dir, report):
        self.out_dir = out_dir
        self.report = report


def _write_bytes(path, data: bytes):
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def run_demo(*, evidence_file, case_id, evidence_id, aletheia_root, bridge_root,
             odin_root, out_dir, runner=None):
    """Run the full chain. Raises ValidationError/ComponentPathError/StepError on
    failure. `runner` is injectable for tests (defaults to the real subprocess
    runner)."""
    # 1-2. Validate IDs.
    validate_id(case_id, label="case_id")
    validate_id(evidence_id, label="evidence_id")
    # 3-5. Validate the evidence source.
    validate_source_file(evidence_file)

    # 6. Refuse a non-empty output dir.
    if os.path.isdir(out_dir) and os.listdir(out_dir):
        raise ComponentPathError("OUTPUT_DIR_NOT_EMPTY",
                                 f"output directory is not empty: {out_dir!r}")

    # 7-9. Component roots exist (only required for the real runner; the injected
    # fake does not need them, but we still check when using the real runner).
    if runner is None:
        for label, root, reason in (("Aletheia", aletheia_root, "ALETHEIA_ROOT_MISSING"),
                                    ("Bridge", bridge_root, "BRIDGE_ROOT_MISSING"),
                                    ("ODIN", odin_root, "ODIN_ROOT_MISSING")):
            if not (isinstance(root, str) and os.path.isdir(root)):
                raise ComponentPathError(reason, f"{label} root not found: {root!r}")
        runner = SubprocessComponentRunner(
            aletheia_root=aletheia_root, bridge_root=bridge_root,
            odin_root=odin_root)

    os.makedirs(out_dir, exist_ok=True)
    bundle_dir = os.path.join(out_dir, versions.ALETHEIA_BUNDLE_DIR)
    bridge_dir = os.path.join(out_dir, versions.BRIDGE_OUTPUT_DIR)
    odin_dir = os.path.join(out_dir, versions.ODIN_OUTPUT_DIR)

    # Steps 10-15: run the chain in order. StepError short-circuits the rest.
    runner.aletheia_bundle(evidence_file, case_id, evidence_id, bundle_dir)
    runner.aletheia_verify(bundle_dir)
    runner.bridge_convert(aletheia_root, odin_root, bundle_dir, bridge_dir)
    runner.bridge_verify(bridge_dir)

    claims_path = os.path.join(bridge_dir, "odin_claims.json")
    runner.odin_reason(claims_path, odin_dir)
    runner.odin_verify(odin_dir)

    # Read the component outputs (preserved exactly; never rewritten).
    manifest = _read_json(os.path.join(bundle_dir, "evidence_manifest.json"))
    bridge_report = _read_json(os.path.join(bridge_dir, "bridge_report.json"))
    odin_report = _read_json(os.path.join(odin_dir, "reasoning_report.json"))

    # 16-18. Write demo_report, demo_steps, demo_checksums.
    report = build_report(
        case_id=case_id, evidence_id=evidence_id,
        aletheia_status=manifest["evidence_status"],
        bridge_status=bridge_report["bridge_status"],
        odin_reasoning_status=odin_report["reasoning_status"],
        odin_claim_count=bridge_report.get("odin_claim_count",
                                           len(bridge_report.get("generated_claims", []))),
        generated_claims=bridge_report.get("generated_claims", []))
    steps = all_completed_steps(case_id)

    report_bytes = canonical_bytes(report)
    steps_bytes = canonical_bytes(steps)
    _write_bytes(os.path.join(out_dir, versions.DEMO_REPORT_NAME), report_bytes)
    _write_bytes(os.path.join(out_dir, versions.DEMO_STEPS_NAME), steps_bytes)

    checksums = format_checksums(
        demo_report_sha256=sha256_bytes(report_bytes),
        demo_steps_sha256=sha256_bytes(steps_bytes),
        aletheia_manifest_sha256=sha256_file(
            os.path.join(out_dir, versions.ALETHEIA_MANIFEST_REL)),
        bridge_report_sha256=sha256_file(
            os.path.join(out_dir, versions.BRIDGE_REPORT_REL)),
        odin_reasoning_report_sha256=sha256_file(
            os.path.join(out_dir, versions.ODIN_REASONING_REPORT_REL)))
    _write_bytes(os.path.join(out_dir, versions.CHECKSUMS_NAME), checksums)

    return RunResult(out_dir, report)


def cmd_run(args, runner=None):
    try:
        result = run_demo(
            evidence_file=args.evidence_file, case_id=args.case_id,
            evidence_id=args.evidence_id, aletheia_root=args.aletheia_root,
            bridge_root=args.bridge_root, odin_root=args.odin_root,
            out_dir=args.out, runner=runner)
    except ValidationError as e:
        print(f"REFUSED {versions.FAILED_INPUT_VALIDATION} [{e.reason}]: {e}",
              file=sys.stderr)
        return 2
    except ComponentPathError as e:
        print(f"REFUSED [{e.reason}]: {e}", file=sys.stderr)
        return 2
    except StepError as e:
        print(f"DEMO {e.demo_status}: {e}", file=sys.stderr)
        return 1
    r = result.report
    print(f"DEMO {r['demo_status']}")
    print(f"  case_id:               {r['case_id']}")
    print(f"  evidence_id:           {r['evidence_id']}")
    print(f"  aletheia_status:       {r['aletheia_status']}")
    print(f"  bridge_status:         {r['bridge_status']}")
    print(f"  odin_reasoning_status: {r['odin_reasoning_status']}")
    print(f"  odin_claim_count:      {r['odin_claim_count']}")
    print(f"  generated_claims:      {', '.join(r['generated_claims'])}")
    print(f"  output:                {result.out_dir}")
    return 0


def cmd_verify(args):
    try:
        result = verify_run(args.run)
    except VerifyError as e:
        print(f"Demo output NOT verified [{e.reason}]: {e}", file=sys.stderr)
        return 1
    print("Demo output verified")
    print(f"  demo_status:           {result.demo_status}")
    print(f"  case_id:               {result.case_id}")
    print(f"  evidence_id:           {result.evidence_id}")
    print(f"  odin_reasoning_status: {result.odin_reasoning_status}")
    return 0


def cmd_selfcheck(args):
    import selfcheck
    return selfcheck.main([])


def build_parser():
    p = argparse.ArgumentParser(
        prog="demo",
        description="Evidence Reasoning Demo v0.1 — run the local "
                    "evidence-integrity reasoning chain and verify it (not a truth "
                    "claim).")
    p.add_argument("--version", action="version",
                   version=f"Evidence Reasoning Demo v{versions.DEMO_VERSION}")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("run", help="run the chain and write a verified demo folder")
    r.add_argument("--evidence-file", required=True)
    r.add_argument("--case-id", required=True)
    r.add_argument("--evidence-id", required=True)
    r.add_argument("--aletheia-root", required=True)
    r.add_argument("--bridge-root", required=True)
    r.add_argument("--odin-root", required=True)
    r.add_argument("--out", required=True)
    r.set_defaults(func=cmd_run)

    v = sub.add_parser("verify", help="verify a demo output folder")
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
