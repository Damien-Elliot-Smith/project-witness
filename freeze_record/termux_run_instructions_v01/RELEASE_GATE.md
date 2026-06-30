# Release Gate — Termux Run Instructions v0.1

## PASS criteria

| Gate | Criterion | Status |
|---|---|---|
| RG-001 | TERMUX_RUN_INSTRUCTIONS.md present | PASS |
| RG-002 | README.md present | PASS |
| RG-003 | CHECKSUMS.txt present and validates | PASS |
| RG-004 | Package verifier present | PASS |
| RG-005 | Package verifier passes | PASS |
| RG-006 | Handoff zip SHA256 stated correctly in instructions | PASS |
| RG-007 | No forbidden claims present | PASS |
| RG-008 | No frozen artifact modified | PASS |
| RG-009 | Move 52 not performed | PASS |
| RG-010 | Final Local v1 Release not claimed | PASS |

## FAIL criteria

This package fails if:
- any required file is missing
- CHECKSUMS.txt hash mismatches
- handoff zip SHA256 is wrong or absent
- a forbidden claim is present
- Move 52 is performed
- final Local v1 Release is claimed
- any frozen artifact is modified
