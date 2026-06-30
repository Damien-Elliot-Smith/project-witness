#!/bin/sh
# Move 52 — verify the Linux desktop run instructions are usable on this machine.
# Checks that the instruction document, the required commands, and the required
# scripts are all present. Fails closed (non-zero) if anything required is missing.
#
# Usage:
#   sh tools/check_linux_desktop_instructions.sh          # presence + command checks
#   sh tools/check_linux_desktop_instructions.sh --full   # also run validate_handoff.sh
#
# By default this does NOT run validate_handoff.sh, to avoid duplicating the full
# test/verify/demo work. Pass --full to run it as well.

ROOT=$(cd "$(dirname "$0")/.." && pwd)
RUN_FULL=0
[ "$1" = "--full" ] && RUN_FULL=1

missing=0

note_ok()      { printf "  OK    %s\n" "$1"; }
note_missing() { printf "  MISS  %s\n" "$1"; missing=$((missing + 1)); }

echo "Linux desktop instruction check"
echo "-------------------------------"

# 1. Instruction document
echo "Document:"
if [ -f "$ROOT/LINUX_DESKTOP_RUN_INSTRUCTIONS.md" ]; then
  note_ok "LINUX_DESKTOP_RUN_INSTRUCTIONS.md"
else
  note_missing "LINUX_DESKTOP_RUN_INSTRUCTIONS.md"
fi

# 2. Required commands
echo "Commands:"
for c in python3 sh unzip sha256sum; do
  if command -v "$c" >/dev/null 2>&1; then
    note_ok "command: $c"
  else
    note_missing "command: $c"
  fi
done

# 3. Required scripts
echo "Scripts:"
for s in validate_handoff.sh run_all_tests.sh run_independent_verify.sh \
         run_local_v1_verify.sh run_termux_verify.sh run_demo.sh; do
  if [ -f "$ROOT/tools/$s" ]; then
    note_ok "tools/$s"
  else
    note_missing "tools/$s"
  fi
done

# Fail closed before any optional heavy work if anything required is missing.
if [ "$missing" -ne 0 ]; then
  echo "-------------------------------"
  echo "LINUX_DESKTOP_INSTRUCTIONS_CHECK: FAIL ($missing required item(s) missing)"
  exit 1
fi

# 4. Optional full validation
if [ "$RUN_FULL" -eq 1 ]; then
  echo "-------------------------------"
  echo "Running full validation (validate_handoff.sh)..."
  sh "$ROOT/tools/validate_handoff.sh"
  code=$?
  if [ "$code" -ne 0 ]; then
    echo "LINUX_DESKTOP_INSTRUCTIONS_CHECK: FAIL (validate_handoff exit $code)"
    exit 1
  fi
fi

echo "-------------------------------"
echo "LINUX_DESKTOP_INSTRUCTIONS_CHECK: PASS"
exit 0
