# Test Results — Local v1 Candidate v0.1

## Candidate package verifier

Command:

```bash
python tools/verify_local_v1_candidate.py
```

Output:

```text
LOCAL_V1_CANDIDATE_VERIFIED
verify_ok = true
```

Return code: `0`

## ResourceWarning sweep

Command:

```bash
python -W error::ResourceWarning tools/verify_local_v1_candidate.py
```

Output:

```text
LOCAL_V1_CANDIDATE_VERIFIED
verify_ok = true
```

Return code: `0`

## Runnable local demo inspection

```text
Zip integrity: PASS
Duplicate entries: 0
START_HERE README present: True
Local demo verifier present: True
Embedded baseline SHA256: 0f1d56ac199a788168e24540c9f347010a3f01e8ea17732d4bdbc756040445bc
Embedded baseline component zips: 36
Embedded baseline checksum records: 36
Embedded baseline checksum validation: PASS
```

## Included artifacts

```text
Project_Witness_Local_Demo_Pack_v01_1_blue_team_repair.zip  f9122b92b03c4c1d6959a080f78e758b7f9dc6509c2c6069b2303d47f31c4707
move49_clean_error_messages_DOWNLOAD_SAFE.zip  dd414897269fa2df8675747a7bcc18524d4784ad3043ad4bb0fd604a824aea62
project_witness_70_step_roadmap_clean.pdf  fb1c13a021f82126d0bc8b709ffaaa0ffcf89e6a29cb6a4f16caa0baafbfd27b
```

## Scope boundary

PASS.

No frozen artifacts were modified.

Move 51 was not performed.

Final Local v1 Release was not frozen.
