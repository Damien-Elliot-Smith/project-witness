#!/bin/sh
# check_src_matches_release.sh — Move 70.6 reconciliation checker.
#
# Repairs the divergence class found by external review on 2026-07-03:
# the live top-level src/ had silently diverged from the src/ inside the
# declared final Roadmap One release package (18 file differences), while
# every existing checker passed, because nothing compared the two.
#
# Rule: the authoritative Roadmap One source is the src/ inside the
# release zip that CURRENT_RELEASE_STATE.md declares. This check compares
# the live top-level src/ against it by path and SHA-256 and fails on:
#   - files missing from live src/
#   - extra files present in live src/
#   - any file whose content differs
#
# Python bytecode (__pycache__/, *.pyc) is excluded on both sides:
# bytecode is interpreter-version-specific, non-deterministic, and per
# project packaging rules must never be part of a source comparison.
#
# The declared zip path is read from CURRENT_RELEASE_STATE.md so the
# state document remains the single source of truth. If the declaration
# moves to a new release, this check follows it automatically.

set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 2

STATE="CURRENT_RELEASE_STATE.md"
if [ ! -f "$STATE" ]; then
    echo "missing $STATE"
    echo "SRC_MATCHES_RELEASE_CHECK: FAIL"
    exit 1
fi

# The comparison target is resolved from CURRENT_RELEASE_STATE.md in two
# tiers, so repairs after Roadmap One can declare a new current package
# without rewriting the historical Roadmap One declaration:
#   1. an explicit "Current source release package:" declaration, if present
#   2. otherwise, the first releases/*.zip path in the document (the
#      declared final Roadmap One package)

ZIP_REL=$(grep -A 2 '^Current source release package:' "$STATE" \
    | grep -o 'releases/[A-Za-z0-9_/.-]*\.zip' | head -n 1)
if [ -z "$ZIP_REL" ]; then
    ZIP_REL=$(grep -o 'releases/[A-Za-z0-9_/.-]*\.zip' "$STATE" | head -n 1)
fi
if [ -z "$ZIP_REL" ] || [ ! -f "$ZIP_REL" ]; then
    echo "declared release zip not found: '$ZIP_REL'"
    echo "SRC_MATCHES_RELEASE_CHECK: FAIL"
    exit 1
fi
echo "declared release package: $ZIP_REL"

TMP=$(mktemp -d) || exit 2
trap 'rm -rf "$TMP"' EXIT

unzip -q "$ZIP_REL" -d "$TMP" || {
    echo "could not extract declared release zip"
    echo "SRC_MATCHES_RELEASE_CHECK: FAIL"
    exit 1
}

REL_SRC=$(find "$TMP" -maxdepth 2 -type d -name src | head -n 1)
if [ -z "$REL_SRC" ]; then
    echo "no src/ directory inside declared release zip"
    echo "SRC_MATCHES_RELEASE_CHECK: FAIL"
    exit 1
fi

list_files() {
    (cd "$1" && find . -type f ! -name '*.pyc' ! -path '*__pycache__*' \
        | sed 's|^\./||' | sort)
}

list_files "src"      > "$TMP/live.list"
list_files "$REL_SRC" > "$TMP/rel.list"

fail=0

MISSING=$(comm -13 "$TMP/live.list" "$TMP/rel.list")
if [ -n "$MISSING" ]; then
    echo "MISSING from live src/ (present in declared release):"
    printf '%s\n' "$MISSING" | sed 's/^/  /'
    fail=1
fi

EXTRA=$(comm -23 "$TMP/live.list" "$TMP/rel.list")
if [ -n "$EXTRA" ]; then
    echo "EXTRA in live src/ (absent from declared release):"
    printf '%s\n' "$EXTRA" | sed 's/^/  /'
    fail=1
fi

checked=0
changed=0
comm -12 "$TMP/live.list" "$TMP/rel.list" > "$TMP/common.list"
while IFS= read -r f; do
    a=$(sha256sum "src/$f" | cut -d' ' -f1)
    b=$(sha256sum "$REL_SRC/$f" | cut -d' ' -f1)
    if [ "$a" != "$b" ]; then
        echo "CHANGED content: src/$f"
        changed=$((changed + 1))
        fail=1
    fi
    checked=$((checked + 1))
done < "$TMP/common.list"

echo "files compared: $checked  changed: $changed"
if [ "$fail" -ne 0 ]; then
    echo "SRC_MATCHES_RELEASE_CHECK: FAIL"
    exit 1
fi
echo "SRC_MATCHES_RELEASE_CHECK: PASS"
exit 0
