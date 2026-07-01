# Five-Minute Demo Script

Status: Local v1 Release. Roadmap complete through Move 60; Moves 61-70 remain future work. The 70-step roadmap is not complete.

This is a short, bounded demonstration route. It does not add runtime capability.
It tells a reviewer what to run and what not to claim.

## Setup commands

```sh
sha256sum -c Project_Witness_WORKING_STACK_v11_MOVE_60.zip.sha256
unzip -q Project_Witness_WORKING_STACK_v11_MOVE_60.zip
cd Project_Witness_WORKING_STACK
```

Expected checksum marker:

```text
Project_Witness_WORKING_STACK_v11_MOVE_60.zip: OK
```

## Say this before running anything

> This is Project Witness Local v1 Release. It is a local verification and
> provenance working stack. It does not prove external truth, authenticate people,
> sign outputs, or anchor anything externally. The demo only shows that the local
> package's own structural checks pass under tested conditions.

## Five-minute path

```sh
sh tools/check_local_v1_release.sh
sh tools/run_demo.sh
```

Expected markers:

```text
LOCAL_V1_RELEASE_CHECK: PASS
COMPANION_COMPLETED
verify_ok: true
```

## Slightly longer path

```sh
sh tools/check_release_blockers.sh
sh tools/check_reviewer_feedback_round.sh
sh tools/check_public_explanation.sh
sh tools/validate_handoff.sh
```

Expected markers:

```text
RELEASE_BLOCKERS_CHECK: PASS
REVIEWER_FEEDBACK_ROUND_CHECK: PASS
PUBLIC_EXPLANATION_CHECK: PASS
HANDOFF_VALIDATION: PASS
```

## Do not say

- "This proves truth."
- "This authenticates sources."
- "This is production-ready."
- "External reviewers approved it."
- "The 70-step roadmap is complete."

## Safe closing line

> The demo shows a local package passing its structural verification checks. The
> important claim is limited: the declared files, hashes, manifests, receipts,
> statuses, and workflow outputs are internally consistent under the included
> local checks.

Status exact marker: Roadmap complete through Move 60; Moves 61-70 remain future work.
