# Verification

## Command

Run from this package root:

```bash
python tools/verify_local_v1_candidate.py
```

Expected:

```text
LOCAL_V1_CANDIDATE_VERIFIED
verify_ok = true
```

## ResourceWarning sweep

```bash
python -W error::ResourceWarning tools/verify_local_v1_candidate.py
```

Expected:

```text
LOCAL_V1_CANDIDATE_VERIFIED
verify_ok = true
```
