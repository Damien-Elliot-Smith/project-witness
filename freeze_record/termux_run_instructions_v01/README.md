# Termux Run Instructions v0.1

Move 51 artifact. Termux-specific run instructions for the Project Witness
Local v1 Candidate stack.

## Contents

- `TERMUX_RUN_INSTRUCTIONS.md` — step-by-step instructions
- `RELEASE_GATE.md` — pass/fail criteria for this package
- `CHECKSUMS.txt` — SHA256 of all package files
- `tools/verify_termux_run_instructions.py` — package verifier

## Verify this package

```bash
python3 tools/verify_termux_run_instructions.py
```

Expected:

```text
TERMUX_RUN_INSTRUCTIONS_VERIFIED
verify_ok = true
```

## Scope

This package contains instructions only.
No frozen artifact was modified.
Move 52 (Linux Desktop Run Instructions) is not performed here.
Final Local v1 Release is not claimed.
