#!/bin/sh
# Move 70.5 - AUTHORITATIVE current release state checker.
# POSIX sh, standard tools only. Fails closed.
#
# This is the single authoritative checker for current status. Older
# tools/check_*.sh scripts were updated in Move 70.5 but are not authoritative.
# The single authoritative current-state document is CURRENT_RELEASE_STATE.md.

ROOT=$(cd "$(dirname "$0")/.." && pwd)
missing=0
ok() { printf "  OK    %s\n" "$1"; }
bad() { printf "  FAIL  %s\n" "$1"; missing=$((missing + 1)); }
contains() { file="$1"; pattern="$2"; label="$3"; if grep -Fq "$pattern" "$file"; then ok "$label"; else bad "$label"; fi; }
forbid() { file="$1"; pattern="$2"; label="$3"; if grep -Fq "$pattern" "$file"; then bad "$label"; else ok "$label"; fi; }

current_marker="Project Witness Roadmap One, Steps 1-70, is complete as a local review/demo stack."
part_two_marker="Part Two has started."
stale_part_two="Part Two has not started."
stale_m71="Move 71 (Python behaviour freeze) has not started"
stale_rust="No Rust work exists"
stale_a="Roadmap complete through Move 60; Moves 61-70 remain future work"
stale_b="Moves 61-70 remain future work"
stale_c="The 70-step roadmap is not complete"

# Current-status docs: must agree on current status and carry no stale wording.
CURRENT_DOCS="README.md START_HERE.md STACK_STATUS.md MOVE_INDEX.md REPOSITORY_STRUCTURE.md HANDOFF_NOTES.md REVIEWER_QUICKSTART.md PUBLIC_EXPLANATION.md PRIVATE_REVIEWER_PACKAGE.md FIVE_MINUTE_DEMO_SCRIPT.md REVIEWER_FEEDBACK_ROUND.md REVIEWER_FEEDBACK_LEDGER.md REVIEWER_FEEDBACK_TRIAGE.md RELEASE_BLOCKER_REGISTER.md RELEASE_BLOCKER_REPAIR_LEDGER.md LICENSE_DECISION_NEEDED.md LINUX_DESKTOP_RUN_INSTRUCTIONS.md WINDOWS_NOTES.md CURRENT_RELEASE_STATE.md"

echo "Current release state check (authoritative)"
echo "--------------------------------------------"

echo "Authoritative current-state document:"
[ -f "$ROOT/CURRENT_RELEASE_STATE.md" ] && ok "CURRENT_RELEASE_STATE.md exists" || bad "CURRENT_RELEASE_STATE.md exists"

echo "Current-status docs agree on current status:"
for f in $CURRENT_DOCS; do
  path="$ROOT/$f"
  [ -f "$path" ] || { bad "missing: $f"; continue; }
  contains "$path" "$current_marker" "$f carries current marker"
done


# B6: no current-state line may contain BOTH "Move 78" and "candidate",
# regardless of parentheses or intervening wording. Move 78 is ADOPTED.
for f in "$ROOT/CURRENT_RELEASE_STATE.md" "$ROOT/rust/README.md"; do
  if grep -n "Move 78" "$f" | grep -qi "candidate"; then
    bad "$(basename "$f"): a line names Move 78 as a candidate (it is ADOPTED)"
    grep -n "Move 78" "$f" | grep -i "candidate" | head -2 | sed 's/^/        /'
  else
    ok "$(basename "$f"): no Move-78-candidate wording"
  fi
done

echo "Part Two clearly marked as started (Move 72 rule):"
for f in README.md STACK_STATUS.md START_HERE.md MOVE_INDEX.md CURRENT_RELEASE_STATE.md; do
  contains "$ROOT/$f" "$part_two_marker" "$f says Part Two has started"
done
for f in $CURRENT_DOCS; do
  path="$ROOT/$f"
  [ -f "$path" ] || continue
  forbid "$path" "$stale_part_two" "$f free of stale Part-Two-not-started claim"
done

echo "No stale Move 60-era wording in current-status docs:"
for f in $CURRENT_DOCS; do
  path="$ROOT/$f"
  [ -f "$path" ] || continue
  forbid "$path" "$stale_a" "$f free of stale Move 60 status marker"
  forbid "$path" "$stale_b" "$f free of 'Moves 61-70 remain future work'"
  forbid "$path" "$stale_c" "$f free of '70-step roadmap is not complete'"
