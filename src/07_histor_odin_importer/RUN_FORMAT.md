# Case format — Histor-lite ODIN Importer v0.1

A successful `import-reasoning` writes a **reasoning case directory** containing
exactly these six files (no others):

```
odin_case_summary.json            the case summary (canonical JSON)
odin_reasoning_report_copy.json    verbatim copy of ODIN reasoning_report.json
odin_proof_trace_copy.json         verbatim copy of ODIN proof_trace.json
odin_claims_copy.json              verbatim copy of ODIN claims_canonical.json
odin_replay_report.txt             a plain-text import/replay report
odin_case_checksums.txt             sha256 of the five files above
```

The three ODIN copies are **byte-for-byte verbatim** — the importer does not alter
the report, rewrite the proof trace, or modify the claims file. (ODIN output is
already canonical, so the verbatim copies are also canonical for verify's canonical
check.) The output directory must be empty or absent before an import; a non-empty
directory is refused (`OUTPUT_DIR_NOT_EMPTY`).

## odin_case_summary.json

Canonical JSON. Fields: `histor_odin_importer_version`, `case_id`, `import_status`,
`source_component`, `source_reasoning_status`, `claim_count`,
`contradiction_count`, `proof_step_count`, `source_claims_sha256`,
`source_reasoning_report_sha256`, `source_proof_trace_sha256`, `known_limitations`.

`import_status` ∈ {`IMPORTED_VERIFIED_ODIN`, `FAILED_ODIN_VERIFY`,
`FAILED_REASONING_STATUS_INVALID`, `FAILED_REPORT_INVALID`,
`FAILED_PROOF_TRACE_INVALID`, `FAILED_CHECKSUMS_INVALID`}. A written case always has
`IMPORTED_VERIFIED_ODIN`; the failure statuses are surfaced on the CLI/stderr and no
case is written.

`source_reasoning_status` ∈ {`CONSISTENT`, `CONTRADICTION_DETECTED`}. `INVALID_INPUT`
is never imported as a successful case.

## odin_replay_report.txt

Plain text. Records `import_status`, `case_id`, `source_reasoning_status`,
`claim_count`, `contradiction_count`, `proof_step_count`, `truth_claim: none`, and
the explicit sentence:

> This import records ODIN structural reasoning metadata only. It does not prove
> that any claim is true.

## odin_case_checksums.txt

Exactly five lines, `sha256sum`-style (`<digest>  <path>`):

```
<odin_case_summary_sha256>  odin_case_summary.json
<odin_reasoning_report_copy_sha256>  odin_reasoning_report_copy.json
<odin_proof_trace_copy_sha256>  odin_proof_trace_copy.json
<odin_claims_copy_sha256>  odin_claims_copy.json
<odin_replay_report_sha256>  odin_replay_report.txt
```

Strict: required keys exactly once; duplicate/missing/unknown keys fail; malformed
or uppercase digests fail; hash mismatch fails; lowercase SHA-256 only.

## verify-case

`histor_odin.py verify-case --case <dir>` performs checks 1–24 (required files; no
unknown files; canonical summary + three copies; strict checksums; recomputed
hashes; case_id matches across summary and all three copies; source_reasoning_status
matches the report copy; claim_count matches the report copy and claims copy length;
contradiction_count matches the report copy; proof_step_count matches the trace
copy; import_status == IMPORTED_VERIFIED_ODIN; status is CONSISTENT or
CONTRADICTION_DETECTED and not INVALID_INPUT; no truth-like claim in summary or
replay report). Exit 0 + `ODIN reasoning case verified` on success, or non-zero with
a specific reason on failure.
