# Verify Local v1 Candidate

## Package verifier

Run from this package root:

```bash
python tools/verify_local_v1_candidate.py
```

Expected:

```text
LOCAL_V1_CANDIDATE_VERIFIED
verify_ok = true
```

## What the package verifier checks

The verifier checks:

- required candidate files exist
- `LOCAL_V1_CANDIDATE_REGISTRY.json` parses
- included artifact SHA256 hashes match the registry
- package `CHECKSUMS.txt` hashes match actual files
- runnable local demo zip integrity passes
- runnable local demo has no duplicate entries
- runnable local demo contains the embedded frozen baseline
- embedded frozen baseline SHA256 matches registry
- embedded frozen baseline zip integrity passes
- embedded baseline `.sha256` records validate against included component zips
- forbidden final-release/status claims are absent

## Verification limits

Passing verification means the candidate package is internally consistent.

It does not prove truth, external reality, source trust, production readiness, signing, or anchoring.