done

echo "Historical documents are marked historical:"
contains "$ROOT/LOCAL_V1_RELEASE.md" "HISTORICAL DOCUMENT" "LOCAL_V1_RELEASE.md banner-marked historical"
contains "$ROOT/CURRENT_RELEASE_STATE.md" "Which docs are historical" "CURRENT_RELEASE_STATE.md lists historical docs"

echo "Known limits are present:"
contains "$ROOT/CURRENT_RELEASE_STATE.md" "What it does not prove" "limits section present"
contains "$ROOT/CURRENT_RELEASE_STATE.md" "does not prove real-world truth" "no real-world truth claim"
contains "$ROOT/CURRENT_RELEASE_STATE.md" "does not prove legal validity" "no legal validity claim"
contains "$ROOT/CURRENT_RELEASE_STATE.md" "does not prove external identity" "no external identity claim"
contains "$ROOT/CURRENT_RELEASE_STATE.md" "does not prove trusted timestamping" "no trusted timestamping claim"
contains "$ROOT/CURRENT_RELEASE_STATE.md" "not real external anchoring" "no real external anchoring claim"
contains "$ROOT/CURRENT_RELEASE_STATE.md" "not production-ready" "not production-ready stated"
contains "$ROOT/README.md" "not production-ready" "README states not production-ready"

echo "Adopted line recorded, stale not-started claims forbidden:"
contains "$ROOT/CURRENT_RELEASE_STATE.md" "Move 70.6 reconciliation adopted" "Move 70.6 adoption recorded"
contains "$ROOT/CURRENT_RELEASE_STATE.md" "RT-004 repair adopted" "RT-004 adoption recorded"
contains "$ROOT/CURRENT_RELEASE_STATE.md" "Move 71 Python behaviour freeze adopted" "Move 71 adoption recorded"
for f in $CURRENT_DOCS; do
  path="$ROOT/$f"
  [ -f "$path" ] || continue
  forbid "$path" "$stale_m71" "$f free of stale Move-71-not-started claim"
done

echo "Rust status honest (Move 72 rules):"
if find "$ROOT/src" "$ROOT/verify" -name "*.rs" -o -name "Cargo.toml" 2>/dev/null | grep -q .; then
  bad "Rust stays outside src/ and verify/"
else
  ok "Rust stays outside src/ and verify/"
