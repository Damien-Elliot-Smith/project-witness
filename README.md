# Project Witness - Working Stack

A local, deterministic, standard-library-only integrity-verification stack. It
preserves and verifies structured provenance relationships between files, hashes,
manifests, receipts, statuses, and declared workflow outputs under tested local
conditions.

This repository is the **runnable working stack**. It is the **Local v1 Release**.
The 70-step roadmap is **not** complete - it is complete **through Move 60**
(Freeze Local v1 Release); Moves 61-70 remain future work.

## What it is

- Pure standard-library Python. No third-party packages, no network, no build step.
- A pipeline of small components (Sentinel, Histor-lite, Aletheia, the
  Aletheia-to-ODIN bridge, ODIN, importers, Case Bundle, Atlas, Coordinator,
  Companion) plus verifiers and a self-check.
- Reproducible: every claim in `STACK_STATUS.md` can be re-run from the scripts in
  `tools/`.
- Demonstrable: `FIVE_MINUTE_DEMO_SCRIPT.md` gives a short, bounded demo path
  without adding new runtime capability.
- Frozen for Local v1 in `LOCAL_V1_RELEASE.md` and
  `freeze_record/local_v1_release_v01/`.

## What it is NOT

- It does **not** prove external truth or that any evidence is factually correct.
- It does **not** authenticate real-world identity or source trust.
- It does **not** sign outputs or anchor them to any external timestamp/ledger.
- It is **not** production-ready, and has no GUI, app, network service, or cloud
  component.
- It does **not** claim external reviewer approval. The feedback ledger records
  `NO_EXTERNAL_FEEDBACK_RECORDED`.

## Read these first

1. `LOCAL_V1_RELEASE.md` - release boundary, validation commands, and limits.
2. `START_HERE.md` - orientation and layout.
3. `FIVE_MINUTE_DEMO_SCRIPT.md` - short demo script and safe spoken wording.
4. `RELEASE_BLOCKER_REGISTER.md` - release-blocker register and repair outcome.
5. `REVIEWER_FEEDBACK_ROUND.md` - feedback-round instructions and honesty boundary.
6. `REVIEWER_QUICKSTART.md` - checksum, extraction, exact commands, expected markers.
7. `PUBLIC_EXPLANATION.md` - plain-language public explanation and safe wording.
8. `REPOSITORY_STRUCTURE.md` - what every top-level directory and file is.
9. `PRIVATE_REVIEWER_PACKAGE.md` - how a private reviewer should inspect and report back.
10. Platform notes: `LINUX_DESKTOP_RUN_INSTRUCTIONS.md`, `WINDOWS_NOTES.md`.

## Quick run

From the repository root, with `python3` and a POSIX shell:

```sh
sh tools/check_local_v1_release.sh
sh tools/validate_handoff.sh
```

Expected final lines: `LOCAL_V1_RELEASE_CHECK: PASS` and
`HANDOFF_VALIDATION: PASS`. Individual commands and expected markers are in
`REVIEWER_QUICKSTART.md`.

## Layout

- `src/` - the latest version of each component, in pipeline order.
- `verify/` - independent verifier and the frozen full-stack component freeze.
- `freeze_record/` - the Move 50 candidate record, Move 51 Termux instructions,
  and the Move 60 Local v1 Release freeze record.
- `tools/` - runnable shell wrappers for tests, verifiers, demo, review checks,
  release-blocker checks, and the Local v1 release check.

See `REPOSITORY_STRUCTURE.md` for the full breakdown.

## Licence

Apache License 2.0 - see `LICENSE`.

## Status

Local v1 Release. Roadmap complete through Move 60; Moves 61-70 remain future work. Do not describe the 70-step roadmap as complete.

Status exact marker: Roadmap complete through Move 60; Moves 61-70 remain future work.
