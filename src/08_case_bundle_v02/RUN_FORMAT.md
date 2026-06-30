# RUN_FORMAT — Case Bundle v0.2

## Bundle folder

A built bundle contains exactly these top-level entries (no others):

```
case_manifest.json
bundle_checksums.txt
sentinel_case/
aletheia_case/
odin_case/
```

### sentinel_case/  (real Histor-lite v0.1.2 names, preserved exactly)
- `case_summary.json`
- `sentinel_replay_report.txt`
- `checksums.txt`            ← 3-token format: `<key>  <digest>  <name>`,
                               and includes a `source_run_sha256` line for the
                               source run file (outside the case folder).

### aletheia_case/  (Histor-lite Aletheia Importer v0.1)
- `evidence_case_summary.json`
- `aletheia_manifest_copy.json`
- `aletheia_replay_report.txt`
- `evidence_case_checksums.txt`   ← 2-token format: `<digest>  <name>`

### odin_case/  (Histor-lite ODIN Importer v0.1)
- `odin_case_summary.json`
- `odin_reasoning_report_copy.json`
- `odin_proof_trace_copy.json`
- `odin_claims_copy.json`
- `odin_replay_report.txt`
- `odin_case_checksums.txt`        ← 2-token format: `<digest>  <name>`

All subcase files are copied **byte-for-byte** from the input case folders.

## case_manifest.json

Canonical JSON (UTF-8, sorted keys, `(",",":")` separators, no NaN, trailing
newline). Fields:

```
case_bundle_version    "0.2.0"
case_id                shared id across all three records
bundle_status          "BUNDLED_VERIFIED_CASE"
included_records       ["sentinel_case","aletheia_case","odin_case"]
sentinel               {source_component, case_status, action_status}
aletheia               {source_component, import_status, source_evidence_status}
odin                   {source_component, import_status, source_reasoning_status,
                        claim_count, contradiction_count}
known_limitations      [...]
```

Allowed `bundle_status` values: `BUNDLED_VERIFIED_CASE`,
`FAILED_SENTINEL_CASE_VERIFY`, `FAILED_ALETHEIA_CASE_VERIFY`,
`FAILED_ODIN_CASE_VERIFY`, `FAILED_CASE_ID_MISMATCH`, `FAILED_CHECKSUMS_INVALID`.

`odin.source_reasoning_status` ∈ {`CONSISTENT`, `CONTRADICTION_DETECTED`}.
`INVALID_INPUT` is never packageable.

## bundle_checksums.txt

Exactly 14 lines, each `<sha256>  <relative-path>` (two spaces), lowercase digests
only. Keys, in canonical order:

```
case_manifest.json
sentinel_case/case_summary.json
sentinel_case/sentinel_replay_report.txt
sentinel_case/checksums.txt
aletheia_case/evidence_case_summary.json
aletheia_case/aletheia_manifest_copy.json
aletheia_case/aletheia_replay_report.txt
aletheia_case/evidence_case_checksums.txt
odin_case/odin_case_summary.json
odin_case/odin_reasoning_report_copy.json
odin_case/odin_proof_trace_copy.json
odin_case/odin_claims_copy.json
odin_case/odin_replay_report.txt
odin_case/odin_case_checksums.txt
```

Rules: required keys exactly once; duplicate / missing / unknown keys fail;
malformed or uppercase digests fail; hash mismatch fails.

## verify (25 rules, summarised)

Required top-level files and folders exist; no unknown top-level entries; required
subcase files exist; no unknown subcase files; manifest loads and is canonical;
bundle checksums parse strictly (uppercase rejected); all bundle-level hashes
recomputed; each subcase's **internal** checksums re-verified in its own format;
all three subcase `case_id`s match `manifest.case_id`;
`bundle_status == BUNDLED_VERIFIED_CASE`; Aletheia status is `VERIFIED_PRESENT`;
ODIN status is `CONSISTENT` or `CONTRADICTION_DETECTED`; ODIN `INVALID_INPUT`
refused; no truth-like claim in the manifest; no truth-like claim in any replay
report. Success only if every check passes.
