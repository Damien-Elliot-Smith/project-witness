#!/bin/sh
# Independently verify the frozen full-stack component freeze (roadmap Move 45/46).
# Expected PASS marker: PROJECT_WITNESS_INDEPENDENT_VERIFICATION_PASSED / verify_ok = true
# Usage:  sh tools/run_independent_verify.sh   (exit 0 on pass)
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PKG="$ROOT/verify/independent_verification_script_v01"
FREEZE="artifacts/full_stack_component_version_freeze_v01.zip"
[ -f "$PKG/tools/independent_verify_project_witness.py" ] || { echo "RESULT: FAIL — verifier script missing"; exit 2; }
( cd "$PKG" && python3 tools/independent_verify_project_witness.py "$FREEZE" )
code=$?
find "$ROOT" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
[ "$code" -eq 0 ] && echo "RESULT: PASS — independent verification" || echo "RESULT: FAIL — independent verification (exit $code)"
exit "$code"
