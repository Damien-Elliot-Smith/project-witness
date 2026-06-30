# Output format — Aletheia -> ODIN Bridge v0.1

A successful `convert` writes a **bridge output directory**:

```
odin_claims.json             the generated ODIN claim set (canonical JSON)
bridge_report.json           the bridge report (canonical JSON)
aletheia_manifest_copy.json   a verbatim copy of the Aletheia manifest (canonical)
bridge_checksums.txt          sha256 of the three JSON files
```

The evidence file is intentionally **not** copied. The output directory must be
empty or absent before a run; a non-empty directory is refused
(`OUTPUT_DIR_NOT_EMPTY`).

## odin_claims.json

An ODIN Claim Reasoner v0.1-compatible claim set: `odin_claim_set_version`,
`case_id`, and exactly two claims with predicates `evidence.present` and
`evidence.integrity_verified`. Each claim has object `true`, polarity `AFFIRMED`,
and one support item referencing `aletheia_evidence_bundle`, the evidence id, and
the manifest `bundled_file_sha256`.

## bridge_report.json

Canonical JSON. Fields: `bridge_version`, `case_id`, `evidence_id`, `bridge_status`,
`aletheia_evidence_status`, `odin_claim_count`, `odin_validation_status`,
`generated_claims`, `known_limitations`.

- `bridge_status` ∈ {`CONVERTED`, `FAILED_ALETHEIA_VERIFY`,
  `FAILED_MANIFEST_INVALID`, `FAILED_STATUS_NOT_VERIFIED_PRESENT`,
  `FAILED_ODIN_VALIDATE`, `FAILED_CHECKSUMS_INVALID`}. A written output always has
  `CONVERTED`; the failure statuses are surfaced on the CLI/stderr and no successful
  output is written.
- `odin_validation_status` ∈ {`VALID`, `SKIPPED`}.

## aletheia_manifest_copy.json

A canonical copy of the source Aletheia manifest, hashed into the checksums file so
verify can confirm it has not been altered.

## bridge_checksums.txt

Exactly three lines, `sha256sum`-style (`<digest>  <path>`):

```
<odin_claims_sha256>  odin_claims.json
<bridge_report_sha256>  bridge_report.json
<aletheia_manifest_copy_sha256>  aletheia_manifest_copy.json
```

Strict: required keys exactly once; duplicate/missing/unknown keys fail; malformed
or uppercase digests fail; hash mismatch fails.

## verify

`bridge.py verify --run <dir>` performs checks 1–18 (required files; no unknown
files; canonical claims/report/manifest-copy; strict checksums; recomputed hashes;
report case_id == claims case_id; report evidence_id == manifest evidence_id; only
allowed predicates; no truth-like predicate; support source_sha256 == manifest
bundled_file_sha256; report odin_claim_count == actual). Exit 0 + `Bridge output
verified` on success, or non-zero with a specific reason on failure.
