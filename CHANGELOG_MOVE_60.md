# Changelog - Move 60 (Freeze Local v1 Release)

Date: 2026-07-01
Roadmap: Step 60 = Freeze Local v1 Release. Step 61 = Decide Next Product Direction, not started.
Scope: release freeze, status consistency, release record, and validation only.

## Files added

- `LOCAL_V1_RELEASE.md` - top-level release boundary, validation commands, and limits.
- `freeze_record/local_v1_release_v01/LOCAL_V1_RELEASE_FREEZE_RECORD.md` - release freeze record.
- `freeze_record/local_v1_release_v01/LOCAL_V1_RELEASE_MANIFEST.md` - release file manifest.
- `freeze_record/local_v1_release_v01/LOCAL_V1_RELEASE_LIMITS.md` - explicit no-overclaim limits.
- `freeze_record/local_v1_release_v01/RELEASE_VALIDATION_COMMANDS.md` - commands required to accept the release.
- `freeze_record/local_v1_release_v01/TREE_HASHES.sha256` - release tree hashes for reviewer-visible files.
- `tools/check_local_v1_release.sh` - POSIX-sh release checker. Prints `LOCAL_V1_RELEASE_CHECK: PASS` only when all release checks pass.
- `CHANGELOG_MOVE_60.md` - this file.

## Files updated

- `README.md`, `START_HERE.md`, `REVIEWER_QUICKSTART.md`, `STACK_STATUS.md`, `MOVE_INDEX.md`, `HANDOFF_NOTES.md`, `REPOSITORY_STRUCTURE.md` - current status now says Local v1 Release and `Roadmap complete through Move 60; Moves 61-70 remain future work`.
- `PRIVATE_REVIEWER_PACKAGE.md`, `PUBLIC_EXPLANATION.md`, `FIVE_MINUTE_DEMO_SCRIPT.md`, `REVIEWER_FEEDBACK_ROUND.md`, `REVIEWER_FEEDBACK_LEDGER.md`, `REVIEWER_FEEDBACK_TRIAGE.md` - active reviewer/public docs now point at the Move 60 release package and preserve the no-external-feedback boundary.
- `RELEASE_BLOCKER_REGISTER.md`, `RELEASE_BLOCKER_REPAIR_LEDGER.md` - carried Move 59 blocker repairs into the Move 60 release freeze without inventing external reviewer blockers.
- `LINUX_DESKTOP_RUN_INSTRUCTIONS.md`, `WINDOWS_NOTES.md` - status footer updated only.
- Documentation checkers updated so their current status marker points at Move 60.
- `tools/validate_handoff.sh` wrapper hardening: generated Python cache artifacts are cleaned between validation stages so a full validation run is repeatable after component tests. No validation stage was removed or weakened.

## Not changed

- No component code behaviour changed.
- No schemas changed.
- No architecture changed.
- No features added: no GUI, app, networking, cloud, signing, anchoring, LLM integration, autonomy, new Sentinel actions, Rust, or production claims.
- No external reviewer approval is claimed.
- `REVIEWER_FEEDBACK_LEDGER.md` still records `NO_EXTERNAL_FEEDBACK_RECORDED`.
- Step 61 was not started.

## Validation

Fresh extraction checks pass:

```text
LOCAL_V1_RELEASE_CHECK: PASS
RELEASE_BLOCKERS_CHECK: PASS
REVIEWER_FEEDBACK_ROUND_CHECK: PASS
FIVE_MINUTE_DEMO_SCRIPT_CHECK: PASS
PUBLIC_EXPLANATION_CHECK: PASS
PRIVATE_REVIEWER_PACKAGE_CHECK: PASS
REPOSITORY_STRUCTURE_CHECK: PASS
LINUX_DESKTOP_INSTRUCTIONS_CHECK: PASS
WINDOWS_NOTES_CHECK: PASS
HANDOFF_VALIDATION: PASS
```

## Status

Move 60 is complete only if the checks above pass. Roadmap complete through Move 60; Moves 61-70 remain future work. This is a Local v1 Release, not a production system. The 70-step roadmap is not complete.
