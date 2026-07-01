# Local v1 Release Manifest

Date: 2026-07-01
Roadmap: Move 60 - Freeze Local v1 Release.
Status exact marker: Roadmap complete through Move 60; Moves 61-70 remain future work.

## Top-level release files

- `LOCAL_V1_RELEASE.md`
- `CHANGELOG_MOVE_60.md`
- `README.md`
- `START_HERE.md`
- `REVIEWER_QUICKSTART.md`
- `STACK_STATUS.md`
- `MOVE_INDEX.md`
- `HANDOFF_NOTES.md`
- `REPOSITORY_STRUCTURE.md`
- `PRIVATE_REVIEWER_PACKAGE.md`
- `PUBLIC_EXPLANATION.md`
- `FIVE_MINUTE_DEMO_SCRIPT.md`
- `REVIEWER_FEEDBACK_ROUND.md`
- `REVIEWER_FEEDBACK_LEDGER.md`
- `REVIEWER_FEEDBACK_TRIAGE.md`
- `RELEASE_BLOCKER_REGISTER.md`
- `RELEASE_BLOCKER_REPAIR_LEDGER.md`
- `LINUX_DESKTOP_RUN_INSTRUCTIONS.md`
- `WINDOWS_NOTES.md`
- `LICENSE`

## Release freeze record files

- `freeze_record/local_v1_release_v01/LOCAL_V1_RELEASE_FREEZE_RECORD.md`
- `freeze_record/local_v1_release_v01/LOCAL_V1_RELEASE_MANIFEST.md`
- `freeze_record/local_v1_release_v01/LOCAL_V1_RELEASE_LIMITS.md`
- `freeze_record/local_v1_release_v01/RELEASE_VALIDATION_COMMANDS.md`
- `freeze_record/local_v1_release_v01/TREE_HASHES.sha256`

## Release checker

- `tools/check_local_v1_release.sh`

## Existing code and verifier trees

- `src/` remains the runtime component tree.
- `verify/` remains the independent verification tree.
- `freeze_record/local_v1_candidate_v01/` remains the Move 50 candidate record.
- `freeze_record/termux_run_instructions_v01/` remains the Move 51 Termux record.

Move 60 adds a release freeze record. It does not rewrite the earlier candidate
record.
