# Project Witness - Start Here

This folder is the clean, runnable working set: the latest canonical version of
every component, extracted and ready to read, run, and verify.

The inherited Roadmap One stack is standard-library-only Python. The adopted Rust verifier is source-built with Cargo/Rust. No external-truth, production signing, or external anchoring claim is made.

Current publication state (2026-08-10): Roadmap One, Steps 1–70, is complete as a local review/demo stack. Move 70.6 and RT-004 are adopted post-completion repairs. Move 71 Python behaviour freeze is adopted. Rust-hardening Moves 72–85 are adopted. Move 85 v08 is the current adopted technical authority for this publication state. Project Witness is not production-ready. The Move 60 "Local v1 Release" was an earlier milestone; its records are historical.

For the single authoritative current state, read `CURRENT_RELEASE_STATE.md`.

## First files to read

1. `CURRENT_RELEASE_STATE.md` - exact current publication state and limitations.
2. `HANDOFF_MOVES_71_TO_85.md` - adopted Rust-hardening build/run/audit handoff.
3. `REVIEWER_QUICKSTART.md` - reviewer routes and expected result semantics.
4. `STACK_STATUS.md` - verification record, including historical Roadmap One material.
5. `MOVE_INDEX.md` - Roadmap One Steps 1-70 plus adopted Moves 71-85.
6. `REPOSITORY_STRUCTURE.md` - layout and file meanings.
7. `HANDOFF_NOTES.md` - scope and honesty boundary.
8. `LOCAL_V1_RELEASE.md` - historical Move 60 Local v1 milestone.

## Layout

```text
Project_Witness_WORKING_STACK/
  README.md
  START_HERE.md
  LOCAL_V1_RELEASE.md
  STACK_STATUS.md
  MOVE_INDEX.md
  REPOSITORY_STRUCTURE.md
  REVIEWER_QUICKSTART.md
  HANDOFF_NOTES.md
  src/                     <- working component code, in pipeline order
  verify/                  <- inherited + Rust-hardening verification/audit material
  rust/                    <- Cargo workspace for source-built witness-verify
  freeze_record/           <- Move 50 candidate, Move 51 Termux, Move 60 release freeze
  tools/                   <- tests, verifiers, demo, and documentation/release checks
```

## Pipeline order

```text
01 sentinel_core            action gate: ALLOW / BLOCK / DRY_RUN + receipts
02 histor_lite              append-only case store
03 aletheia_evidence_bundle evidence packaging + manifest
04 aletheia_odin_bridge     evidence manifest -> ODIN claim format
05 odin_claim_reasoner      deterministic structural claim reasoner
06 histor_aletheia_importer imports Aletheia bundles into Histor-lite
07 histor_odin_importer     imports ODIN outputs into Histor-lite
08 case_bundle_v02          case bundle format + verifier
09 atlas_registry           read-only controlled vocabulary
10 atlas_release_gate       validates Coordinator output against Atlas
11 coordinator_workflow_v032 orchestrates the full lower stack
12 companion_cli_v031       human-facing entry point
13 unified_case_manifest    cross-component manifest
14 stack_verifier           end-to-end stack output verifier
15 stack_selfcheck_v012     stack inventory / documentation selfcheck
16 evidence_reasoning_demo  evidence -> ODIN reasoning demonstration
17 connected_demo           end-to-end connected pipeline orchestrator
18 one_command_demo         one-command beginner demo wrapper
```

## How to run

### Roadmap One Python/POSIX route

From this folder:

```sh
sh tools/check_local_v1_release.sh
sh tools/validate_handoff.sh
```

Expected Roadmap One markers:

```text
LOCAL_V1_RELEASE_CHECK: PASS
HANDOFF_VALIDATION: PASS
```

Optional individual checks:

```sh
sh tools/check_release_blockers.sh
sh tools/check_reviewer_feedback_round.sh
sh tools/check_five_minute_demo_script.sh
sh tools/check_public_explanation.sh
sh tools/check_private_reviewer_package.sh
sh tools/check_repository_structure.sh
sh tools/check_linux_desktop_instructions.sh
sh tools/check_windows_notes.sh
sh tools/run_all_tests.sh
sh tools/run_independent_verify.sh
sh tools/run_local_v1_verify.sh
sh tools/run_termux_verify.sh
sh tools/run_demo.sh
```


### Adopted Rust-hardening route

Read `HANDOFF_MOVES_71_TO_85.md` before building or running the Rust verifier. From the `rust/` workspace the documented source-build command is:

```sh
cargo build --release
```

The held build/runtime evidence establishes **Android/Termux AArch64 only**. Linux x86_64, Linux AArch64, and Windows x86_64 remain unestablished. A clean Rust bundle result is `INCONCLUSIVE`, exit `3`, not PASS. The Move 85 roadmap deliverable is audit pack v1; the standalone binary and provenance record are supporting measurement artefacts.

## Truth boundary

This stack preserves and verifies structured provenance relationships between
files, hashes, manifests, receipts, statuses, and declared workflow outputs under
tested local conditions.

It does **not** prove external truth or authenticate sources. Move 65 signing is test-only, Move 66 anchoring is local simulation only, and no production-valid signing, real external anchoring, or production-readiness claim is made.

Status exact marker: Current publication state (2026-08-10): Roadmap One, Steps 1–70, is complete as a local review/demo stack. Move 70.6 and RT-004 are adopted post-completion repairs. Move 71 Python behaviour freeze is adopted. Rust-hardening Moves 72–85 are adopted. Move 85 v08 is the current adopted technical authority for this publication state. Project Witness is not production-ready.
