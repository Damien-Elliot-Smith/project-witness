# Test Results — Independent Verification Script v0.1

## Target

```text
full_stack_component_version_freeze_v01.zip
SHA256: e97e4d6dbd40254439506dea43b02e5cd87623d45ecbd6df153e6cd9568e1333
```

## Positive verification

Command:

```bash
python tools/independent_verify_project_witness.py artifacts/full_stack_component_version_freeze_v01.zip
```

Return code: `0`

Output:

```text
PROJECT_WITNESS_INDEPENDENT_VERIFICATION_PASSED
verify_ok = true
```

## JSON summary run

Return code: `0`

Output begins with:

```text
PROJECT_WITNESS_INDEPENDENT_VERIFICATION_PASSED
verify_ok = true
{
  "artifact_count": 7,
  "baseline_component_zip_count": 36,
  "baseline_sha256": "0f1d56ac199a788168e24540c9f347010a3f01e8ea17732d4bdbc756040445bc",
  "baseline_sha_record_count": 36,
  "baseline_sha_records_passed": 36,
  "package_root": "full_stack_component_version_freeze_v01/",
  "target": "artifacts/full_stack_component_version_freeze_v01.zip",
  "target_sha256": "e97e4d6dbd40254439506dea43b02e5cd87623d45ecbd6df153e6cd9568e1333"
}
```

## ResourceWarning sweep

Command:

```bash
python -W error::ResourceWarning tools/independent_verify_project_witness.py artifacts/full_stack_component_version_freeze_v01.zip
```

Return code: `0`

Output:

```text
PROJECT_WITNESS_INDEPENDENT_VERIFICATION_PASSED
verify_ok = true
```

## Scope boundary

PASS.

No frozen artifacts were modified.

Move 47 was not performed.

Local v1 Candidate was not frozen.
