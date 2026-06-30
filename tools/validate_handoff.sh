#!/bin/sh
# Top-level handoff validation. Runs the major verifiers and summarizes.
# Fails closed: exits non-zero if ANY stage fails. Failure output is NOT hidden.
#
# Usage:  sh tools/validate_handoff.sh
ROOT=$(cd "$(dirname "$0")/.." && pwd)
TOOLS="$ROOT/tools"

# Ordered list of "label|script" stages.
STAGES="
component_tests|run_all_tests.sh
independent_verify|run_independent_verify.sh
local_v1_verify|run_local_v1_verify.sh
termux_verify|run_termux_verify.sh
live_end_to_end_demo|run_demo.sh
"

overall=0
summary=""

echo "=========================================="
echo " Project Witness — handoff validation"
echo "=========================================="

# Use a temp file to accumulate the summary so the subshell loop changes persist.
tmpsum=$(mktemp)
echo "$STAGES" | while IFS='|' read -r label script; do
  [ -z "$label" ] && continue
  echo ""
  echo ">>> STAGE: $label  ($script)"
  echo "------------------------------------------"
  if [ ! -f "$TOOLS/$script" ]; then
    echo "MISSING: $TOOLS/$script"
    echo "$label MISSING" >> "$tmpsum"
    continue
  fi
  sh "$TOOLS/$script"
  code=$?
  if [ "$code" -eq 0 ]; then
    echo "$label PASS" >> "$tmpsum"
  else
    echo "$label FAIL(exit $code)" >> "$tmpsum"
  fi
done

echo ""
echo "=========================================="
echo " SUMMARY"
echo "=========================================="
while read -r line; do
  [ -z "$line" ] && continue
  echo "  $line"
  case "$line" in
    *" PASS") : ;;
    *) overall=1 ;;
  esac
done < "$tmpsum"
rm -f "$tmpsum"

find "$ROOT" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

echo "------------------------------------------"
if [ "$overall" -eq 0 ]; then
  echo "HANDOFF_VALIDATION: PASS"
  exit 0
else
  echo "HANDOFF_VALIDATION: FAIL"
  exit 1
fi
