# Changelog - Move 57 (Five-Minute Demo Script)

Date: 2026-06-30
Roadmap: Step 57 = Build Five-Minute Demo Script (Step 55 = Private Reviewer Package, Step 56 = Public-Facing Short Explanation, Step 58 = Reviewer Feedback Round - not started).
Scope: public/private demonstration script and documentation-consistency update only.

## Correction note

A previous draft package labelled Move 57 incorrectly contained reviewer-feedback-round material. The clean roadmap says Move 57 is **Build Five-Minute Demo Script** and Move 58 is **Run Reviewer Feedback Round**. This package is the corrected Move 57 and is built from the verified Move 56 package, not from the misnumbered feedback-round package.

## Added

- `FIVE_MINUTE_DEMO_SCRIPT.md` - a timed five-minute demonstration script with exact commands, expected markers, reviewer-safe wording, and honesty boundaries.
- `tools/check_five_minute_demo_script.sh` - POSIX-sh checker that fails closed if the demo script, required commands, current status wording, or truth-boundary wording is missing. Prints `FIVE_MINUTE_DEMO_SCRIPT_CHECK: PASS` only when all checks pass.
- `CHANGELOG_MOVE_57.md` - this file.

## Updated (documentation consistency only)

- `README.md` - status now complete through Move 57; added the five-minute demo script to the read-first list.
- `START_HERE.md` - status and run-command list updated for Move 57.
- `REVIEWER_QUICKSTART.md` - status now Moves 58-70 remain future work; mentions the five-minute demo script/check.
- `STACK_STATUS.md` - added the Move 57 verification note and status.
- `MOVE_INDEX.md` - title is now Roadmap Steps 1-57; added row for Move 57; status section now complete through Move 57 / Moves 58-70 remain future work.
- `HANDOFF_NOTES.md` - roadmap status updated through Move 57.
- `REPOSITORY_STRUCTURE.md` - includes the new demo script and checker.
- `PUBLIC_EXPLANATION.md` - status and safe public wording updated through Move 57.
- `PRIVATE_REVIEWER_PACKAGE.md` - status and reviewer route updated through Move 57.
- `LINUX_DESKTOP_RUN_INSTRUCTIONS.md`, `WINDOWS_NOTES.md` - status footers updated to Move 57 only; platform instructions unchanged.
- Existing check scripts updated so their status consistency checks expect Move 57 instead of Move 56.

Historical changelogs for Moves 52-56 were intentionally left unchanged as records of earlier packages.

## Not changed

- No component code behaviour changed.
- No schemas changed.
- No architecture changed.
- No features added (no GUI, app, networking, cloud, signing, anchoring, LLM integration, autonomy, new Sentinel actions, Rust, or production claims).
- `src/`, `verify/`, and `freeze_record/` are byte-identical to v07 / Move 56.
- Step 58 was not started.

## Validation

- `sh tools/check_five_minute_demo_script.sh` -> `FIVE_MINUTE_DEMO_SCRIPT_CHECK: PASS`
- `sh tools/check_public_explanation.sh` -> `PUBLIC_EXPLANATION_CHECK: PASS`
- `sh tools/check_private_reviewer_package.sh` -> `PRIVATE_REVIEWER_PACKAGE_CHECK: PASS`
- `sh tools/check_repository_structure.sh` -> `REPOSITORY_STRUCTURE_CHECK: PASS`
- `sh tools/check_linux_desktop_instructions.sh` -> `LINUX_DESKTOP_INSTRUCTIONS_CHECK: PASS`
- `sh tools/check_windows_notes.sh` -> `WINDOWS_NOTES_CHECK: PASS`
- `sh tools/validate_handoff.sh` -> `HANDOFF_VALIDATION: PASS`

## Status

Move 57 is complete only if the checks above pass. Roadmap complete through Move 57; Moves 58-70 remain future work. This is a Local v1 Candidate, not a final Local v1 Release. The 70-step roadmap is not complete.
