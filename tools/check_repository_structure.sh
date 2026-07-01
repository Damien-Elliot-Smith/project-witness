#!/bin/sh
# Move 54/60 - repository structure check.

ROOT=$(cd "$(dirname "$0")/.." && pwd)
missing=0
ok() { printf "  OK    %s\n" "$1"; }
bad() { printf "  FAIL  %s\n" "$1"; missing=$((missing + 1)); }
contains() { file="$1"; pattern="$2"; label="$3"; if grep -Fq "$pattern" "$file"; then ok "$label"; else bad "$label"; fi; }
forbid() { file="$1"; pattern="$2"; label="$3"; if grep -Fq "$pattern" "$file"; then bad "$label"; else ok "$label"; fi; }

current_marker="Roadmap complete through Move 60; Moves 61-70 remain future work"
echo "Repository structure check"
echo "--------------------------"
echo "Files:"
for f in README.md START_HERE.md REVIEWER_QUICKSTART.md STACK_STATUS.md MOVE_INDEX.md HANDOFF_NOTES.md REPOSITORY_STRUCTURE.md LOCAL_V1_RELEASE.md LICENSE LINUX_DESKTOP_RUN_INSTRUCTIONS.md WINDOWS_NOTES.md; do [ -f "$ROOT/$f" ] && ok "$f" || bad "$f"; done
echo "Directories:"
for d in src verify freeze_record tools freeze_record/local_v1_release_v01; do [ -d "$ROOT/$d" ] && ok "$d/" || bad "$d/"; done
echo "Status consistency:"
for f in README.md START_HERE.md STACK_STATUS.md MOVE_INDEX.md REPOSITORY_STRUCTURE.md HANDOFF_NOTES.md LOCAL_V1_RELEASE.md; do path="$ROOT/$f"; [ -f "$path" ] || continue; contains "$path" "$current_marker" "$f has current marker"; done
echo "--------------------------"
if [ "$missing" -eq 0 ]; then echo "REPOSITORY_STRUCTURE_CHECK: PASS"; exit 0; fi
echo "REPOSITORY_STRUCTURE_CHECK: FAIL ($missing required item(s) missing or inconsistent)"; exit 1
