#!/usr/bin/env python3
# sentinel.py
# Command-line interface for Sentinel Core v0.2.2.
#
# This CLI is a thin operator shell around the deterministic core. It does NOT
# accept natural language: every action is expressed as a structured request,
# either via explicit flags (which this script assembles into the exact schema)
# or by passing a JSON request file. No natural-language parsing, no LLM, no
# shell execution happens anywhere.
#
# Commands:
#   create   Build one CREATE_DIRECTORY request, process it, append to a run.
#   close    Close an open run (emits the final receipt and run seal).
#   replay   Re-derive a saved run through a fresh kernel and report.
#   inspect  Print a human-readable summary of a saved run file.

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from sentinel_core.action_schema import ACTION_SCHEMA_VERSION  # noqa: E402
from sentinel_core.errors import SentinelError  # noqa: E402
from sentinel_core.journal import Journal  # noqa: E402
from sentinel_core.kernel import Kernel  # noqa: E402
from sentinel_core.manifest import build_manifest, load_run_file  # noqa: E402
from sentinel_core.persistence import AtomicFileBackend  # noqa: E402
from sentinel_core.receipts import ReceiptChain  # noqa: E402
from sentinel_core.replay import replay_from_path  # noqa: E402
from sentinel_core.run_loader import open_run_for_append  # noqa: E402
from sentinel_core.run_seal import RUN_SEAL_FIELD  # noqa: E402
from sentinel_core.versions import PACKAGE_VERSION  # noqa: E402


def _load_or_create_kernel(run_path, run_id, allowed_root_arg):
    """Open an existing run for append, or create a fresh one.

    The manifest's allowed_root is AUTHORITATIVE. For an existing run, a
    supplied --allowed-root must canonicalise to the same real path as the
    manifest root, otherwise we refuse rather than silently re-rooting.
    For a new run, --allowed-root is required and is recorded (absolute) in
    the manifest.
    """
    if os.path.exists(run_path):
        # v0.1.2: ALL append paths go through the validated loader. It verifies
        # the manifest, recomputes every receipt hash, verifies chain
        # structure, refuses any run containing a close receipt (even with the
        # seal deleted), refuses sealed runs, and derives the session state
        # from the chain head. No kernel exists until the run proves valid.
        kernel = open_run_for_append(run_path)
        if allowed_root_arg is not None:
            supplied = os.path.realpath(os.path.abspath(allowed_root_arg))
            configured = os.path.realpath(kernel.manifest["allowed_root"])
            if supplied != configured:
                raise SystemExit(
                    f"--allowed-root {supplied!r} does not match the run's "
                    f"configured root {configured!r}. The manifest root is "
                    f"authoritative; omit --allowed-root when appending.")
        return kernel
    if allowed_root_arg is None:
        raise SystemExit("--allowed-root is required when creating a new run.")
    run_data = build_manifest(run_id, os.path.abspath(allowed_root_arg))
    return Kernel(Journal(AtomicFileBackend(run_path), ReceiptChain(run_id), run_data))


def cmd_create(args):
    # v1.1.0: the request carries NO allowed_root. --allowed-root configures
    # the run manifest when a NEW run is created; for an existing run the
    # manifest root is authoritative and --allowed-root must be absent or
    # match it exactly after canonicalisation.
    request = {
        "request_id": args.request_id,
        "action_type": "CREATE_DIRECTORY",
        "target_path": args.target_path,
        "dry_run": bool(args.dry_run),
        "preconditions": ["target_absent", "parent_exists", "inside_allowed_root"],
        "postconditions": ["target_exists", "target_is_directory"],
        "schema_version": ACTION_SCHEMA_VERSION,
    }
    kernel = _load_or_create_kernel(args.run, args.run_id, args.allowed_root)
    receipt = kernel.process(request)
    print(receipt.summary_line())
    print(f"  reason: {receipt.reason_code}")
    return 0


