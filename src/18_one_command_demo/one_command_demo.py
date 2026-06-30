#!/usr/bin/env python3
"""One-Command Demo Script v0.1.

A usability wrapper that runs and verifies the frozen Project Witness Connected
Demo v0.1 with one command, then records a small wrapper report. It only
orchestrates the Connected Demo's public CLI; it does not modify any frozen
component, invent statuses, or fake DEMO_COMPLETED.

One-Command Demo Script v0.1 runs and verifies the frozen Project Witness
Connected Demo v0.1. It does not prove evidence contents are true, does not prove
ODIN claims are true, and does not verify external reality.

Subcommands:
  run        -- run and verify the frozen Connected Demo, write a wrapper report
  selfcheck  -- in-process self-checks (fake demo output, no subprocess)
"""

import argparse
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from one_command_demo_lib import engine, versions
from one_command_demo_lib.errors import ONE_COMMAND_DEMO_COMPLETED
from one_command_demo_lib.runner import FakeConnectedDemoRunner


def cmd_run(args):
    status, _ = engine.run_wrapper(args.config, args.out)
    print(json.dumps({"wrapper_status": status, "out": args.out}, sort_keys=True))
    return 0 if status == ONE_COMMAND_DEMO_COMPLETED else 1


def _fake_config(tmp):
    root = os.path.join(tmp, "connected_demo_v01")
    os.makedirs(root, exist_ok=True)
    with open(os.path.join(root, "connected_demo.py"), "w", encoding="utf-8") as h:
        h.write("# placeholder for selfcheck only\n")
    demo_cfg = os.path.join(tmp, "connected_demo_config.json")
    with open(demo_cfg, "w", encoding="utf-8") as h:
        json.dump({}, h)
    cfg = os.path.join(tmp, "wrapper_config.json")
    with open(cfg, "w", encoding="utf-8") as h:
        json.dump({"config_version": versions.CONFIG_VERSION,
                   "connected_demo_root": root,
                   "connected_demo_config": demo_cfg}, h)
    return cfg


def cmd_selfcheck(args):
    failures = []
    tmp = tempfile.mkdtemp(prefix="ocd_selfcheck_")
    cfg = _fake_config(tmp)
    status, _ = engine.run_wrapper(cfg, os.path.join(tmp, "ok"),
                                   runner=FakeConnectedDemoRunner(honest=True))
    if status != ONE_COMMAND_DEMO_COMPLETED:
        failures.append("honest fake did not reach ONE_COMMAND_DEMO_COMPLETED")
    status, _ = engine.run_wrapper(cfg, os.path.join(tmp, "bad"),
                                   runner=FakeConnectedDemoRunner(honest=False))
    if status == ONE_COMMAND_DEMO_COMPLETED:
        failures.append("failing demo was not reported as a failure")
    status, _ = engine.run_wrapper(cfg, os.path.join(tmp, "notruth"),
                                   runner=FakeConnectedDemoRunner(honest=True,
                                                                  truth_valid=False))
    if status != "FAILED_TRUTH_BOUNDARY":
        failures.append("invalid truth boundary not caught")
    for f in failures:
        print("FAIL  " + f)
    if failures:
        return 1
    print("selfcheck: all gates passed")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        description="One-Command Demo Script v0.1")
    sub = parser.add_subparsers(dest="command")
    run = sub.add_parser("run", help="run and verify the frozen Connected Demo")
    run.add_argument("--config", required=True)
    run.add_argument("--out", required=True)
    run.set_defaults(func=cmd_run)
    sc = sub.add_parser("selfcheck", help="in-process self-checks")
    sc.set_defaults(func=cmd_selfcheck)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not getattr(args, "func", None):
        build_parser().print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
