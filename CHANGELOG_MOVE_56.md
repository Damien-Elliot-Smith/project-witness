# Changelog - Move 56 (Public Explanation)

Date: 2026-06-30
Roadmap: Step 56 = Build Public Explanation (Step 55 = Private Reviewer Package,
Step 57 = Reviewer Feedback Round - not started).
Scope: public-facing explanation, documentation consistency, and presence/content
checks only.

## Files added

- `PUBLIC_EXPLANATION.md` - plain-language public explanation: what Project
  Witness is, what problem it addresses, what a reviewer can run, what PASS means,
  what PASS does not mean, explicit non-claims, reviewer path, and safe public
  wording.
- `tools/check_public_explanation.sh` - POSIX-sh checker that fails closed if the
  public explanation is missing, stale, or lacks required honesty boundaries.
  Prints `PUBLIC_EXPLANATION_CHECK: PASS` only when all checks pass.
- `CHANGELOG_MOVE_56.md` - this file.

## Files updated (documentation consistency only)

- `README.md` - status now complete through Move 56; public explanation added to
  read-first pointers.
- `START_HERE.md` - public reader pointer added; layout and roadmap wording
  updated.
- `REVIEWER_QUICKSTART.md` - current package name and Move 56 status wording
  updated; public explanation check added to the expected-check list.
- `REPOSITORY_STRUCTURE.md` - lists `PUBLIC_EXPLANATION.md` and
  `tools/check_public_explanation.sh`.
- `MOVE_INDEX.md` - title is now Roadmap Steps 1-56; added Move 56 row; status now
  complete through Move 56 / Moves 57-70 remain future work.
- `HANDOFF_NOTES.md` - public explanation section added; roadmap status updated.
- `STACK_STATUS.md` - added the Move 56 status note and current status footer.
- `PRIVATE_REVIEWER_PACKAGE.md` - current package name and status wording updated;
  public explanation check added to private-review command list.
- `LINUX_DESKTOP_RUN_INSTRUCTIONS.md`, `WINDOWS_NOTES.md` - status footers updated
  to complete through Move 56; no platform instructions changed.
- `tools/check_repository_structure.sh` - current-status wording updated to Move
  56 and the public explanation file added to required-file/status checks.
- `tools/check_private_reviewer_package.sh` - current-status wording updated to
  Move 56 and the public explanation file added to required checks.
- `tools/validate_handoff.sh` - wrapper hardened so validation stages are called
  directly rather than through a pipe-fed loop. Child stages still run with stdin
  closed. No validation stage was removed or weakened.

Historical changelogs (`CHANGELOG_MOVE_52.md`, `CHANGELOG_MOVE_53.md`,
`CHANGELOG_MOVE_54.md`, `CHANGELOG_MOVE_55.md`, `CHANGELOG_REPAIR_v02.md`) were
intentionally left unchanged as accurate records.

## Not changed

- No component code behaviour changed.
- No schemas changed.
- No architecture changed.
- No features added (no GUI, app, networking, cloud, signing, anchoring, LLM
  integration, autonomy, new Sentinel actions, Rust, or production claims).
- `src/`, `verify/`, and `freeze_record/` remain byte-identical to v06.
- Step 57 was not started.

## Validation

- `sh tools/check_public_explanation.sh` -> `PUBLIC_EXPLANATION_CHECK: PASS`
- `sh tools/check_private_reviewer_package.sh` -> `PRIVATE_REVIEWER_PACKAGE_CHECK: PASS`
- `sh tools/check_repository_structure.sh` -> `REPOSITORY_STRUCTURE_CHECK: PASS`
- `sh tools/validate_handoff.sh` -> `HANDOFF_VALIDATION: PASS`
- `sh tools/check_linux_desktop_instructions.sh` -> `LINUX_DESKTOP_INSTRUCTIONS_CHECK: PASS`
- `sh tools/check_windows_notes.sh` -> `WINDOWS_NOTES_CHECK: PASS`

## Status

Move 56 is complete only if the checks above pass. Roadmap complete through Move
56; Moves 57-70 remain future work. This is a Local v1 Candidate, not a final
Local v1 Release. The 70-step roadmap is not complete.
