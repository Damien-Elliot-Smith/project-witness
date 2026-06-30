# Release Gate — Independent Verification Script v0.1

## PASS criteria

| Gate | Criterion | Required status |
|---|---|---|
| RG-001 | Independent verifier exists | PASS |
| RG-002 | Independent verifier uses only Python standard library | PASS |
| RG-003 | Independent verifier verifies Move 45 package externally | PASS |
| RG-004 | Independent verifier does not execute internal Project Witness verifiers | PASS |
| RG-005 | Positive verification passes | PASS |
| RG-006 | ResourceWarning sweep passes | PASS |
| RG-007 | Negative checksum/package tamper test fails as expected | PASS |
| RG-008 | Negative artifact tamper test fails as expected | PASS |
| RG-009 | Move 46 package verifier passes | PASS |
| RG-010 | Move 47 is not performed | PASS |
| RG-011 | Local v1 Candidate is not frozen | PASS |
| RG-012 | No frozen artifacts are modified | PASS |

## FAIL criteria

The package fails if:

- the verifier cannot verify the included Move 45 package
- tampered packages pass
- artifact hash mismatches are not detected
- the script depends on Project Witness runtime modules
- Move 47 is performed
- Local v1 Candidate is claimed as frozen
- truth/external-reality/source-trust claims are overclaimed
