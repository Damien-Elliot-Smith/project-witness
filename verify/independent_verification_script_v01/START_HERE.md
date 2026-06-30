# Start Here — Move 46

To verify the included Move 45 package, run:

```bash
python tools/independent_verify_project_witness.py artifacts/full_stack_component_version_freeze_v01.zip
```

Expected output:

```text
PROJECT_WITNESS_INDEPENDENT_VERIFICATION_PASSED
verify_ok = true
```

To verify this Move 46 package itself, run:

```bash
python tools/verify_independent_verification_script_package.py
```

Expected output:

```text
INDEPENDENT_VERIFICATION_SCRIPT_PACKAGE_VERIFIED
verify_ok = true
```
