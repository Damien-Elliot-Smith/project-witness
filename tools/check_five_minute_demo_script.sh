#!/bin/sh
# Move 57/60 - five-minute demo script check.

ROOT=$(cd "$(dirname "$0")/.." && pwd)
missing=0
ok() { printf "  OK    %s\n" "$1"; }
bad() { printf "  FAIL  %s\n" "$1"; missing=$((missing + 1)); }
contains() { file="$1"; pattern="$2"; label="$3"; if grep -Fq "$pattern" "$file"; then ok "$label"; else bad "$label"; fi; }
forbid() { file="$1"; pattern="$2"; label="$3"; if grep -Fq "$pattern" "$file"; then bad "$label"; else ok "$label"; fi; }

# Move 70.5: marker updated to the Roadmap One completion state.
# The authoritative current-state checker is tools/check_current_release_state.sh.
current_marker="Project Witness Roadmap One, Steps 1-70, is complete as a local review/demo stack."
echo "Five-minute demo script check"
echo "-----------------------------"
SCRIPT="$ROOT/FIVE_MINUTE_DEMO_SCRIPT.md"; [ -f "$SCRIPT" ] && ok "FIVE_MINUTE_DEMO_SCRIPT.md" || bad "FIVE_MINUTE_DEMO_SCRIPT.md"
if [ -f "$SCRIPT" ]; then
contains "$SCRIPT" "local review/demo stack" "states local review/demo stack boundary"
contains "$SCRIPT" "$current_marker" "has current marker"
contains "$SCRIPT" "sha256sum -c Project_Witness_WORKING_STACK_v20_MOVE_70.zip.sha256" "includes current checksum command"
contains "$SCRIPT" "sh tools/check_local_v1_release.sh" "includes release check"
contains "$SCRIPT" "does not prove external truth" "states no external truth"
# Move 74 repair: this rule previously required "Part Two has not
# started", which became a false-state enforcement (a stale-checker
# external-review finding) once Moves 72-73 were adopted. It now
# enforces the current honest state.
contains "$SCRIPT" "Part Two has started" "states Part Two has started"
contains "$SCRIPT" "Move 79 (verification-only Python/Rust agreement harness) is the current candidate" "Move 79 marked candidate only"
contains "$SCRIPT" "no full bundle verification capability exists or is claimed" "no full-verification overclaim"
contains "$SCRIPT" "not production-ready" "no production-ready claim"
contains "$SCRIPT" "does not prove real-world truth" "no external truth claim"
forbid "$SCRIPT" "Part Two has not started" "free of stale Part-Two-not-started claim"
fi
echo "-----------------------------"
if [ "$missing" -eq 0 ]; then echo "FIVE_MINUTE_DEMO_SCRIPT_CHECK: PASS"; exit 0; fi
echo "FIVE_MINUTE_DEMO_SCRIPT_CHECK: FAIL ($missing required item(s) missing or inconsistent)"; exit 1
