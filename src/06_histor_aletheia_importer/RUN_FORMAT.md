# Case format — Histor-lite Aletheia Importer v0.1

A successful `import-evidence` writes an **evidence case directory** containing
exactly these four files (no others):

```
evidence_case_summary.json     the case summary (canonical JSON)
aletheia_manifest_copy.json     a canonical copy of the Aletheia manifest
aletheia_replay_report.txt      a plain-text import/replay report
evidence_case_checksums.txt      sha256 of the three files above
```

The evidence file itself is **not** copied. The output directory must be empty or
absent before an import; a non-empty directory is refused (`OUTPUT_DIR_NOT_EMPTY`).

## evidence_case_summary.json

Canonical JSON. Fields: `histor_aletheia_importer_version`, `case_id`,
`evidence_id`, `import_status`, `source_component`, `source_evidence_status`,
`source_file_name`, `source_file_size_bytes`, `source_file_sha256`,
`bundled_file_sha256`, `source_bundle_manifest_sha256`, `known_limitations`.

`import_status` ∈ {`IMPORTED_VERIFIED_ALETHEIA`, `FAILED_ALETHEIA_VERIFY`,
`FAILED_STATUS_NOT_VERIFIED_PRESENT`, `FAILED_MANIFEST_INVALID`,
`FAILED_CHECKSUMS_INVALID`}. A written case always has `IMPORTED_VERIFIED_ALETHEIA`;
the failure statuses are surfaced on the CLI/stderr and no case is written.

## aletheia_manifest_copy.json

A canonical copy of the source Aletheia manifest, hashed into the checksums file so
verify can confirm it has not been altered. Its `source_bundle_manifest_sha256` in
the summary is the SHA-256 of this canonical copy.

## aletheia_replay_report.txt

Plain text. Records `import_status`, `case_id`, `evidence_id`,
`source_evidence_status`, `source_file_sha256`, `bundled_file_sha256`,
`truth_claim: none`, and the explicit sentence:

> This import verifies Aletheia evidence integrity metadata only. It does not prove
> the evidence contents are true.

## evidence_case_checksums.txt

Exactly three lines, `sha256sum`-style (`<digest>  <path>`):

```
<evidence_case_summary_sha256>  evidence_case_summary.json
<aletheia_manifest_copy_sha256>  aletheia_manifest_copy.json
<aletheia_replay_report_sha256>  aletheia_replay_report.txt
```

Strict: required keys exactly once; duplicate/missing/unknown keys fail; malformed
or uppercase digests fail; hash mismatch fails; lowercase SHA-256 only.

## verify-case

`histor_aletheia.py verify-case --case <dir>` performs checks 1–19 (required files;
no unknown files; canonical summary/manifest copy; strict checksums; recomputed
hashes; case_id and evidence_id match summary + manifest; source_evidence_status ==
VERIFIED_PRESENT; import_status == IMPORTED_VERIFIED_ALETHEIA; source and bundled
SHAs match the manifest; no truth-like claim in summary or replay report). Exit 0 +
`Evidence case verified` on success, or non-zero with a specific reason on failure.
