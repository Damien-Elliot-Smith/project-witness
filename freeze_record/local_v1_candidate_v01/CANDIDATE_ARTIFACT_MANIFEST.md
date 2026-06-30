# Candidate Artifact Manifest

## Included artifacts

| Artifact | SHA256 | Size bytes | Status |
|---|---|---:|---|
| `Project_Witness_Local_Demo_Pack_v01_1_blue_team_repair.zip` | `f9122b92b03c4c1d6959a080f78e758b7f9dc6509c2c6069b2303d47f31c4707` | 12640234 | Included |
| `move49_clean_error_messages_DOWNLOAD_SAFE.zip` | `dd414897269fa2df8675747a7bcc18524d4784ad3043ad4bb0fd604a824aea62` | 21507 | Included |
| `project_witness_70_step_roadmap_clean.pdf` | `fb1c13a021f82126d0bc8b709ffaaa0ffcf89e6a29cb6a4f16caa0baafbfd27b` | 5009 | Included |

## External artifacts recorded but not embedded

| Artifact | SHA256 | Size bytes | Status |
|---|---|---:|---|
| `full_stack_component_version_freeze_v01.zip` | `e97e4d6dbd40254439506dea43b02e5cd87623d45ecbd6df153e6cd9568e1333` | 50421064 | External reference, not embedded to keep package download-safe |
| `independent_verification_script_v01.zip` | `d470a5863ae550a732e00ef3b7b34ffc15c88978ebe11d0a47afd328370e2c30` | 50447770 | External reference, not embedded to keep package download-safe |
| `example_reviewer_walkthrough_v01.zip` | `68a9da30e20ffca31f76ef530eaf6e514c88866392266036cc928b82c49f49f0` | 100913144 | External reference, not embedded to keep package download-safe |
| `human_readable_reports_v01.zip` | `6892e84750fd530386657680c2cc1f213cfec9f8020e540f11c00ca1be75739d` | 100949167 | External reference, not embedded to keep package download-safe |
| `clean_error_messages_v01.zip` | `0a361d19d2d3a4e102999659e3ff6d8463e3434bbd41f15294e394b94f94a7de` | 302771035 | External reference, not embedded to keep package download-safe |

## Why some artifacts are external

This package avoids recursively nesting large previous stack zips because that caused download failures.

The larger artifacts are still frozen by exact SHA256 in the registry.
