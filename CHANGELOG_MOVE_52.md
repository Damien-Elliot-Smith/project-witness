# Changelog — Move 52 (Linux Desktop Run Instructions)

Date: 2026-06-29
Roadmap: Step 52 = Linux Desktop Run Instructions (Step 51 = Termux, Step 53 =
Windows Notes — not started).
Scope: documentation and a presence/readiness check only.

## Added

- `LINUX_DESKTOP_RUN_INSTRUCTIONS.md` — step-by-step instructions for verifying
  and running the working stack on an ordinary Linux desktop/laptop: required
  tools (`python3`, POSIX `sh`, `unzip`, `sha256sum`), offline / no-extra-packages
  note, checksum verification, extraction, the main validator, each verification
  command, the live demo, expected PASS markers, what failure means, and known
  limits.
- `tools/check_linux_desktop_instructions.sh` — checks that the instruction
  document, the required commands, and the required scripts are all present. Fails
  closed (non-zero) if anything required is missing. Optional `--full` flag also
  runs `validate_handoff.sh`. Prints `LINUX_DESKTOP_INSTRUCTIONS_CHECK: PASS` only
  when everything required is present.

## Updated (minimal)

- `REVIEWER_QUICKSTART.md` — points Linux users to the new instructions.
- `START_HERE.md` — mentions the Linux desktop instructions.
- `STACK_STATUS.md` — added the Move 52 status note (after the check passed).

## Not changed

- No component code behaviour changed.
- No schemas changed.
- No architecture changes; no new features (no GUI, app, networking, signing,
  anchoring, cloud, LLM integration, autonomy, or new Sentinel actions).
- Did not advance to Step 53 (Windows Notes).

## Validation

- Existing validation still passes: `sh tools/validate_handoff.sh` →
  `HANDOFF_VALIDATION: PASS`.
- New check passes: `sh tools/check_linux_desktop_instructions.sh` →
  `LINUX_DESKTOP_INSTRUCTIONS_CHECK: PASS`.

## Status

Roadmap complete **through Move 52**. Moves 53–70 remain future work. This is a
Local v1 Candidate, not a final Local v1 Release. The 70-step roadmap is not
complete.
