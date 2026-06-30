# Negative Test Results — Independent Verification Script v0.1

The negative test copies were created outside the final package and are not included.

## Negative test 1 — package CHECKSUMS mismatch

Action:

```text
Tampered README.md inside a temporary copy of full_stack_component_version_freeze_v01.zip without updating CHECKSUMS.txt.
```

Return code: `1`

Output:

```text
INDEPENDENT_VERIFY_FAIL: CHECKSUMS.txt hash mismatch for README.md
```

Expected failure: checksum mismatch.

## Negative test 2 — artifact hash mismatch

Action:

```text
Tampered artifacts/full_stack_red_team_round_2_v01.zip inside a temporary copy of full_stack_component_version_freeze_v01.zip without updating the registry.
```

Return code: `1`

Output:

```text
INDEPENDENT_VERIFY_FAIL: CHECKSUMS.txt hash mismatch for artifacts/full_stack_red_team_round_2_v01.zip
```

Expected failure: checksum or artifact hash mismatch.


expected failure: both negative tests must fail.
