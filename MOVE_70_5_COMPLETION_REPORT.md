# Move 70.5 Completion Report - Release State Cleanup and Documentation Truth Pass

Date: 2026-07-03
Scope: documentation, release markers, status files, and checker scripts only.
No component behaviour, schema, or architecture changed. No Move 71 work. No Rust work.

Status: Roadmap One (Steps 1-70) complete as a local review/demo stack. Not production-ready. Part Two has not started.

Status exact marker: Project Witness Roadmap One, Steps 1-70, is complete as a local review/demo stack. Post-completion repairs Move 70.6 and RT-004 are adopted. The Move 71 Python behaviour freeze is adopted. Rust Moves 72-78 are adopted, including ZipGuard archive safety. Part Two has started. Move 79 (verification-only Python/Rust agreement harness) is the current candidate; no full bundle verification capability exists or is claimed.

## Contradictions found

1. **Primary contradiction.** `README.md`, `STACK_STATUS.md`, and
   `ROADMAP_ONE_COMPLETE.md` stated Roadmap One Steps 1-70 complete, while 15
   other top-level docs still stated the current status as
   "Local v1 Release. Roadmap complete through Move 60; Moves 61-70 remain
   future work. The 70-step roadmap is not complete."
   Affected as current-status claims: START_HERE.md, REPOSITORY_STRUCTURE.md,
   REVIEWER_QUICKSTART.md, HANDOFF_NOTES.md, PUBLIC_EXPLANATION.md,
   PRIVATE_REVIEWER_PACKAGE.md, FIVE_MINUTE_DEMO_SCRIPT.md,
   REVIEWER_FEEDBACK_ROUND.md, REVIEWER_FEEDBACK_LEDGER.md,
   REVIEWER_FEEDBACK_TRIAGE.md, RELEASE_BLOCKER_REGISTER.md,
   RELEASE_BLOCKER_REPAIR_LEDGER.md, LICENSE_DECISION_NEEDED.md,
   LINUX_DESKTOP_RUN_INSTRUCTIONS.md, WINDOWS_NOTES.md, LOCAL_V1_RELEASE.md.
2. **Three competing "exact marker" phrasings** existed simultaneously: the
   Move 60 marker, MOVE_INDEX.md's own Roadmap One marker, and the README/
   STACK_STATUS sentence. There was no single canonical marker.
3. **Stale checker expectations.** Seven `tools/check_*.sh` scripts hard-coded
   the Move 60 marker as `current_marker`, so they actively enforced the stale
   wording. Three of them (check_local_v1_release.sh, check_release_blockers.sh,
   check_repository_structure.sh) were already FAILING at baseline because
   README/STACK_STATUS/MOVE_INDEX had moved to the new wording.
4. **Stale package references.** Six docs and five checkers still pointed at
   `Project_Witness_WORKING_STACK_v11_MOVE_60.zip` (which does not exist in the
   repo) instead of the final
   `Project_Witness_WORKING_STACK_v20_MOVE_70.zip` (which does, with matching
   SHA-256 `1248bc46...81aba`).
5. **Internal contradiction in WINDOWS_NOTES.md**: one block claimed "Local v1
   Candidate ... complete through Move 58; Moves 57-70 remain future work"
   (itself inconsistent) while the marker line below said Move 60.
6. **LOCAL_V1_RELEASE.md** presented the Move 60 milestone as current, including
   an active instruction "Do not describe the 70-step roadmap as complete."
7. **No single authoritative current-state document or checker existed.**
   Note: KNOWN_LIMITS.md, HOW_TO_RUN.md, HOW_TO_VERIFY.md, and
   REVIEWER_GUIDE.md do not exist in this repository; their roles are covered
   by README.md ("What it is not"), START_HERE.md, REVIEWER_QUICKSTART.md, and
   now CURRENT_RELEASE_STATE.md.

## Contradictions fixed

- One canonical current status adopted everywhere:
  "Project Witness Roadmap One, Steps 1-70, is complete as a local review/demo
  stack." plus "Part Two has not started." All current-status docs updated.
- MOVE_INDEX.md marker unified to the canonical marker.
- LOCAL_V1_RELEASE.md banner-marked as a HISTORICAL DOCUMENT (Move 60
  milestone); its historical marker relabelled "Historical status marker
  (superseded)"; its "Future work boundary" section relabelled historical with
  a pointer to the current state.
- WINDOWS_NOTES.md Move 58-era block corrected and noted as historical wording.
- HANDOFF_NOTES.md and REVIEWER_QUICKSTART.md reworded so "Local v1 Release" is
  described as an earlier milestone, not the current package identity.
- All `v11_MOVE_60.zip` references in current docs updated to
  `Project_Witness_WORKING_STACK_v20_MOVE_70.zip`.
- Seven checker scripts updated to the canonical marker and current zip, each
  with a header note that `tools/check_current_release_state.sh` is
  authoritative. check_local_v1_release.sh and check_repository_structure.sh
  now require LOCAL_V1_RELEASE.md's historical banner instead of a current
  marker in it.
- New authoritative checker created: `tools/check_current_release_state.sh`.
- New authoritative current-state document created: `CURRENT_RELEASE_STATE.md`.
- Historical files deliberately NOT rewritten: `CHANGELOG_MOVE_52..60.md`,
  `CHANGELOG_REPAIR_v02.md`, everything under `freeze_record/`, `src/*/_frozen/`,
  `releases/`, and the labelled historical notes inside STACK_STATUS.md. These
  are historical records and are identified as such in CURRENT_RELEASE_STATE.md.

## Contradictions left

