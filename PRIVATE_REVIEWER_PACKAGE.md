# Private Reviewer Package

Purpose: give one reviewer a bounded, honest way to inspect Project Witness Local
v1 Release without needing a meeting, pitch, or verbal explanation.

Status: Local v1 Release. Roadmap complete through Move 60; Moves 61-70 remain future work. The 70-step roadmap is not complete.

## Files to send

1. `Project_Witness_WORKING_STACK_v11_MOVE_60.zip`
2. `Project_Witness_WORKING_STACK_v11_MOVE_60.zip.sha256`
3. `PUBLIC_EXPLANATION.md` or a link to the repository.
4. Optional: `PRIVATE_REVIEWER_FEEDBACK_TEMPLATE.md`.

## Ask the reviewer to do only this

1. Verify the checksum.
2. Extract the zip.
3. Read `LOCAL_V1_RELEASE.md`, `README.md`, and `REVIEWER_QUICKSTART.md`.
4. Run the release check and full handoff validation.
5. Report only concrete failures, confusing claims, missing files, or overclaims.

## Exact commands

```sh
sha256sum -c Project_Witness_WORKING_STACK_v11_MOVE_60.zip.sha256
unzip -q Project_Witness_WORKING_STACK_v11_MOVE_60.zip
cd Project_Witness_WORKING_STACK
sh tools/check_local_v1_release.sh
sh tools/validate_handoff.sh
```

Expected key markers:

```text
Project_Witness_WORKING_STACK_v11_MOVE_60.zip: OK
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

Status exact marker: Roadmap complete through Move 60; Moves 61-70 remain future work.
