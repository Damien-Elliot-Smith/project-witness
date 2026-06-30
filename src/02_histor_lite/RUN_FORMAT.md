# Case output format — Histor-lite v0.1.2

A successful `import-sentinel` writes a **case folder** containing exactly three
files. All paths below are relative to the `--out` directory.

```
case_summary.json            deterministic canonical JSON (see below)
sentinel_replay_report.txt   the frozen Sentinel verifier's full replay report
checksums.txt                SHA-256 of the source run + the two files above
```

## case_summary.json

Deterministic canonical JSON: keys sorted, compact separators
(`,` and `:`), UTF-8, no NaN/Infinity, single trailing newline. The same inputs
always produce byte-identical output, so the summary's own SHA-256 is
reproducible.

Fields:

| Field | Meaning |
|-------|---------|
| `histor_lite_version` | Histor-lite version that produced the case (`"0.1.0"`). |
| `case_id` | `"case_" + source_run_sha256[:16]` — deterministic per run. |
| `source_component` | `"sentinel_core"`. |
| `source_component_version` | `"0.2.2"`. |
| `source_run_path` | Absolute path of the imported Sentinel run file. |
| `source_run_sha256` | SHA-256 of the source run file's bytes. |
| `sentinel_replay_verdict` | The frozen verifier's verdict, **preserved exactly**. |
| `sentinel_replay_ok` | `true` for both accepted verdicts. |
| `import_status` | `IMPORTED` or `IMPORTED_WITH_ENVIRONMENTAL_EXCEPTIONS`. |
| `verified_at_utc` | ISO-8601 `Z` timestamp of the import. |
| `known_limitations` | Sentinel's disclosed limits, carried verbatim. |

Example (a `PASS_STRICT` import):

```json
{"case_id":"case_e8c630b1b29e8cba","histor_lite_version":"0.1.0","import_status":"IMPORTED","known_limitations":["Sentinel hashes are unkeyed; whole-file fabrication requires signing or anchoring to detect.","Environmental ERROR receipts may be structurally verified rather than strictly reproduced."],"sentinel_replay_ok":true,"sentinel_replay_verdict":"PASS_STRICT","source_component":"sentinel_core","source_component_version":"0.2.2","source_run_path":"/abs/run.json","source_run_sha256":"e8c630...","verified_at_utc":"2026-06-13T18:30:35Z"}
```

For a `PASS_WITH_ENVIRONMENTAL_EXCEPTIONS` run the `sentinel_replay_verdict` is
`"PASS_WITH_ENVIRONMENTAL_EXCEPTIONS"` and `import_status` is
`"IMPORTED_WITH_ENVIRONMENTAL_EXCEPTIONS"`. The verdict is never relabelled as
strict.

## sentinel_replay_report.txt

The full text report returned by the frozen Sentinel verifier, written verbatim
(with a trailing newline). Its final lines carry the Sentinel `REPLAY VERDICT:`
line and summary.

## checksums.txt

Three `key  hash  label` lines (whitespace-separated):

```
source_run_sha256              <hash>  <source run filename>
case_summary_sha256            <hash>  case_summary.json
sentinel_replay_report_sha256  <hash>  sentinel_replay_report.txt
```

`checksums.txt` is not self-referential. Each recognised key must appear
**exactly once**: duplicate keys are rejected at parse time so a tampered line
cannot hide behind a correct duplicate (no "last line wins"). `verify-case`
recomputes the SHA-256 of `case_summary.json` and `sentinel_replay_report.txt`,
compares them against this file, re-checks that `case_summary.json` is still in
canonical form, and verifies that the recorded `source_run_sha256` is a
well-formed digest that matches the `source_run_sha256` inside
`case_summary.json`. The `source_run_sha256` line is
provenance metadata for a file that is not copied into the case folder; it is
therefore consistency-checked against the summary rather than rehashed.

## Integrity scope

`verify-case` proves the case folder is internally consistent **as written**. It
is unkeyed (see KNOWN_LIMITATIONS H1/H2): it detects modification of a file whose
recorded hash was not also updated, non-canonical re-serialisation of the
summary, a tampered or malformed `source_run_sha256` metadata line, and
duplicate checksum keys, but it cannot detect a fully reconstructed case folder. It does not re-run Sentinel.
