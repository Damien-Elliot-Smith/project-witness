#!/bin/sh
# Move 60 - Local v1 Release check.
# POSIX sh, standard tools only. Fails closed on missing release files, stale
# status, or overclaims.


ROOT=$(cd "$(dirname "$0")/.." && pwd)
missing=0
ok() { printf "  OK    %s\n" "$1"; }
bad() { printf "  FAIL  %s\n" "$1"; missing=$((missing + 1)); }
contains() { file="$1"; pattern="$2"; label="$3"; if grep -Fq "$pattern" "$file"; then ok "$label"; else bad "$label"; fi; }
forbid() { file="$1"; pattern="$2"; label="$3"; if grep -Fq "$pattern" "$file"; then bad "$label"; else ok "$label"; fi; }

# Move 70.5: marker updated to the Roadmap One completion state.
# The authoritative current-state checker is tools/check_current_release_state.sh.
current_marker="Project Witness Roadmap One, Steps 1-70, is complete as a local review/demo stack."
current_zip="Project_Witness_WORKING_STACK_v20_MOVE_70.zip"

echo "Local v1 release check"
echo "----------------------"

echo "Release files:"
for f in LOCAL_V1_RELEASE.md CHANGELOG_MOVE_60.md README.md START_HERE.md REVIEWER_QUICKSTART.md STACK_STATUS.md MOVE_INDEX.md HANDOFF_NOTES.md REPOSITORY_STRUCTURE.md RELEASE_BLOCKER_REGISTER.md RELEASE_BLOCKER_REPAIR_LEDGER.md REVIEWER_FEEDBACK_LEDGER.md; do
  [ -f "$ROOT/$f" ] && ok "$f" || bad "$f"
done

echo "Release freeze record:"
for f in freeze_record/local_v1_release_v01/LOCAL_V1_RELEASE_FREEZE_RECORD.md freeze_record/local_v1_release_v01/LOCAL_V1_RELEASE_MANIFEST.md freeze_record/local_v1_release_v01/LOCAL_V1_RELEASE_LIMITS.md freeze_record/local_v1_release_v01/RELEASE_VALIDATION_COMMANDS.md freeze_record/local_v1_release_v01/TREE_HASHES.sha256; do
  [ -f "$ROOT/$f" ] && ok "$f" || bad "$f"
done

echo "Required directories:"
for d in src verify freeze_record tools; do
  [ -d "$ROOT/$d" ] && ok "$d/" || bad "$d/"
done

echo "Status consistency:"
contains "$ROOT/LOCAL_V1_RELEASE.md" "HISTORICAL DOCUMENT" "LOCAL_V1_RELEASE.md is marked historical"
for f in README.md START_HERE.md REVIEWER_QUICKSTART.md STACK_STATUS.md MOVE_INDEX.md HANDOFF_NOTES.md REPOSITORY_STRUCTURE.md PRIVATE_REVIEWER_PACKAGE.md PUBLIC_EXPLANATION.md FIVE_MINUTE_DEMO_SCRIPT.md REVIEWER_FEEDBACK_ROUND.md REVIEWER_FEEDBACK_LEDGER.md REVIEWER_FEEDBACK_TRIAGE.md RELEASE_BLOCKER_REGISTER.md RELEASE_BLOCKER_REPAIR_LEDGER.md; do
  path="$ROOT/$f"
  [ -f "$path" ] || { bad "status doc missing: $f"; continue; }
  contains "$path" "$current_marker" "$f has current marker"
  forbid "$path" "Moves 60-70 remain future work" "$f has no old Move 60 future marker"
  forbid "$path" "Roadmap complete through Move 59" "$f has no old Move 59 marker"
done

echo "Release honesty boundary:"
for f in LOCAL_V1_RELEASE.md freeze_record/local_v1_release_v01/LOCAL_V1_RELEASE_LIMITS.md HANDOFF_NOTES.md PUBLIC_EXPLANATION.md; do
  path="$ROOT/$f"
  [ -f "$path" ] || continue
  contains "$path" "does not prove external truth" "$f says no external truth"
  contains "$path" "not production-ready" "$f says not production-ready"
  contains "$path" "NO_EXTERNAL_FEEDBACK_RECORDED" "$f preserves no-feedback boundary"
done

echo "Move index:"
contains "$ROOT/MOVE_INDEX.md" "| 60 | Freeze Local v1 Release |" "MOVE_INDEX includes Move 60 row"
contains "$ROOT/MOVE_INDEX.md" "$current_marker" "MOVE_INDEX has current exact marker"

echo "Current package references:"
for f in REVIEWER_QUICKSTART.md PRIVATE_REVIEWER_PACKAGE.md FIVE_MINUTE_DEMO_SCRIPT.md REVIEWER_FEEDBACK_ROUND.md REVIEWER_FEEDBACK_LEDGER.md; do
  path="$ROOT/$f"
  [ -f "$path" ] || continue
  contains "$path" "$current_zip" "$f references current package zip"
done

echo "Previous checkers present:"
for f in tools/check_release_blockers.sh tools/check_reviewer_feedback_round.sh tools/check_five_minute_demo_script.sh tools/check_public_explanation.sh tools/check_private_reviewer_package.sh tools/check_repository_structure.sh tools/check_linux_desktop_instructions.sh tools/check_windows_notes.sh tools/validate_handoff.sh; do
  [ -f "$ROOT/$f" ] && ok "$f" || bad "$f"
done

echo "----------------------"
if [ "$missing" -eq 0 ]; then
  echo "LOCAL_V1_RELEASE_CHECK: PASS"
  exit 0
fi
echo "LOCAL_V1_RELEASE_CHECK: FAIL ($missing required item(s) missing or inconsistent)"
exit 1
