#!/bin/sh
# Top-level handoff validation. Runs the major verifiers and summarizes.
# Fails closed: exits non-zero if ANY stage fails. Failure output is NOT hidden.
#
# Usage:  sh tools/validate_handoff.sh
ROOT=$(cd "$(dirname "$0")/.." && pwd)
TOOLS="$ROOT/tools"

overall=0
tmpsum=$(mktemp)

cleanup_generated_python_artifacts() {
  find "$ROOT" -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
  find "$ROOT" -type f -name '*.pyc' -delete 2>/dev/null || true
}

run_stage() {
  label="$1"
  script="$2"

  echo ""
  echo ">>> STAGE: $label  ($script)"
  echo "------------------------------------------"

  if [ ! -f "$TOOLS/$script" ]; then
    echo "MISSING: $TOOLS/$script"
    echo "$label MISSING" >> "$tmpsum"
    return
  fi

  # Remove generated Python cache artifacts between stages so validation is
  # repeatable from fresh extractions and after test runs.
  cleanup_generated_python_artifacts

  # Close stdin for child scripts so no child process can accidentally wait on or
  # consume wrapper input. Stages are called directly, not from a pipe-fed loop.
  sh "$TOOLS/$script" < /dev/null
  code=$?
  cleanup_generated_python_artifacts
  if [ "$code" -eq 0 ]; then
    echo "$label PASS" >> "$tmpsum"
  else
    echo "$label FAIL(exit $code)" >> "$tmpsum"
  fi
}

echo "=========================================="
echo " Project Witness - handoff validation"
echo "=========================================="

run_stage component_tests run_all_tests.sh
run_stage independent_verify run_independent_verify.sh
run_stage local_v1_verify run_local_v1_verify.sh
run_stage termux_verify run_termux_verify.sh
run_stage live_end_to_end_demo run_demo.sh

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

find "$ROOT" -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
find "$ROOT" -type f -name '*.pyc' -delete 2>/dev/null || true

echo "------------------------------------------"
if [ "$overall" -eq 0 ]; then
  echo "HANDOFF_VALIDATION: PASS"
  exit 0
else
  echo "HANDOFF_VALIDATION: FAIL"
  exit 1
fi
