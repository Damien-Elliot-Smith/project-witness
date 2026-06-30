# Histor-lite v0.1.2

A narrow importer/verifier that connects the frozen **Sentinel Core v0.2.2**
milestone to the wider Project Witness stack. Given a Sentinel run file,
Histor-lite verifies it with the **frozen Sentinel verifier** and writes a
stack-level case summary.

```
Sentinel run file
  -> Histor-lite import
  -> Sentinel replay verification (frozen verifier)
  -> case summary written to disk
```

## What Histor-lite v0.1.2 is

- A **narrow importer/verifier**. It imports Sentinel Core v0.2.2
  `CREATE_DIRECTORY` runs, asks the frozen Sentinel verifier for a replay
  verdict, and writes a case folder (`case_summary.json`,
  `sentinel_replay_report.txt`, `checksums.txt`).
- The **first connection** between Sentinel and the wider stack.
- Standard library only.

## What Histor-lite v0.1.2 is NOT

- **Not full Histor.** No ledger, no chaining of cases, no multi-component
  graph.
- **It imports Sentinel runs only.** It does not import Aletheia, ODIN, Atlas, or
  Companion records.
- **It does not sign or externally anchor anything.**
- **It is not a production ledger** and provides no production security.
- It does not modify Sentinel, add Sentinel actions, or create a new Sentinel
  version. Sentinel v0.2.2 is treated as frozen.

## How to run an import

```bash
python3 histor_lite.py import-sentinel \
  --sentinel-root /path/to/extracted/sentinel_core_v022 \
  --run /path/to/sentinel_run.json \
  --out /path/to/case_output
```

This checks the Sentinel root and verifier module exist, checks the run file
exists, computes its SHA-256, runs the **frozen** Sentinel verifier, and — only
if the verdict is `PASS_STRICT` or `PASS_WITH_ENVIRONMENTAL_EXCEPTIONS` — writes
the case folder. Any other verdict (or a missing/malformed run, or a verifier
that cannot run) is refused with a non-zero exit and a clear reason.

Exit codes: `0` imported; `2` refused (`ImportRefused`, e.g. a `FAIL` /
`REPLAY_INCOMPATIBLE` verdict, a missing or malformed run, or an **inconsistent**
result where the verifier reports an accepted verdict but `ok=False`); `3` the
Sentinel verifier was unavailable or crashed.

An accepted verdict is honoured only when the verifier's own `ok` flag is `True`.
A result like `verdict=PASS_STRICT, ok=False` is internally contradictory and is
refused with reason `SENTINEL_VERDICT_INCONSISTENT` — Histor-lite never imports a
case the verifier did not actually bless.

## How to verify a case output

```bash
python3 histor_lite.py verify-case --case /path/to/case_output
```

This recomputes the SHA-256 of `case_summary.json` and
`sentinel_replay_report.txt` and compares them against `checksums.txt`; checks
that the recorded `source_run_sha256` is a well-formed digest **and matches** the
`source_run_sha256` embedded in `case_summary.json`; and checks that
`case_summary.json` is still valid canonical JSON. A mutated case summary, a
mutated replay report, or a tampered `source_run_sha256` provenance line is
detected (non-zero exit). This is an integrity check of the **case folder**; the
source run file is not copied in, so it is not rehashed — but its recorded
checksum metadata must be internally consistent. It does not re-run Sentinel.

## How to run tests

```bash
python3 -m compileall -q .
python3 -m unittest discover -s tests -v
python3 -O -m unittest discover -s tests -v
python3 selfcheck.py
python3 -O selfcheck.py
python3 -W error::ResourceWarning -m unittest discover -s tests
python3 release_check.py
sha256sum -c histor_lite_v01.sha256
```

The unit suite uses a small **stub** Sentinel verifier so it can test
Histor-lite's logic deterministically without an external Sentinel checkout.
An optional real-Sentinel integration test runs only when you point it at one:

```bash
SENTINEL_V022_ROOT=/path/to/sentinel_core_v022 \
  python3 -m unittest tests.test_import_sentinel.TestRealSentinelIntegration -v
```

## What the verdicts mean

The verdict always comes from the **frozen Sentinel verifier** and is preserved
exactly in the case summary.

| Sentinel verdict | Histor-lite `import_status` | `sentinel_replay_ok` | Imported? |
|------------------|-----------------------------|----------------------|-----------|
| `PASS_STRICT` | `IMPORTED` | `true` | yes |
| `PASS_WITH_ENVIRONMENTAL_EXCEPTIONS` | `IMPORTED_WITH_ENVIRONMENTAL_EXCEPTIONS` | `true` | yes (verdict preserved exactly) |
| `FAIL` | — | — | no — refused, non-zero exit |
| `REPLAY_INCOMPATIBLE` | — | — | no — refused, non-zero exit |

An accepted verdict (`PASS_STRICT` or `PASS_WITH_ENVIRONMENTAL_EXCEPTIONS`) is
imported only if the verifier's `ok` flag is `True`; otherwise it is refused as
`SENTINEL_VERDICT_INCONSISTENT`.

A `PASS_WITH_ENVIRONMENTAL_EXCEPTIONS` import is **never** relabelled as strict.
The case summary records the exact verdict so a downstream reader knows the
Sentinel run leaned on an environmental exception (an execution/postcondition
ERROR that Sentinel structurally verified rather than strictly reproduced).

## Frozen Sentinel input

```
sentinel_core_v022.zip
  sha256: 23381adf4de437191d2ff4f87d6034d556084e1af4419f94033e8ca6ce4bca5f
```

Histor-lite trusts whatever Sentinel verifier is present at `--sentinel-root`;
verify that checksum before importing if provenance matters.
