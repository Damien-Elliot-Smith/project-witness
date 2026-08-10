#!/bin/sh
# Run every component's unittest suite reliably.
# Pass/fail is decided by the Python unittest EXIT CODE, never by text matching.
# Full output is captured per component and printed in full only when that
# component fails. Standard library only; no network; no pytest.
#
# Usage:  sh tools/run_all_tests.sh
# Exit:   0 only if every component suite passes; non-zero otherwise.

ROOT=$(cd "$(dirname "$0")/.." && pwd)
SRC="$ROOT/src"

comps=0
passed=0
failed=0
total=0
count_complete=1          # set to 0 if any "Ran N" line cannot be parsed
failed_names=""

for d in "$SRC"/*/; do
  [ -d "$d" ] || continue
  d=${d%/}
  name=$(basename "$d")

  tdir=$(find "$d" -path "*/tests" -type d 2>/dev/null | head -1)
  [ -z "$tdir" ] && continue
  comps=$((comps + 1))
  pkgroot=$(dirname "$tdir")

  # Capture full output AND exit code. A non-zero code must not abort the loop,
  # so we deliberately do not use `set -e`.
  out=$(cd "$pkgroot" && python3 -m unittest discover -s tests 2>&1)
  code=$?

  # Best-effort test count from the FULL output (first "Ran N tests" line).
  # A missing/unparseable count must never crash the script.
  n=$(printf '%s\n' "$out" | sed -n 's/^Ran \([0-9][0-9]*\) test.*/\1/p' | head -1)
  if [ -n "$n" ]; then
    total=$((total + n))
  else
    count_complete=0
  fi

  if [ "$code" -eq 0 ]; then
    passed=$((passed + 1))
    printf "  PASS  %-32s %s tests\n" "$name" "${n:-?}"
  else
    failed=$((failed + 1))
    failed_names="$failed_names $name"
    printf "  FAIL  %-32s (unittest exit %s)\n" "$name" "$code"
    # Show the full failure output; do not hide it.
    printf '%s\n' "$out" | sed 's/^/      | /'
  fi
done

echo ""
echo "----------------------------------------"
echo "Components checked: $comps"
echo "Components passed:  $passed"
echo "Components failed:  $failed"
if [ "$count_complete" -eq 1 ]; then
  echo "Total tests detected: $total"
else
  echo "Total tests detected: $total (partial: one or more counts could not be parsed)"
fi
echo "----------------------------------------"

# Bytecode hygiene (project convention): strip anything the run created.
find "$ROOT" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find "$ROOT" -type f -name '*.pyc' -delete 2>/dev/null || true

if [ "$comps" -eq 0 ]; then
  echo "RESULT: FAIL — no component test suites found under src/"
  exit 2
fi
if [ "$failed" -eq 0 ]; then
  echo "RESULT: PASS — ALL_COMPONENT_TESTS_PASSED"
  exit 0
fi
echo "RESULT: FAIL — failing components:$failed_names"
exit 1
