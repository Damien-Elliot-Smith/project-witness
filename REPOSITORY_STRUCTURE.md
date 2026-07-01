# Repository Structure

Status: Local v1 Release. Roadmap complete through Move 60; Moves 61-70 remain future work. The 70-step roadmap is not complete.

This repository is arranged so a reviewer can inspect the working stack without
needing the old archive to run the current release.

## Root files

The root contains the reviewer entry points, status records, release docs, and
roadmap/control documents:

- `README.md` - GitHub landing page.
- `START_HERE.md` - orientation and run path.
- `LOCAL_V1_RELEASE.md` - Move 60 release boundary and validation commands.
- `STACK_STATUS.md` - verification record.
- `MOVE_INDEX.md` - roadmap moves mapped to artifacts.
- `REVIEWER_QUICKSTART.md` - exact commands for reviewers.
- `HANDOFF_NOTES.md` - scope and boundary notes.
- `PUBLIC_EXPLANATION.md` - public-facing short explanation.
- `FIVE_MINUTE_DEMO_SCRIPT.md` - short demo path.
- `RELEASE_BLOCKER_REGISTER.md` and `RELEASE_BLOCKER_REPAIR_LEDGER.md` - Move 59
  release-blocker repair records.
- `REVIEWER_FEEDBACK_*` files - feedback intake and triage structure.
- `LICENSE` - Apache 2.0.

## Directories

- `src/` - working component code, ordered 01-18 in pipeline order.
- `verify/` - independent verifier and the Move 45 full-stack freeze it checks.
- `freeze_record/` - candidate, Termux, and Local v1 Release freeze records.
- `tools/` - shell wrappers for validation, demo, and documentation/release checks.

## Archive relationship

Some earlier roadmap moves point to archived/superseded artifacts that are not
needed to run the current release. The current release is runnable from this
working-stack folder using the commands in `REVIEWER_QUICKSTART.md` and
`LOCAL_V1_RELEASE.md`.

## Review order

1. `LOCAL_V1_RELEASE.md`
2. `README.md`
3. `START_HERE.md`
4. `REVIEWER_QUICKSTART.md`
5. `STACK_STATUS.md`
6. `MOVE_INDEX.md`
7. `HANDOFF_NOTES.md`
8. `src/` and `tools/`

## Release limits

Local v1 Release does not mean production-ready. It does not prove external truth,
authenticate identity, sign outputs, anchor outputs, claim external reviewer
approval, or provide a hosted service.

Status exact marker: Roadmap complete through Move 60; Moves 61-70 remain future work.
