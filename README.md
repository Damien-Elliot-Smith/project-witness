# Project Witness

Project Witness is a local, standard-library-only verification/provenance working stack.

This repository snapshot is the **Working Stack v04 / Move 53** package. It is complete through **Move 53** of the clean 70-step roadmap:

- Move 51: Termux Run Instructions
- Move 52: Linux Desktop Run Instructions
- Move 53: Windows Notes

Status: **Local v1 Candidate**. This is **not** the final Local v1 Release, and the 70-step roadmap is not complete.

## What this is

A runnable local working stack for review, testing, and breakage attempts. The current package includes component tests, handoff validation, independent verification, Local v1 candidate verification, and end-to-end demonstration. All components use Python standard library only — no external dependencies.

## What this is not

This does not prove external truth. It does not authenticate real-world identity. It does not sign or externally anchor outputs. It is not production-ready. It is not a hosted service, cloud product, or final release. See `HANDOFF_NOTES.md` and `master_known_limitations_v01` (in the archive) for full boundary conditions.

## Start here

Read:

1. `START_HERE.md`
2. `REVIEWER_QUICKSTART.md`
3. `STACK_STATUS.md`
4. `MOVE_INDEX.md`
5. `HANDOFF_NOTES.md`

Main validation command from the repository root:

```sh
sh tools/validate_handoff.sh
```

Expected final marker:

```text
HANDOFF_VALIDATION: PASS
```

Linux users should also read `LINUX_DESKTOP_RUN_INSTRUCTIONS.md`.

Windows users should read `WINDOWS_NOTES.md`. Native Windows support is not claimed; WSL2 is the recommended route unless native Windows is directly tested later.

## Licence

This project is licensed under the **Apache License 2.0**. See the `LICENSE` file for details.

Apache 2.0 provides:
- Permissive use and redistribution rights
- Explicit patent grant protection
- Clear attribution and contribution terms

## Current roadmap status

Complete through Move 53. Moves 54-70 remain future work.
