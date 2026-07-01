#!/bin/sh
# Move 57/60 - five-minute demo script check.

ROOT=$(cd "$(dirname "$0")/.." && pwd)
missing=0
ok() { printf "  OK    %s\n" "$1"; }
bad() { printf "  FAIL  %s\n" "$1"; missing=$((missing + 1)); }
contains() { file="$1"; pattern="$2"; label="$3"; if grep -Fq "$pattern" "$file"; then ok "$label"; else bad "$label"; fi; }
forbid() { file="$1"; pattern="$2"; label="$3"; if grep -Fq "$pattern" "$file"; then bad "$label"; else ok "$label"; fi; }

current_marker="Roadmap complete through Move 60; Moves 61-70 remain future work"
echo "Five-minute demo script check"
echo "-----------------------------"
SCRIPT="$ROOT/FIVE_MINUTE_DEMO_SCRIPT.md"; [ -f "$SCRIPT" ] && ok "FIVE_MINUTE_DEMO_SCRIPT.md" || bad "FIVE_MINUTE_DEMO_SCRIPT.md"
if [ -f "$SCRIPT" ]; then
contains "$SCRIPT" "Local v1 Release" "states Local v1 Release"
contains "$SCRIPT" "$current_marker" "has current marker"
contains "$SCRIPT" "sha256sum -c Project_Witness_WORKING_STACK_v11_MOVE_60.zip.sha256" "includes current checksum command"
contains "$SCRIPT" "sh tools/check_local_v1_release.sh" "includes release check"
contains "$SCRIPT" "does not prove external truth" "states no external truth"
contains "$SCRIPT" "The 70-step roadmap is not complete" "prevents roadmap-complete overclaim"
fi
echo "-----------------------------"
if [ "$missing" -eq 0 ]; then echo "FIVE_MINUTE_DEMO_SCRIPT_CHECK: PASS"; exit 0; fi
echo "FIVE_MINUTE_DEMO_SCRIPT_CHECK: FAIL ($missing required item(s) missing or inconsistent)"; exit 1
