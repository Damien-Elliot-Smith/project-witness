#!/bin/sh
# Move 59/60 - release blocker repair check.
# POSIX sh, standard tools only.


ROOT=$(cd "$(dirname "$0")/.." && pwd)
missing=0
ok() { printf "  OK    %s\n" "$1"; }
bad() { printf "  FAIL  %s\n" "$1"; missing=$((missing + 1)); }
contains() { file="$1"; pattern="$2"; label="$3"; if grep -Fq "$pattern" "$file"; then ok "$label"; else bad "$label"; fi; }
forbid() { file="$1"; pattern="$2"; label="$3"; if grep -Fq "$pattern" "$file"; then bad "$label"; else ok "$label"; fi; }

current_marker="Roadmap complete through Move 60; Moves 61-70 remain future work"
current_zip="Project_Witness_WORKING_STACK_v11_MOVE_60.zip"

echo "Release blocker repair check"
echo "----------------------------"
for f in RELEASE_BLOCKER_REGISTER.md RELEASE_BLOCKER_REPAIR_LEDGER.md REVIEWER_FEEDBACK_LEDGER.md MOVE_INDEX.md STACK_STATUS.md; do [ -f "$ROOT/$f" ] && ok "$f" || bad "$f"; done
for f in tools/check_release_blockers.sh tools/check_local_v1_release.sh; do [ -f "$ROOT/$f" ] && ok "$f" || bad "$f"; done
for f in RELEASE_BLOCKER_REGISTER.md RELEASE_BLOCKER_REPAIR_LEDGER.md REVIEWER_FEEDBACK_LEDGER.md MOVE_INDEX.md STACK_STATUS.md; do path="$ROOT/$f"; [ -f "$path" ] || continue; contains "$path" "$current_marker" "$f has current marker"; done
contains "$ROOT/RELEASE_BLOCKER_REGISTER.md" "RB-59-001" "register includes RB-59-001"
contains "$ROOT/RELEASE_BLOCKER_REGISTER.md" "RB-59-006" "register includes RB-59-006"
contains "$ROOT/RELEASE_BLOCKER_REGISTER.md" "NO_EXTERNAL_FEEDBACK_RECORDED" "register preserves no-feedback state"
contains "$ROOT/RELEASE_BLOCKER_REPAIR_LEDGER.md" "No external reviewer blocker was repaired" "ledger prevents invented external blockers"
contains "$ROOT/REVIEWER_FEEDBACK_LEDGER.md" "NO_EXTERNAL_FEEDBACK_RECORDED" "feedback ledger still says zero feedback"
contains "$ROOT/MOVE_INDEX.md" "| 59 | Repair Release Blockers |" "MOVE_INDEX includes Move 59 row"
contains "$ROOT/MOVE_INDEX.md" "| 60 | Freeze Local v1 Release |" "MOVE_INDEX includes Move 60 row"
forbid "$ROOT/RELEASE_BLOCKER_REGISTER.md" "Step 60 = Freeze Local v1 Release, not started" "register no longer says Step 60 not started"
echo "----------------------------"
if [ "$missing" -eq 0 ]; then echo "RELEASE_BLOCKERS_CHECK: PASS"; exit 0; fi
echo "RELEASE_BLOCKERS_CHECK: FAIL ($missing required item(s) missing or inconsistent)"; exit 1
