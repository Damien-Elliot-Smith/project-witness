#!/bin/sh
# Stable entry point for the live end-to-end pipeline demo.
# Delegates to run_live_e2e_demo.sh. Expected end: COMPANION_COMPLETED / verify_ok: true
# Usage:  sh tools/run_demo.sh
ROOT=$(cd "$(dirname "$0")/.." && pwd)
exec sh "$ROOT/tools/run_live_e2e_demo.sh"
