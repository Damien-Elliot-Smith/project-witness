# Usage

## Basic verification

From the package root:

```bash
python tools/independent_verify_project_witness.py artifacts/full_stack_component_version_freeze_v01.zip
```

Expected output:

```text
PROJECT_WITNESS_INDEPENDENT_VERIFICATION_PASSED
verify_ok = true
```

## JSON summary

```bash
python tools/independent_verify_project_witness.py artifacts/full_stack_component_version_freeze_v01.zip --json
```

## Verify this Move 46 package

```bash
python tools/verify_independent_verification_script_package.py
```

Expected output:

```text
INDEPENDENT_VERIFICATION_SCRIPT_PACKAGE_VERIFIED
verify_ok = true
```

## Failure meaning

If the script prints `INDEPENDENT_VERIFY_FAIL`, do not treat the stack as verified. Investigate the exact failure message.