fi
if [ -d "$ROOT/rust" ]; then
  contains "$ROOT/CURRENT_RELEASE_STATE.md" "Rust verification capability currently covers manifest structure," "state doc: precise current Rust capability stated"
  contains "$ROOT/CURRENT_RELEASE_STATE.md" "receipt canonical-hash recomputation, and adopted ZIP archive" "state doc: capability includes ADOPTED archive safety"
  contains "$ROOT/CURRENT_RELEASE_STATE.md" "No full or production Rust bundle verifier exists or is" "state doc: no full/production verifier claimed"
  forbid "$ROOT/CURRENT_RELEASE_STATE.md" "Rust workspace exists, but no Rust verification capability exists yet" "state doc free of stale no-capability claim"
  forbid "$ROOT/CURRENT_RELEASE_STATE.md" "Move 74 is a Rust case manifest validator candidate" "state doc free of stale Move-74-candidate claim"
  contains "$ROOT/CURRENT_RELEASE_STATE.md" "Rust Moves 72-78 are adopted" "state doc: Moves 72-78 adopted"
  forbid "$ROOT/CURRENT_RELEASE_STATE.md" "full Rust bundle verifier is complete" "state doc forbids full-verifier-complete claim"
  forbid "$ROOT/CURRENT_RELEASE_STATE.md" "production Rust verifier is complete" "state doc forbids production-verifier-complete claim"
  forbid "$ROOT/CURRENT_RELEASE_STATE.md" "a full Rust verifier exists" "state doc forbids full-verifier-exists claim"
  contains "$ROOT/CURRENT_RELEASE_STATE.md" "Move 72 Rust workspace skeleton adopted" "state doc: Move 72 adoption recorded"
  contains "$ROOT/CURRENT_RELEASE_STATE.md" "Move 73 witness-verify CLI skeleton adopted" "state doc: Move 73 adoption recorded"
  contains "$ROOT/CURRENT_RELEASE_STATE.md" "Move 74 Rust case manifest validator adopted" "state doc: Move 74 adoption recorded"
  contains "$ROOT/CURRENT_RELEASE_STATE.md" "Move 75 Rust top-level file hash verification adopted" "state doc: Move 75 adoption recorded"
  contains "$ROOT/CURRENT_RELEASE_STATE.md" "Move 76 Rust declared receipt-chain linkage adopted" "state doc: Move 76 adoption recorded"
  contains "$ROOT/CURRENT_RELEASE_STATE.md" "Move 77 Rust canonical JSON + receipt hash recomputation adopted" "state doc: Move 77 adoption recorded"
  contains "$ROOT/CURRENT_RELEASE_STATE.md" "Move 79 is a verification-only Python/Rust agreement harness" "state doc: Move 79 harness-candidate"
  contains "$ROOT/CURRENT_RELEASE_STATE.md" "Move 78 Rust ZipGuard archive-safety adopted" "state doc: Move 78 adoption recorded"
  forbid "$ROOT/rust/README.md" "Move 78 candidate" "rust README free of Move-78-candidate wording"
  forbid "$ROOT/CURRENT_RELEASE_STATE.md" "candidate ZIP archive" "state doc: ZIP archive safety is ADOPTED not candidate"
  forbid "$ROOT/CURRENT_RELEASE_STATE.md" "Move 78 is a Rust ZipGuard archive-safety candidate" "state doc free of Move-78-candidate wording"
  forbid "$ROOT/CURRENT_RELEASE_STATE.md" "archive safety proves" "state doc forbids archive-proves-validity claim"
  forbid "$ROOT/CURRENT_RELEASE_STATE.md" "Move 77 is a Rust canonical JSON tool candidate" "state doc free of stale Move-77-candidate claim"
  grep -q "ARCHIVE_SAFETY_OK" "$ROOT/rust/witness-verify/src/main.rs" && ok "archive-safe path stays INCONCLUSIVE" || bad "archive-safe path stays INCONCLUSIVE"
  grep -q "no_reachable_path_emits_pass" "$ROOT/rust/witness-verify/src/main.rs" && ok "PASS-unreachable property tested" || bad "PASS-unreachable property tested"
  forbid "$ROOT/CURRENT_RELEASE_STATE.md" "$stale_rust" "state doc free of no-Rust-work claim while rust/ exists"
  [ -f "$ROOT/tools/check_rust_workspace.sh" ] && ok "tools/check_rust_workspace.sh exists" || bad "tools/check_rust_workspace.sh exists"
else
  contains "$ROOT/CURRENT_RELEASE_STATE.md" "No Rust work exists" "Rust explicitly not started"
fi
for f in $CURRENT_DOCS; do
  path="$ROOT/$f"
  [ -f "$path" ] || continue
  forbid "$path" "Rust implementation is complete" "$f does not claim Rust implemented"
  forbid "$path" "Rust verifier is complete" "$f does not claim a working Rust verifier"
done

echo "One clear command path for verification:"
contains "$ROOT/CURRENT_RELEASE_STATE.md" "Which commands verify it" "verification commands section present"
contains "$ROOT/CURRENT_RELEASE_STATE.md" "sh tools/check_current_release_state.sh" "authoritative checker command listed"
contains "$ROOT/CURRENT_RELEASE_STATE.md" "sh tools/run_all_tests.sh" "test command listed"
for f in tools/check_current_release_state.sh tools/run_all_tests.sh tools/validate_handoff.sh tools/run_demo.sh tools/check_local_v1_release.sh; do
  [ -f "$ROOT/$f" ] && ok "$f exists" || bad "$f exists"
done

echo "Final package integrity reference:"
contains "$ROOT/CURRENT_RELEASE_STATE.md" "1248bc46fa555cc50ed7b63c9284baffd1e95a6972cdfbc4a40a0201fea81aba" "SHA-256 recorded"
[ -f "$ROOT/releases/roadmap_one_complete/move_70_final/Project_Witness_WORKING_STACK_v20_MOVE_70.zip" ] \
  && ok "final Move 70 zip present" || bad "final Move 70 zip present"

echo "--------------------------------------------"
if [ "$missing" -eq 0 ]; then
  echo "CURRENT_RELEASE_STATE_CHECK: PASS"
  exit 0
fi
echo "CURRENT_RELEASE_STATE_CHECK: FAIL ($missing required item(s) missing or inconsistent)"
exit 1
