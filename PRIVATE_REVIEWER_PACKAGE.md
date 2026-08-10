# Private Reviewer Package

Purpose: give one reviewer a bounded, honest way to inspect Project Witness without needing a meeting, pitch, or verbal explanation. The Move 70 package instructions below are retained as the Roadmap One review route; the current Rust-hardening authority is identified separately.

Current publication state (2026-08-10): Roadmap One, Steps 1–70, is complete as a local review/demo stack. Move 70.6 and RT-004 are adopted post-completion repairs. Move 71 Python behaviour freeze is adopted. Rust-hardening Moves 72–85 are adopted. Move 85 v08 is the current adopted technical authority for this publication state. Project Witness is not production-ready.

## Current authority for publication review

- `project-witness-MOVE_85_candidate_v08.zip`
- SHA-256: `f512cc9933153d2a6a97c3158515766fc3c9db0a226153cbb010b37fccb59665`
- `CURRENT_RELEASE_STATE.md`
- `HANDOFF_MOVES_71_TO_85.md`
- `verify/audit_pack_v01/README.md`

## Historical Roadmap One package files

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

## Roadmap One package commands

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

Status exact marker: Current publication state (2026-08-10): Roadmap One, Steps 1–70, is complete as a local review/demo stack. Move 70.6 and RT-004 are adopted post-completion repairs. Move 71 Python behaviour freeze is adopted. Rust-hardening Moves 72–85 are adopted. Move 85 v08 is the current adopted technical authority for this publication state. Project Witness is not production-ready.
