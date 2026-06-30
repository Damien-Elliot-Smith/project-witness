#!/usr/bin/env python3
"""Verify a One-Command Demo wrapper output folder. Read-only; no subprocess."""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from one_command_demo_lib import verifier
from one_command_demo_lib.errors import VerifyError


def main(argv=None):
    parser = argparse.ArgumentParser(description="Verify a One-Command Demo output")
    parser.add_argument("--run", required=True)
    args = parser.parse_args(argv)
    try:
        verifier.verify(args.run)
    except VerifyError as exc:
        print(json.dumps({"verify_ok": False, "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({"verify_ok": True}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