def cmd_create_from_file(args):
    raw = load_run_file(args.request_file)  # reuses hostile-JSON-safe loader
    kernel = _load_or_create_kernel(args.run, args.run_id, args.allowed_root)
    receipt = kernel.process(raw)
    print(receipt.summary_line())
    print(f"  reason: {receipt.reason_code}")
    return 0


def cmd_close(args):
    if not os.path.exists(args.run):
        raise SystemExit(f"Run file not found: {args.run}")
    # v0.1.2: closing also goes through the validated loader, so a tampered or
    # already-closed run (including one with a deleted seal) cannot receive a
    # second close receipt.
    kernel = open_run_for_append(args.run)
    receipt = kernel.close_session()
    print(f"Closed run. Final receipt: {receipt.summary_line()}")
    return 0


def cmd_replay(args):
    result = replay_from_path(args.run, allow_open=args.allow_open)
    print(result.report)
    # Exit 0 for PASS_STRICT and PASS_WITH_ENVIRONMENTAL_EXCEPTIONS (the run is
    # accepted); non-zero for FAIL and REPLAY_INCOMPATIBLE. The verdict text
    # already distinguishes the two PASS categories.
    return 0 if result.ok else 1


def cmd_inspect(args):
    raw = load_run_file(args.run)
    manifest = raw.get("manifest", {})
    receipts = raw.get("receipts", [])
    seal = raw.get(RUN_SEAL_FIELD)
    print(f"Run ID:       {manifest.get('run_id')}")
    print(f"allowed_root: {manifest.get('allowed_root')}")
    print(f"impl_version: {manifest.get('impl_version')}")
    print(f"receipts:     {len(receipts)}")
    print(f"closed:       {seal is not None}")
    print("-" * 64)
    for r in receipts:
        rid = r.get("request", {}).get("request_id", "?") if isinstance(r.get("request"), dict) else "?"
        ref = f" <-#{r.get('intent_receipt_id'):04d}" if r.get("intent_receipt_id") is not None else ""
        print(f"  #{r.get('receipt_id'):04d} {r.get('stage', '?'):13s} {r.get('decision'):7s} "
              f"{r.get('reason_code')} req={rid} exec={r.get('executed')}{ref}")
    return 0


def build_parser():
    p = argparse.ArgumentParser(
        prog="sentinel",
        description="Sentinel Core v0.2.2 — deterministic CREATE_DIRECTORY action gate.")
    p.add_argument("--version", action="version", version=f"Sentinel Core v{PACKAGE_VERSION}")
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("create", help="Process one CREATE_DIRECTORY request.")
    c.add_argument("--run", required=True, help="Path to the run file (created if absent).")
    c.add_argument("--run-id", default="run", help="Run id when creating a new run.")
    c.add_argument("--request-id", required=True)
    c.add_argument("--target-path", required=True)
    c.add_argument("--allowed-root", default=None,
                   help="Run boundary. Required when creating a NEW run; for an "
                        "existing run the manifest root is authoritative and this "
                        "must be omitted or match it.")
    c.add_argument("--dry-run", action="store_true")
    c.set_defaults(func=cmd_create)

    cf = sub.add_parser("create-from-file", help="Process a JSON request file.")
    cf.add_argument("--run", required=True)
    cf.add_argument("--run-id", default="run")
    cf.add_argument("--request-file", required=True)
    cf.add_argument("--allowed-root", default=None,
                    help="Run boundary; required only when creating a new run.")
    cf.set_defaults(func=cmd_create_from_file)

    cl = sub.add_parser("close", help="Close an open run and write its seal.")
    cl.add_argument("--run", required=True)
    cl.set_defaults(func=cmd_close)

    r = sub.add_parser("replay", help="Re-derive a saved run through a fresh kernel.")
    r.add_argument("--run", required=True)
    r.add_argument("--allow-open", action="store_true",
                   help="Permit replay of an unsealed (open) run.")
    r.set_defaults(func=cmd_replay)

    i = sub.add_parser("inspect", help="Summarise a saved run file.")
    i.add_argument("--run", required=True)
    i.set_defaults(func=cmd_inspect)
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except SentinelError as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
