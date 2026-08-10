#!/bin/sh
# Move 58/60 - reviewer feedback round check.

ROOT=$(cd "$(dirname "$0")/.." && pwd)
missing=0
ok() { printf "  OK    %s\n" "$1"; }
bad() { printf "  FAIL  %s\n" "$1"; missing=$((missing + 1)); }
contains() { file="$1"; pattern="$2"; label="$3"; if grep -Fq "$pattern" "$file"; then ok "$label"; else bad "$label"; fi; }
forbid() { file="$1"; pattern="$2"; label="$3"; if grep -Fq "$pattern" "$file"; then bad "$label"; else ok "$label"; fi; }

# Move 70.5: marker updated to the Roadmap One completion state.
# The authoritative current-state checker is tools/check_current_release_state.sh.
current_marker="Project Witness Roadmap One, Steps 1-70, is complete as a local review/demo stack."
echo "Reviewer feedback round check"
echo "-----------------------------"
for f in REVIEWER_FEEDBACK_ROUND.md REVIEWER_FEEDBACK_LEDGER.md REVIEWER_FEEDBACK_TRIAGE.md; do [ -f "$ROOT/$f" ] && ok "$f" || bad "$f"; done
for f in REVIEWER_FEEDBACK_ROUND.md REVIEWER_FEEDBACK_LEDGER.md REVIEWER_FEEDBACK_TRIAGE.md; do path="$ROOT/$f"; [ -f "$path" ] || continue; contains "$path" "$current_marker" "$f has current marker"; contains "$path" "NO_EXTERNAL_FEEDBACK_RECORDED" "$f preserves no-feedback state"; done
contains "$ROOT/REVIEWER_FEEDBACK_ROUND.md" "Project_Witness_WORKING_STACK_v20_MOVE_70.zip" "round references current package zip"
contains "$ROOT/REVIEWER_FEEDBACK_ROUND.md" "sh tools/check_local_v1_release.sh" "round includes release check"
contains "$ROOT/REVIEWER_FEEDBACK_TRIAGE.md" "Do not claim Move 59 or Move 60 repaired invented external blockers" "prevents invented external blockers"
echo "-----------------------------"
if [ "$missing" -eq 0 ]; then echo "REVIEWER_FEEDBACK_ROUND_CHECK: PASS"; exit 0; fi
echo "REVIEWER_FEEDBACK_ROUND_CHECK: FAIL ($missing required item(s) missing or inconsistent)"; exit 1
