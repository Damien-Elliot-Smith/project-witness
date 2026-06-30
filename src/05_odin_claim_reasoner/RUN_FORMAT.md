# Output format — ODIN Claim Reasoner v0.1

A successful `reason` writes an **ODIN output directory**:

```
claims_canonical.json    the validated claim set, in canonical JSON
reasoning_report.json    reasoning status, per-claim rows, contradictions (canonical)
proof_trace.json         deterministic step-by-step trace (canonical)
odin_checksums.txt        sha256 of the three JSON files
```

The output directory must be empty or absent before a run; a non-empty directory is
refused (`OUTPUT_DIR_NOT_EMPTY`).

## Claim input format (canonical JSON)

```
{
  "odin_claim_set_version": "0.1.0",
  "case_id": "case_001",
  "claims": [
    {
      "claim_id": "claim_001",
      "subject": "evidence:evidence_001",
      "predicate": "evidence.integrity_verified",
      "object": true,
      "polarity": "AFFIRMED",
      "support": [
        {"support_id": "support_001", "source_component": "aletheia_evidence_bundle",
         "source_id": "evidence_001", "source_sha256": "<64 hex>"}
      ]
    }
  ]
}
```

Each claim has exactly `claim_id`, `subject`, `predicate`, `object`, `polarity`,
`support`. `polarity` ∈ {`AFFIRMED`, `DENIED`}. `object` ∈ {string, boolean,
integer, null} — no floats. `support` is a non-empty list; each item has exactly
`support_id`, `source_component`, `source_id`, `source_sha256` (64 lowercase hex).

## reasoning_report.json

Canonical JSON. Fields: `odin_reasoner_version`, `case_id`, `reasoning_status`,
`claim_count`, `contradiction_count`, `unsupported_claim_count`, `claims` (each
`claim_id` + `claim_status` + `support_status`), `contradictions` (each
`claim_ids` + `rule`), `known_limitations`.

- `reasoning_status` ∈ {`CONSISTENT`, `CONTRADICTION_DETECTED`, `INVALID_INPUT`}.
- `claim_status` ∈ {`ACCEPTED`, `CONTRADICTED`, `INVALID`}.
- `support_status` ∈ {`SUPPORTED`, `MISSING_SUPPORT`, `INVALID_SUPPORT`}.

## proof_trace.json

Canonical JSON. `proof_trace_version`, `case_id`, and `steps`. One
`CLAIM_ACCEPTED` step per claim (reason `CLAIM_SCHEMA_VALID_AND_SUPPORT_PRESENT`),
then one `CONTRADICTION_DETECTED` step per contradiction (with both `claim_ids` and
the exact `rule`). Step ids are sequential (`step_001`, ...).

## odin_checksums.txt

Exactly three lines, `sha256sum`-style (`<digest>  <path>`):

```
<claims_canonical_sha256>  claims_canonical.json
<reasoning_report_sha256>  reasoning_report.json
<proof_trace_sha256>  proof_trace.json
```

Strict: required keys exactly once; duplicate/missing/unknown keys fail; malformed
digests fail; hash mismatch fails.

## verify

`odin.py verify --run <dir>` performs checks 1–13 (required files; no unknown
files; canonical claims/report/trace; strict checksums; recomputed hashes match;
report status/count match an independent recomputation from the claims; proof trace
references only valid claim IDs). Exit 0 + `ODIN output verified` on success, or
non-zero with a specific reason on any failure.
