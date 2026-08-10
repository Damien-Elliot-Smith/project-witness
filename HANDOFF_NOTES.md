# Handoff Notes

Scope and boundary notes for anyone receiving this package.

## What this package is

This is the **Project Witness Roadmap One working stack** (Steps 1-70 complete as
a local review/demo stack): the current runnable working stack, the frozen
verification artifacts, the historical freeze records (including the earlier
Move 60 "Local v1 Release" milestone), and the scripts needed to run the checks
locally. Part Two has started.

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
component/freeze state; `MOVE_INDEX.md` and `LOCAL_V1_RELEASE.md` describe the
assembled current release package.

## Roadmap status

- Roadmap complete through **Move 60** (Freeze Local v1 Release).
- Moves **61-70 remain future work**.
- Do **not** describe the 70-step roadmap as complete.
- Local v1 Release does not mean production-ready. It is not production-ready.

## Honesty boundary

This stack verifies structured provenance relationships under tested local
conditions. It does not prove external truth, authenticate real-world identity,
establish source trust, sign outputs, or externally anchor outputs. Treat every
PASS marker as "the structural checks held under local test conditions," nothing
more.

No external reviewer approval is claimed. The feedback ledger records
`NO_EXTERNAL_FEEDBACK_RECORDED`.

## Licence

Apache License 2.0. See `LICENSE`.

Status exact marker: Project Witness Roadmap One, Steps 1-70, is complete as a local review/demo stack. Post-completion repairs Move 70.6 and RT-004 are adopted. The Move 71 Python behaviour freeze is adopted. Rust Moves 72-78 are adopted, including ZipGuard archive safety. Part Two has started. Move 79 (verification-only Python/Rust agreement harness) is the current candidate; no full bundle verification capability exists or is claimed.
