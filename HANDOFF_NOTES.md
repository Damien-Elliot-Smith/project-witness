# Handoff Notes

Scope and boundary notes for anyone receiving this package.

## What this package is

This contains the **Project Witness Roadmap One working stack** (Steps 1-70
complete as a local review/demo stack): its runnable Python working stack, frozen
verification artifacts, historical freeze records (including the earlier Move 60
"Local v1 Release" milestone), and scripts needed to run those checks locally.
Rust-hardening Moves 71-85 are also adopted; their verifier is source-built with
Cargo/Rust. See `HANDOFF_MOVES_71_TO_85.md` for that block.

## Relationship to earlier freeze records

`freeze_record/local_v1_candidate_v01/` remains the Move 50 candidate record.
`freeze_record/termux_run_instructions_v01/` remains the Move 51 Termux record.
`freeze_record/local_v1_release_v01/` is the Move 60 release freeze record.

Historical records are not rewritten to pretend they were release records.
`LOCAL_V1_RELEASE.md` and the Move 60 freeze record document the earlier Move 60
milestone only. The current state is documented by `CURRENT_RELEASE_STATE.md`.

## Authoritative current index

`MOVE_INDEX.md` is the current overall stack index. Where an older component-local
or freeze-time document differs in scope, the older document describes that older
component/freeze state; `MOVE_INDEX.md` and `CURRENT_RELEASE_STATE.md` describe the assembled current publication state. `LOCAL_V1_RELEASE.md` remains the historical Move 60 milestone.

## Roadmap status

- Roadmap One, Steps **1-70**, is complete as a local review/demo stack.
- Move 70.6 and RT-004 are adopted post-completion repairs.
- Move 71 Python behaviour freeze is adopted.
- Rust-hardening Moves **72-85** are adopted.
- Move 85 v08 is the current adopted technical authority for this publication state.
- Completion of the Rust-hardening block does not mean Project Witness is production-ready.

## Honesty boundary

This stack verifies structured provenance relationships under tested local
conditions. It does not prove external truth, authenticate real-world identity,
establish source trust or production readiness. Move 65 signing is test-only and
Move 66 anchoring is local simulation only; no production-valid signing or real
external anchoring is claimed. Treat Roadmap One PASS markers as "the structural
checks held under local test conditions," nothing more. The adopted Rust clean
bundle observation is INCONCLUSIVE / exit 3, not PASS.

No external reviewer approval is claimed. The feedback ledger records
`NO_EXTERNAL_FEEDBACK_RECORDED`.

## Licence

Apache License 2.0. See `LICENSE`.

Status exact marker: Current publication state (2026-08-10): Roadmap One, Steps 1–70, is complete as a local review/demo stack. Move 70.6 and RT-004 are adopted post-completion repairs. Move 71 Python behaviour freeze is adopted. Rust-hardening Moves 72–85 are adopted. Move 85 v08 is the current adopted technical authority for this publication state. Project Witness is not production-ready.
