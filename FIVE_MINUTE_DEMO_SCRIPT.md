# Five-Minute Demo Script

Current publication state (2026-08-10): Roadmap One, Steps 1–70, is complete as a local review/demo stack. Move 70.6 and RT-004 are adopted post-completion repairs. Move 71 Python behaviour freeze is adopted. Rust-hardening Moves 72–85 are adopted. Move 85 v08 is the current adopted technical authority for this publication state. Project Witness is not production-ready.

This is a short, bounded demonstration route. It does not add runtime capability.
It tells a reviewer what to run and what not to claim.

## Roadmap One demo setup commands

```sh
sha256sum -c Project_Witness_WORKING_STACK_v20_MOVE_70.zip.sha256
unzip -q Project_Witness_WORKING_STACK_v20_MOVE_70.zip
cd Project_Witness_WORKING_STACK
```

Expected checksum marker:

```text
Project_Witness_WORKING_STACK_v20_MOVE_70.zip: OK
```

## Say this before running anything

> This is the completed Project Witness Roadmap One local review/demo package. It is a local verification and
> provenance working stack. It does not prove external truth, authenticate people,
> provide production-valid signing or real external anchoring. Move 65 signing is test-only and Move 66 anchoring is local simulation only. The demo only shows that the local
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
- "Project Witness is finished or production-ready."

## Adopted Rust-hardening demonstration

For the current Moves 71-85 demonstration, use `HANDOFF_MOVES_71_TO_85.md` and
`verify/demo_v01/README.md`. The clean Rust observation is `INCONCLUSIVE`, exit
`3`, not PASS. The Rust verifier detects the demonstrated top-level tamper but
does not detect the demonstrated nested evidence tamper at
`coordinator_output/aletheia_bundle/evidence/evidence_001.bin`; the Python lane
does detect it. Audit pack v1 is the Move 85 roadmap deliverable.

## Safe closing line

> The Roadmap One demo shows a local package passing its structural verification checks. The
> important claim is limited: the declared files, hashes, manifests, receipts,
> statuses, and workflow outputs are internally consistent under the included
> local checks.

The stack is not production-ready, and a passing demo
does not prove real-world truth: it does not prove that any evidence is
factually correct, only that the recorded run is internally consistent.

Status exact marker: Current publication state (2026-08-10): Roadmap One, Steps 1–70, is complete as a local review/demo stack. Move 70.6 and RT-004 are adopted post-completion repairs. Move 71 Python behaviour freeze is adopted. Rust-hardening Moves 72–85 are adopted. Move 85 v08 is the current adopted technical authority for this publication state. Project Witness is not production-ready.