- None known in current-status documentation. The only remaining occurrence of
  the old Move 60 marker outside changelogs/freeze records is inside
  LOCAL_V1_RELEASE.md, explicitly labelled "Historical status marker
  (superseded)" beneath a HISTORICAL DOCUMENT banner.

## Files changed

Documentation (19): README.md, START_HERE.md, STACK_STATUS.md, MOVE_INDEX.md,
REPOSITORY_STRUCTURE.md, HANDOFF_NOTES.md, REVIEWER_QUICKSTART.md,
PUBLIC_EXPLANATION.md, PRIVATE_REVIEWER_PACKAGE.md, FIVE_MINUTE_DEMO_SCRIPT.md,
REVIEWER_FEEDBACK_ROUND.md, REVIEWER_FEEDBACK_LEDGER.md,
REVIEWER_FEEDBACK_TRIAGE.md, RELEASE_BLOCKER_REGISTER.md,
RELEASE_BLOCKER_REPAIR_LEDGER.md, LICENSE_DECISION_NEEDED.md,
LINUX_DESKTOP_RUN_INSTRUCTIONS.md, WINDOWS_NOTES.md, LOCAL_V1_RELEASE.md.

Checkers updated (7): tools/check_repository_structure.sh,
tools/check_local_v1_release.sh, tools/check_release_blockers.sh,
tools/check_reviewer_feedback_round.sh, tools/check_five_minute_demo_script.sh,
tools/check_public_explanation.sh, tools/check_private_reviewer_package.sh.

New files (3): CURRENT_RELEASE_STATE.md, tools/check_current_release_state.sh,
MOVE_70_5_COMPLETION_REPORT.md (this file).

Unchanged (verified by recursive diff against the pre-70.5 tree):
src/, verify/, freeze_record/, releases/. No PACKAGE_VERSION bumped.

## Commands run and exact results

Baseline (before edits):
- tools/check_local_v1_release.sh — `LOCAL_V1_RELEASE_CHECK: FAIL (4 required item(s) missing or inconsistent)`
- tools/check_release_blockers.sh — `RELEASE_BLOCKERS_CHECK: FAIL (2 required item(s) missing or inconsistent)`
- tools/check_repository_structure.sh — `REPOSITORY_STRUCTURE_CHECK: FAIL (3 required item(s) missing or inconsistent)`
- all other checkers — PASS (by enforcing the stale marker)

After cleanup:
- sh tools/check_current_release_state.sh — `CURRENT_RELEASE_STATE_CHECK: PASS`
- sh tools/check_local_v1_release.sh — `LOCAL_V1_RELEASE_CHECK: PASS`
- sh tools/check_release_blockers.sh — `RELEASE_BLOCKERS_CHECK: PASS`
- sh tools/check_repository_structure.sh — `REPOSITORY_STRUCTURE_CHECK: PASS`
- sh tools/check_reviewer_feedback_round.sh — `REVIEWER_FEEDBACK_ROUND_CHECK: PASS`
- sh tools/check_five_minute_demo_script.sh — `FIVE_MINUTE_DEMO_SCRIPT_CHECK: PASS`
- sh tools/check_public_explanation.sh — `PUBLIC_EXPLANATION_CHECK: PASS`
- sh tools/check_private_reviewer_package.sh — `PRIVATE_REVIEWER_PACKAGE_CHECK: PASS`
- sh tools/check_linux_desktop_instructions.sh — PASS
- sh tools/check_windows_notes.sh — PASS
- sh tools/validate_handoff.sh — `HANDOFF_VALIDATION: PASS`
- sh tools/run_all_tests.sh — `RESULT: PASS — ALL_COMPONENT_TESTS_PASSED`
  (Components checked: 18, passed: 18, failed: 0, total tests detected: 1234)
- sh tools/run_demo.sh — `COMPANION_COMPLETED`, `verify_ok: true`
- sh tools/run_live_e2e_demo.sh — `COMPANION_COMPLETED`, `verify_ok: true`
- sh tools/run_independent_verify.sh — `PROJECT_WITNESS_INDEPENDENT_VERIFICATION_PASSED`, `verify_ok = true`
- sh tools/run_local_v1_verify.sh — `LOCAL_V1_CANDIDATE_VERIFIED`, `verify_ok = true`
- python3 -m compileall src tools verify — PASS (no compile errors)
- sha256sum of releases/roadmap_one_complete/move_70_final/Project_Witness_WORKING_STACK_v20_MOVE_70.zip —
  matches recorded `1248bc46fa555cc50ed7b63c9284baffd1e95a6972cdfbc4a40a0201fea81aba`

Not run: tools/run_termux_verify.sh (Termux-specific environment not available
here; no claim made about it).

## Completion criteria check

- Current docs do not contradict each other — met (enforced by new checker).
- Old Move 60 wording removed from current-status docs or clearly marked historical — met.
- One current release state documented — met (CURRENT_RELEASE_STATE.md).
- One authoritative current-state checker exists — met (tools/check_current_release_state.sh, PASS).
- Tests/verifiers pass — met (18/18 components, 1234 tests, all verifiers PASS).
- Move 71 not claimed complete — met (explicitly stated not started; checker forbids the claim).
- No Rust work started — met (checker verifies no .rs/Cargo.toml and forbids the claim).
- No new product behaviour added — met (src/, verify/, freeze_record/, releases/ byte-identical to pre-70.5).

## Remaining blockers

None for Move 70.5. Carried forward, unchanged and out of scope here:
- No external human reviewer has yet reviewed the stack
  (`NO_EXTERNAL_FEEDBACK_RECORDED`).
- The `companion verify` nested-bundle verification-depth gap remains a
  blocker-register concern for future work; no behaviour change was permitted
  in this move.

## Final status

MOVE 70.5: COMPLETE
