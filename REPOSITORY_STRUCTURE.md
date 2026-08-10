# Repository Structure

Status: Roadmap One (Steps 1-70) complete as a local review/demo stack. Not production-ready. Part Two has started.

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

Status exact marker: Project Witness Roadmap One, Steps 1-70, is complete as a local review/demo stack. Post-completion repairs Move 70.6 and RT-004 are adopted. The Move 71 Python behaviour freeze is adopted. Rust Moves 72-78 are adopted, including ZipGuard archive safety. Part Two has started. Move 79 (verification-only Python/Rust agreement harness) is the current candidate; no full bundle verification capability exists or is claimed.
