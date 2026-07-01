# Changelog - Move 59 (Repair Release Blockers)

Date: 2026-06-30
Roadmap: Step 59 = Repair Release Blockers (Step 58 = Reviewer Feedback Round, Step 60 = Freeze Local v1 Release - not started).
Scope: release-readiness repair of documented blockers only.

## Files added

- `RELEASE_BLOCKER_REGISTER.md` - current release-blocker register for Move 59.
- `RELEASE_BLOCKER_REPAIR_LEDGER.md` - repair ledger mapping each accepted blocker to the files repaired and verification used.
- `tools/check_release_blockers.sh` - POSIX-sh checker that fails closed unless blocker documents, current status markers, current package references, and no-stale-status conditions pass.
- `CHANGELOG_MOVE_59.md` - this file.

## Release blockers repaired

- `RB-59-001` - current top-level docs had stale roadmap status ranges.
- `RB-59-002` - some current docs mislabelled Move 58 as the Five-Minute Demo Script.
- `RB-59-003` - active reviewer/demo docs still used stale package zip names.
- `RB-59-004` - `STACK_STATUS.md` current bottom line still mentioned an earlier move range.
- `RB-59-005` - `MOVE_INDEX.md` needed the Move 59 row and clean status section.
- `RB-59-006` - no explicit release-blocker checker existed before Step 60.

## Files updated - documentation/checker consistency only

- `README.md`, `START_HERE.md`, `REVIEWER_QUICKSTART.md`, `STACK_STATUS.md`, `MOVE_INDEX.md`, `HANDOFF_NOTES.md`, `REPOSITORY_STRUCTURE.md`.
- `PRIVATE_REVIEWER_PACKAGE.md`, `PUBLIC_EXPLANATION.md`, `FIVE_MINUTE_DEMO_SCRIPT.md`, `REVIEWER_FEEDBACK_ROUND.md`, `REVIEWER_FEEDBACK_LEDGER.md`, `REVIEWER_FEEDBACK_TRIAGE.md`.
- Existing checker scripts were updated to the current marker: `Roadmap complete through Move 59; Moves 60-70 remain future work`.

## External reviewer honesty boundary

No external reviewer feedback is recorded in this package. `REVIEWER_FEEDBACK_LEDGER.md` still records `NO_EXTERNAL_FEEDBACK_RECORDED`. Move 59 does not claim reviewer approval, reviewer acceptance, or repair of external reviewer blockers.

## Not changed

- No component code behaviour changed.
- No schemas changed.
- No architecture changed.
- No features added.
- No GUI, app, networking, cloud, signing, anchoring, LLM integration, autonomy, new Sentinel actions, Rust, or production claims were added.
- `src/`, `verify/`, and `freeze_record/` are byte-identical to Move 58.
- Step 60 was not started.

## Validation

Fresh extraction of `Project_Witness_WORKING_STACK_v10_MOVE_59.zip`:

- `sha256sum -c Project_Witness_WORKING_STACK_v10_MOVE_59.zip.sha256` -> OK.
- `sh tools/check_release_blockers.sh` -> `RELEASE_BLOCKERS_CHECK: PASS`.
- `sh tools/check_reviewer_feedback_round.sh` -> `REVIEWER_FEEDBACK_ROUND_CHECK: PASS`.
- `sh tools/check_five_minute_demo_script.sh` -> `FIVE_MINUTE_DEMO_SCRIPT_CHECK: PASS`.
- `sh tools/check_public_explanation.sh` -> `PUBLIC_EXPLANATION_CHECK: PASS`.
- `sh tools/check_private_reviewer_package.sh` -> `PRIVATE_REVIEWER_PACKAGE_CHECK: PASS`.
- `sh tools/check_repository_structure.sh` -> `REPOSITORY_STRUCTURE_CHECK: PASS`.
- `sh tools/check_linux_desktop_instructions.sh` -> `LINUX_DESKTOP_INSTRUCTIONS_CHECK: PASS`.
- `sh tools/check_windows_notes.sh` -> `WINDOWS_NOTES_CHECK: PASS`.
- `sh tools/validate_handoff.sh` -> `HANDOFF_VALIDATION: PASS`.

## Status

Move 59 is complete only if the checks above pass. Roadmap complete through Move 59; Moves 60-70 remain future work. This is a Local v1 Candidate, not a final Local v1 Release. The 70-step roadmap is not complete.
