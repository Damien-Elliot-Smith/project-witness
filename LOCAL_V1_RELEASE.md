# Local v1 Release - Project Witness

Date: 2026-07-01
Roadmap: Step 60 = Freeze Local v1 Release.
Status exact marker: Roadmap complete through Move 60; Moves 61-70 remain future work.

## Release statement

This package is the Project Witness **Local v1 Release**. It freezes the local,
standard-library-only working stack that was previously carried as a Local v1
Candidate.

The release is local and bounded. It verifies structured provenance relationships
between files, hashes, manifests, receipts, statuses, and declared workflow
outputs under tested local conditions.

## What is frozen

The release freezes the current reviewable package after Moves 51-59:

- Termux run instructions.
- Linux desktop run instructions.
- Windows notes, with WSL2 as the recommended run route.
- Clean GitHub repository structure.
- Private reviewer package.
- Public-facing short explanation.
- Five-minute demo script.
- Reviewer feedback round structure.
- Release-blocker register and repair ledger.

The component code under `src/`, the independent verifier under `verify/`, and
the earlier candidate/Termux freeze records remain bounded by their existing
freeze records. Move 60 does not change runtime behaviour.

## What is not claimed

This release does not prove external truth. It does not authenticate real-world
identity or source trust. It does not sign outputs or externally anchor outputs.
It is not production-ready. It is not a hosted service. It has no GUI, app,
network service, cloud backend, autonomy, or LLM integration.

No external reviewer approval is claimed. The reviewer feedback ledger still
records `NO_EXTERNAL_FEEDBACK_RECORDED`.

## Validation required for this release

From the repository root:

```sh
sha256sum -c Project_Witness_WORKING_STACK_v11_MOVE_60.zip.sha256
sh tools/check_local_v1_release.sh
sh tools/check_release_blockers.sh
sh tools/check_reviewer_feedback_round.sh
sh tools/check_five_minute_demo_script.sh
sh tools/check_public_explanation.sh
sh tools/check_private_reviewer_package.sh
sh tools/check_repository_structure.sh
sh tools/check_linux_desktop_instructions.sh
sh tools/check_windows_notes.sh
sh tools/validate_handoff.sh
```

Expected markers:

```text
LOCAL_V1_RELEASE_CHECK: PASS
RELEASE_BLOCKERS_CHECK: PASS
REVIEWER_FEEDBACK_ROUND_CHECK: PASS
FIVE_MINUTE_DEMO_SCRIPT_CHECK: PASS
PUBLIC_EXPLANATION_CHECK: PASS
PRIVATE_REVIEWER_PACKAGE_CHECK: PASS
REPOSITORY_STRUCTURE_CHECK: PASS
LINUX_DESKTOP_INSTRUCTIONS_CHECK: PASS
WINDOWS_NOTES_CHECK: PASS
HANDOFF_VALIDATION: PASS
```

## Future work boundary

Moves 61-70 remain future work. Do not describe the 70-step roadmap as complete.
Do not start product-direction work, second Sentinel actions, signing, anchoring,
GUI, Android, Windows wrappers, or final review inside this Move 60 package.
