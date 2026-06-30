#!/bin/sh
# Move 53 — verify the Windows notes are present, honest, and point to the
# verified Linux/WSL2 path. Content checks are intentionally about substance:
# the notes must mention WSL, must not claim a guaranteed native port (unless
# directly tested), and must point at the Linux desktop instructions.
# Fails closed (non-zero) if anything required is missing.
#
# POSIX sh; runs from the current verified environment.
# Usage:  sh tools/check_windows_notes.sh

ROOT=$(cd "$(dirname "$0")/.." && pwd)
DOC="$ROOT/WINDOWS_NOTES.md"
missing=0

ok()   { printf "  OK    %s\n" "$1"; }
miss() { printf "  MISS  %s\n" "$1"; missing=$((missing + 1)); }

echo "Windows notes check"
echo "-------------------"

# 1. Document exists
if [ -f "$DOC" ]; then
  ok "WINDOWS_NOTES.md exists"
else
  miss "WINDOWS_NOTES.md exists"
  echo "-------------------"
  echo "WINDOWS_NOTES_CHECK: FAIL ($missing required item(s) missing)"
  exit 1
fi

# 2. Mentions WSL / WSL2
if grep -iq 'wsl' "$DOC"; then ok "mentions WSL/WSL2"; else miss "mentions WSL/WSL2"; fi

# 3. States this is notes/readiness, not a guaranteed native port unless tested
if grep -iqE 'readiness' "$DOC" \
   && grep -iqE 'not[^.]*native|native[^.]*not|not been[^.]*tested' "$DOC"; then
  ok "states notes/readiness, native not guaranteed unless tested"
else
  miss "states notes/readiness, native not guaranteed unless tested"
fi

# 4. Points to the Linux desktop instructions
if grep -Fq 'LINUX_DESKTOP_RUN_INSTRUCTIONS.md' "$DOC"; then
  ok "points to LINUX_DESKTOP_RUN_INSTRUCTIONS.md"
else
  miss "points to LINUX_DESKTOP_RUN_INSTRUCTIONS.md"
fi

# 5. Required existing scripts still present
echo "Scripts:"
for s in validate_handoff.sh run_all_tests.sh run_demo.sh; do
  if [ -f "$ROOT/tools/$s" ]; then ok "tools/$s"; else miss "tools/$s"; fi
done

echo "-------------------"
if [ "$missing" -eq 0 ]; then
  echo "WINDOWS_NOTES_CHECK: PASS"
  exit 0
fi
echo "WINDOWS_NOTES_CHECK: FAIL ($missing required item(s) missing)"
exit 1
