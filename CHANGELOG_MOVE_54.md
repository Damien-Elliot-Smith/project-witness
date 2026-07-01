# Changelog — Move 54 (Clean GitHub Repository Structure)

Date: 2026-06-29
Roadmap: Step 54 = Clean GitHub Repository Structure (Step 51 = Termux, Step 52 =
Linux Desktop, Step 53 = Windows Notes, Step 55 = not started).
Scope: repository-structure and documentation-consistency cleanup only.

## Files added

- `README.md` — GitHub landing page: overview, what it is / is not, read-first
  pointers, quick run, layout, licence, and roadmap status.
- `REPOSITORY_STRUCTURE.md` — explains the repo root, `src/`, `verify/`,
  `freeze_record/`, `tools/`, the reviewer read-first order, and that
  archived/superseded artifacts are referenced by the move index but are not
  needed to run the working stack.
- `LICENSE` — Apache License 2.0 (the licence decision is now made).
- `tools/check_repository_structure.sh` — POSIX-sh checker that fails closed if
  required files/directories are missing or if the main status docs are not
  consistently "complete through Move 54". Prints `REPOSITORY_STRUCTURE_CHECK: PASS`
  only when all checks pass.
- `CHANGELOG_MOVE_54.md` — this file.

## Files updated (documentation consistency only)

- `START_HERE.md` — roadmap status now "complete through Move 54"; added README /
  REPOSITORY_STRUCTURE pointers.
- `REVIEWER_QUICKSTART.md` — "Moves 55–70 remain future work".
- `STACK_STATUS.md` — added the Move 54 note; status now through Move 54.
- `MOVE_INDEX.md` — title is now "Roadmap Steps 1–54"; added rows for Moves 52, 53,
  and 54; status section now "complete through Move 54 / Moves 55–70 remain future
  work".
- `HANDOFF_NOTES.md` — roadmap status through Move 54; licence section now states
  Apache 2.0 (`LICENSE`) and that the public GitHub repo is the review target.
- `LINUX_DESKTOP_RUN_INSTRUCTIONS.md`, `WINDOWS_NOTES.md` — status footers updated
  to "complete through Move 54" (removed the per-document self-reference); no
  instructional content changed.
- `LICENSE_DECISION_NEEDED.md` — marked RESOLVED (Apache 2.0, see `LICENSE`);
  retained as a historical note.

Historical changelogs (`CHANGELOG_MOVE_52.md`, `CHANGELOG_MOVE_53.md`,
`CHANGELOG_REPAIR_v02.md`) were intentionally left unchanged as accurate records.

## Not changed

- No component code behaviour changed.
- No schemas changed.
- No architecture changed.
- No features added (no GUI, app, networking, cloud, signing, anchoring, LLM
  integration, autonomy, new Sentinel actions, Rust, or production claims).
- `src/`, `verify/`, and `freeze_record/` are byte-identical to v04.
- Step 55 was not started.

## Validation

- `sh tools/check_repository_structure.sh` → `REPOSITORY_STRUCTURE_CHECK: PASS`.
- Existing validation commands were not weakened:
  - `sh tools/validate_handoff.sh` → `HANDOFF_VALIDATION: PASS`
  - `sh tools/check_linux_desktop_instructions.sh` → `LINUX_DESKTOP_INSTRUCTIONS_CHECK: PASS`
  - `sh tools/check_windows_notes.sh` → `WINDOWS_NOTES_CHECK: PASS`

## Status

Move 54 is complete only if the checks above pass. Roadmap complete **through
Move 54**; Moves 55–70 remain future work. This is a Local v1 Candidate, not a
final Local v1 Release. The 70-step roadmap is not complete.
