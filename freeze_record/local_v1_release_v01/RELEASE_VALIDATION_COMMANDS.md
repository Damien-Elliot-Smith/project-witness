# Release Validation Commands

Date: 2026-07-01
Status exact marker: Roadmap complete through Move 60; Moves 61-70 remain future work.

Run from the extracted `Project_Witness_WORKING_STACK/` directory.

```sh
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

Expected final markers:

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

A failure in any command means Move 60 is not accepted.
