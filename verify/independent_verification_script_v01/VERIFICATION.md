# Verification

## Verify the independent verifier against the included target

```bash
python tools/independent_verify_project_witness.py artifacts/full_stack_component_version_freeze_v01.zip
```

Expected:

```text
PROJECT_WITNESS_INDEPENDENT_VERIFICATION_PASSED
verify_ok = true
```

## Verify this package

```bash
python tools/verify_independent_verification_script_package.py
```

Expected:

```text
INDEPENDENT_VERIFICATION_SCRIPT_PACKAGE_VERIFIED
verify_ok = true
```
