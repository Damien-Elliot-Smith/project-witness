#!/bin/sh
# The verification instrument must not mutate the baseline it measures.
#
# ONE traversal (an earlier version ran six separate `find` passes over a
# 136MB tree and could exceed the gate's time budget).
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 2
ARTEFACTS=$(find . -path ./.git -prune -o \
    \( -name "*.pyc" -o -name "*.pyo" \
       -o -type d -name "__pycache__" \
       -o -type d -name ".pytest_cache" \
       -o -type d -name ".mypy_cache" \
       -o -type d -name ".ruff_cache" \) -print 2>/dev/null)
N=$(printf '%s' "$ARTEFACTS" | grep -c . 2>/dev/null || true)
echo "  cache/bytecode artefacts: ${N:-0}"
if [ "${N:-0}" -eq 0 ]; then
    echo "PACKAGE_HYGIENE_CHECK: PASS"
    exit 0
fi
printf '%s\n' "$ARTEFACTS" | head -8 | sed 's/^/  artefact: /'
echo "PACKAGE_HYGIENE_CHECK: FAIL"
exit 1
