# Release Gate — Local v1 Candidate v0.1

## PASS criteria

| Gate | Criterion | Required status |
|---|---|---|
| RG-001 | Candidate freeze record exists | PASS |
| RG-002 | Runnable local demo pack included | PASS |
| RG-003 | Move 49 download-safe package included | PASS |
| RG-004 | Roadmap reference included | PASS |
| RG-005 | Candidate registry exists | PASS |
| RG-006 | Included artifact hashes match registry | PASS |
| RG-007 | Package CHECKSUMS.txt validates | PASS |
| RG-008 | Runnable local demo zip integrity passes | PASS |
| RG-009 | Embedded frozen baseline exists | PASS |
| RG-010 | Embedded frozen baseline SHA256 matches registry | PASS |
| RG-011 | Embedded baseline checksum records validate | PASS |
| RG-012 | External artifact index exists | PASS |
| RG-013 | Claims and limits are explicit | PASS |
| RG-014 | Package verifier passes | PASS |
| RG-015 | ResourceWarning sweep passes | PASS |
| RG-016 | Move 51 is not performed | PASS |
| RG-017 | Final Local v1 Release is not claimed | PASS |

## FAIL criteria

The candidate fails if:

- any included artifact hash mismatches
- package checksum validation fails
- runnable local demo zip integrity fails
- embedded baseline is missing
- embedded baseline hash mismatches
- final release is claimed
- truth/provenance limits are overclaimed
- Move 51 is performed
