# Bundle format — Aletheia Evidence Bundle v0.1

A successful `bundle-file` writes an **evidence bundle directory**:

```
evidence_manifest.json     deterministic canonical JSON (fields below)
evidence_checksums.txt      sha256 lines for the manifest and the bundled file
evidence/
  evidence_001.bin          a byte-for-byte copy of the source file
```

The output directory must be empty or absent before a build; a non-empty directory
is refused (`OUTPUT_DIR_NOT_EMPTY`). The bundled evidence file is always named
`evidence_001.bin`; the original filename is preserved only in the manifest.

## evidence_manifest.json

Deterministic canonical JSON: keys sorted, compact separators, UTF-8, no
NaN/Infinity, single trailing newline. Exact field set:

| Field | Meaning |
|-------|---------|
| `aletheia_evidence_bundle_version` | `"0.1.0"`. |
| `case_id` | Validated case identifier. |
| `evidence_id` | Validated evidence identifier. |
| `source_file_name` | Basename of the original source file (metadata only). |
| `source_file_size_bytes` | Size of the source file in bytes. |
| `source_file_sha256` | SHA-256 of the source file. |
| `bundled_file_path` | Always `evidence/evidence_001.bin`. |
| `bundled_file_sha256` | SHA-256 of the bundled copy (must equal source at build). |
| `bundle_status` | `"BUNDLED"`. |
| `evidence_status` | `"VERIFIED_PRESENT"` — an integrity verdict, not truth. |
| `created_at_utc` | UTC timestamp `YYYY-MM-DDTHH:MM:SSZ`. |
| `known_limitations` | Disclosed limits, including that contents are not proven true. |

## evidence_checksums.txt

Exactly two lines, `sha256sum`-style (`<digest>  <path>`), manifest first:

```
<evidence_manifest_sha256>  evidence_manifest.json
<bundled_file_sha256>  evidence/evidence_001.bin
```

Strict on parse: required keys appear exactly once; duplicate keys fail; missing
keys fail; unknown keys fail; malformed digests fail.

## evidence_status values

`VERIFIED_PRESENT` (integrity pass), `FAILED_MISSING_FILE`,
`FAILED_HASH_MISMATCH`, `FAILED_MANIFEST_INVALID`, `FAILED_CHECKSUMS_INVALID`,
`FAILED_NON_CANONICAL_MANIFEST`.

## verify

`aletheia.py verify --bundle <dir>` performs checks 1–14 (required files; no
unknown files; canonical valid manifest; strict checksums; recomputed manifest and
evidence hashes match the checksums file; manifest `bundled_file_sha256` matches
the actual file; manifest `source_file_sha256` == `bundled_file_sha256`). It exits
0 and prints `Aletheia evidence bundle verified` on success, or exits non-zero with
a `FAILED_*` status on any failure.
