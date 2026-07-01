#!/bin/sh
# Verify the frozen Local v1 Candidate freeze record (roadmap Move 50).
# Expected PASS marker: LOCAL_V1_CANDIDATE_VERIFIED / verify_ok = true
# Usage:  sh tools/run_local_v1_verify.sh   (exit 0 on pass)
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PKG="$ROOT/freeze_record/local_v1_candidate_v01"
[ -f "$PKG/tools/verify_local_v1_candidate.py" ] || { echo "RESULT: FAIL — verifier script missing"; exit 2; }
( cd "$PKG" && python3 tools/verify_local_v1_candidate.py )
code=$?
find "$ROOT" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
[ "$code" -eq 0 ] && echo "RESULT: PASS — local v1 candidate verification" || echo "RESULT: FAIL — local v1 candidate verification (exit $code)"
exit "$code"
