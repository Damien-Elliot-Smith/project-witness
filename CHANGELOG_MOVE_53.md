# Changelog — Move 53 (Windows Notes)

Date: 2026-06-29
Roadmap: Step 53 = Windows Notes (Step 51 = Termux, Step 52 = Linux Desktop,
Step 54 = Clean GitHub Repository Structure — not started).
Scope: documentation and a presence/content check only. Notes/readiness, not a
native Windows port.

## Added

- `WINDOWS_NOTES.md` — honest Windows notes: what can be inspected safely on
  Windows; a clear statement that native Windows execution has **not** been
  directly tested; the recommended WSL2 + Ubuntu route (then follow
  `LINUX_DESKTOP_RUN_INSTRUCTIONS.md`); possible native requirements (Python 3,
  PowerShell/Command Prompt, zip extraction, checksum via `certutil` or
  `Get-FileHash`); likely path and line-ending issues; expected limitations;
  the no-network / no-extra-packages note; known PASS markers; and what failure
  means.
- `tools/check_windows_notes.sh` — checks `WINDOWS_NOTES.md` exists, mentions
  WSL/WSL2, states this is notes/readiness rather than a guaranteed native port
  unless directly tested, points to `LINUX_DESKTOP_RUN_INSTRUCTIONS.md`, and that
  the required existing scripts (`validate_handoff.sh`, `run_all_tests.sh`,
  `run_demo.sh`) are present. Prints `WINDOWS_NOTES_CHECK: PASS` only when all
  checks pass; fails closed (non-zero) otherwise. POSIX sh.

## Updated (minimal)

- `REVIEWER_QUICKSTART.md` — pointers for Linux (Linux instructions) and Windows
  (Windows notes).
- `START_HERE.md` — mentions Windows users should read `WINDOWS_NOTES.md` and that
  WSL2 is the recommended route unless native Windows is directly verified.
- `STACK_STATUS.md` — added the Move 53 status note (after the check passed).

## Not changed

- No component code behaviour changed.
- No schemas changed.
- No architecture changed; no new features (no GUI, app, networking, signing,
  anchoring, cloud, LLM integration, autonomy, or new Sentinel actions).
- Step 54 (Clean GitHub Repository Structure) was not started.

## Honesty note

Windows native support is **not** claimed. The verified environments remain
Termux (Android) and Linux-style POSIX shells. Windows is documented as
inspect-safe and runnable via WSL2; a native run is described as untested.

## Validation

- Existing validation still passes: `sh tools/validate_handoff.sh` →
  `HANDOFF_VALIDATION: PASS`.
- Move 52 Linux check still passes: `sh tools/check_linux_desktop_instructions.sh`
  → `LINUX_DESKTOP_INSTRUCTIONS_CHECK: PASS`.
- New Windows notes check passes: `sh tools/check_windows_notes.sh` →
  `WINDOWS_NOTES_CHECK: PASS`.

## Status

Roadmap complete **through Move 53**. Moves 54–70 remain future work. This is a
Local v1 Candidate, not a final Local v1 Release. The 70-step roadmap is not
complete.
