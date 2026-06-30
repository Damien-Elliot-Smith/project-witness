# Project Witness — Local v1 Candidate v0.1

## Move

This package is **Move 50 — Freeze Local v1 Candidate**.

## Status

This is a **Local v1 Candidate**.

It is not the final Local v1 Release.

Project Witness Part One is complete through Move 50. Moves 51–70 remain future work.

## Why this package is download-safe

Earlier packages that recursively embedded prior stack zips grew beyond 300 MB and failed to download in the app.

This candidate package includes the current runnable local demo pack and the current Move 49 download-safe package. It records the larger prior stack artifacts by checksum in `EXTERNAL_ARTIFACTS_INDEX.md` and `LOCAL_V1_CANDIDATE_REGISTRY.json` rather than nesting them again.

## Verify this package

Run:

```bash
python tools/verify_local_v1_candidate.py
```

Expected:

```text
LOCAL_V1_CANDIDATE_VERIFIED
verify_ok = true
```
