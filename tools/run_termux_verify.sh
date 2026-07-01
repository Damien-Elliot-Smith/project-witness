#!/bin/sh
# Verify the frozen Termux Run Instructions package (roadmap Move 51).
# Expected PASS marker: TERMUX_RUN_INSTRUCTIONS_VERIFIED / verify_ok = true
# Usage:  sh tools/run_termux_verify.sh   (exit 0 on pass)
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PKG="$ROOT/freeze_record/termux_run_instructions_v01"
[ -f "$PKG/tools/verify_termux_run_instructions.py" ] || { echo "RESULT: FAIL — verifier script missing"; exit 2; }
( cd "$PKG" && python3 tools/verify_termux_run_instructions.py )
code=$?
find "$ROOT" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
[ "$code" -eq 0 ] && echo "RESULT: PASS — termux instructions verification" || echo "RESULT: FAIL — termux instructions verification (exit $code)"
exit "$code"
