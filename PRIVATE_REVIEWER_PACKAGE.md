# Private Reviewer Package

Purpose: give one reviewer a bounded, honest way to inspect the Project Witness
Roadmap One final package without needing a meeting, pitch, or verbal explanation.

Status: Roadmap One (Steps 1-70) complete as a local review/demo stack. Not production-ready. Part Two has started.

## Files to send

1. `Project_Witness_WORKING_STACK_v20_MOVE_70.zip`
2. `Project_Witness_WORKING_STACK_v20_MOVE_70.zip.sha256`
3. `PUBLIC_EXPLANATION.md` or a link to the repository.
4. Optional: `PRIVATE_REVIEWER_FEEDBACK_TEMPLATE.md`.

## Ask the reviewer to do only this

1. Verify the checksum.
2. Extract the zip.
3. Read `CURRENT_RELEASE_STATE.md`, `README.md`, and `REVIEWER_QUICKSTART.md`.
4. Run the release check and full handoff validation.
5. Report only concrete failures, confusing claims, missing files, or overclaims.

## Exact commands

```sh
sha256sum -c Project_Witness_WORKING_STACK_v20_MOVE_70.zip.sha256
unzip -q Project_Witness_WORKING_STACK_v20_MOVE_70.zip
cd Project_Witness_WORKING_STACK
sh tools/check_local_v1_release.sh
sh tools/validate_handoff.sh
```

Expected key markers:

```text
Project_Witness_WORKING_STACK_v20_MOVE_70.zip: OK
LOCAL_V1_RELEASE_CHECK: PASS
HANDOFF_VALIDATION: PASS
```

## Boundary for the reviewer

Do not ask the reviewer to judge whether Project Witness proves external truth.
It does not. Ask them whether the package runs, whether the claims match the
outputs, whether the limitations are honest, and whether the documentation makes
false or confusing claims.

No external reviewer approval is claimed in this package. The feedback ledger
records `NO_EXTERNAL_FEEDBACK_RECORDED`.

Status exact marker: Project Witness Roadmap One, Steps 1-70, is complete as a local review/demo stack. Post-completion repairs Move 70.6 and RT-004 are adopted. The Move 71 Python behaviour freeze is adopted. Rust Moves 72-78 are adopted, including ZipGuard archive safety. Part Two has started. Move 79 (verification-only Python/Rust agreement harness) is the current candidate; no full bundle verification capability exists or is claimed.
