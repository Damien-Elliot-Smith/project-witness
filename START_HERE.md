# Project Witness - Start Here

This folder is the clean, runnable working set: the latest canonical version of
every component, extracted and ready to read, run, and verify.

Standard library only. No network. No signing. No external anchoring.

Status: **Local v1 Release**. Roadmap complete through Move 60; Moves 61-70 remain future work. The 70-step roadmap is not complete.

## First files to read

1. `LOCAL_V1_RELEASE.md` - what the Local v1 Release does and does not claim.
2. `REVIEWER_QUICKSTART.md` - exact commands and expected PASS markers.
3. `STACK_STATUS.md` - verification record.
4. `MOVE_INDEX.md` - roadmap moves mapped to artifacts.
5. `REPOSITORY_STRUCTURE.md` - layout and file meanings.
6. `HANDOFF_NOTES.md` - scope and honesty boundary.

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
  verify/                  <- independent verifier + Move 45 freeze it checks
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

From this folder:

```sh
sh tools/check_local_v1_release.sh
sh tools/validate_handoff.sh
```

Expected final markers:

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

## Truth boundary

This stack preserves and verifies structured provenance relationships between
files, hashes, manifests, receipts, statuses, and declared workflow outputs under
tested local conditions.

It does **not** prove external truth, authenticate sources, sign outputs,
externally anchor outputs, or claim production readiness.

Status exact marker: Roadmap complete through Move 60; Moves 61-70 remain future work.
