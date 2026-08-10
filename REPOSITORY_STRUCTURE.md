# Repository Structure

Current publication state (2026-08-10): Roadmap One, Steps 1–70, is complete as a local review/demo stack. Move 70.6 and RT-004 are adopted post-completion repairs. Move 71 Python behaviour freeze is adopted. Rust-hardening Moves 72–85 are adopted. Move 85 v08 is the current adopted technical authority for this publication state. Project Witness is not production-ready.

This repository is arranged so a reviewer can inspect the working stack without
needing the old archive to inspect the current adopted tree. Roadmap One and the Rust-hardening block have distinct run/build prerequisites.

## Root files

The root contains the reviewer entry points, status records, release docs, and
roadmap/control documents:

- `README.md` - GitHub landing page.
- `START_HERE.md` - orientation and run path.
- `CURRENT_RELEASE_STATE.md` - current Move 85 publication state.
- `HANDOFF_MOVES_71_TO_85.md` - adopted Rust-hardening handoff.
- `LOCAL_V1_RELEASE.md` - historical Move 60 release boundary and validation commands.
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
- `verify/` - inherited verifier material plus adopted agreement, corruption, report, demo, portable-build, and audit-pack material.
- `rust/` - Cargo workspace containing source-built `witness-verify`.
- `freeze_record/` - candidate, Termux, and Local v1 Release freeze records.
- `tools/` - shell wrappers for validation, demo, and documentation/release checks.

## Archive relationship

Some earlier roadmap moves point to archived/superseded artifacts that are not
needed for current inspection. The inherited Roadmap One Python path is runnable
using the commands in `REVIEWER_QUICKSTART.md` and `LOCAL_V1_RELEASE.md`. The
adopted Rust verifier has a separate source-build/run route in
`HANDOFF_MOVES_71_TO_85.md` and requires Cargo/Rust; held build/runtime evidence
establishes Android/Termux AArch64 only.

## Review order

1. `README.md`
2. `START_HERE.md`
3. `CURRENT_RELEASE_STATE.md`
4. `HANDOFF_MOVES_71_TO_85.md`
5. `REVIEWER_QUICKSTART.md`
6. `FIVE_MINUTE_DEMO_SCRIPT.md`
7. `STACK_STATUS.md`
8. `MOVE_INDEX.md`
9. `HANDOFF_NOTES.md`
10. `verify/audit_pack_v01/`, then `src/`, `rust/`, and `tools/` as needed

## Release limits

The historical Local v1 Release milestone and the current Move 85 publication state do not mean production-ready. It does not prove external truth,
authenticate identity, provide production-valid signing or real external anchoring,
claim external reviewer approval, or provide a hosted service. Move 65 signing is
test-only and Move 66 anchoring is local simulation only.

Status exact marker: Current publication state (2026-08-10): Roadmap One, Steps 1–70, is complete as a local review/demo stack. Move 70.6 and RT-004 are adopted post-completion repairs. Move 71 Python behaviour freeze is adopted. Rust-hardening Moves 72–85 are adopted. Move 85 v08 is the current adopted technical authority for this publication state. Project Witness is not production-ready.
