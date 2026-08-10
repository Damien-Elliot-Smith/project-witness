#!/bin/sh
# Move 55/60 - private reviewer package check.

ROOT=$(cd "$(dirname "$0")/.." && pwd)
missing=0
ok() { printf "  OK    %s\n" "$1"; }
bad() { printf "  FAIL  %s\n" "$1"; missing=$((missing + 1)); }
contains() { file="$1"; pattern="$2"; label="$3"; if grep -Fq "$pattern" "$file"; then ok "$label"; else bad "$label"; fi; }
forbid() { file="$1"; pattern="$2"; label="$3"; if grep -Fq "$pattern" "$file"; then bad "$label"; else ok "$label"; fi; }

# Move 70.5: marker updated to the Roadmap One completion state.
# The authoritative current-state checker is tools/check_current_release_state.sh.
current_marker="Project Witness Roadmap One, Steps 1-70, is complete as a local review/demo stack."
echo "Private reviewer package check"
echo "------------------------------"
PKG="$ROOT/PRIVATE_REVIEWER_PACKAGE.md"; TPL="$ROOT/PRIVATE_REVIEWER_FEEDBACK_TEMPLATE.md"
[ -f "$PKG" ] && ok "PRIVATE_REVIEWER_PACKAGE.md" || bad "PRIVATE_REVIEWER_PACKAGE.md"
[ -f "$TPL" ] && ok "PRIVATE_REVIEWER_FEEDBACK_TEMPLATE.md" || bad "PRIVATE_REVIEWER_FEEDBACK_TEMPLATE.md"
if [ -f "$PKG" ]; then
contains "$PKG" "local review/demo stack" "states local review/demo stack boundary"
contains "$PKG" "$current_marker" "has current marker"
contains "$PKG" "NO_EXTERNAL_FEEDBACK_RECORDED" "does not claim reviewer approval"
contains "$PKG" "Project_Witness_WORKING_STACK_v20_MOVE_70.zip" "references current package zip"
contains "$PKG" "sh tools/check_local_v1_release.sh" "includes release check command"
fi
echo "------------------------------"
if [ "$missing" -eq 0 ]; then echo "PRIVATE_REVIEWER_PACKAGE_CHECK: PASS"; exit 0; fi
echo "PRIVATE_REVIEWER_PACKAGE_CHECK: FAIL ($missing required item(s) missing or inconsistent)"; exit 1
