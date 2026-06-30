# Histor-lite ODIN Importer v0.1

A deterministic importer that takes a **verified ODIN Claim Reasoner v0.1 output**
and records it as a Histor-lite-style **reasoning case record**. It is Move 17 of
Project Witness.

It reads ODIN's reasoning output, preserves ODIN's reasoning status exactly, and
writes a small case folder (summary + verbatim copies of the report, proof trace,
and claims + replay report + checksums) that can be verified later.

> Histor-lite ODIN Importer v0.1 records verified ODIN structural reasoning metadata
> only. It does not prove that any claim is true.

## What it is

```
ODIN reasoning output
  -> verify the run with frozen ODIN
  -> read reasoning_report.json, proof_trace.json, claims_canonical.json
  -> require reasoning_status in {CONSISTENT, CONTRADICTION_DETECTED}
  -> copy the three ODIN files verbatim into the case
  -> write odin_case_summary.json
  -> write odin_replay_report.txt
  -> write odin_case_checksums.txt
  -> verify the imported reasoning case
```

## Which frozen component it reads from

The frozen **ODIN Claim Reasoner v0.1**. The importer verifies the run with ODIN
(via subprocess at runtime) before reading the output, and never modifies it.

## What it imports

Structural reasoning metadata only: the case_id, ODIN reasoning status
(`CONSISTENT` or `CONTRADICTION_DETECTED`), claim count, contradiction count, proof
step count, and the SHA-256 hashes of the three ODIN output files. The three ODIN
files are copied **verbatim** (byte-for-byte) into the case, never rewritten.

A structural **contradiction is a valid reasoning outcome**, not a failed import:
both `CONSISTENT` and `CONTRADICTION_DETECTED` import successfully as
`IMPORTED_VERIFIED_ODIN`. Only `INVALID_INPUT` is refused.

## What it does NOT import

- It does **not** prove any claim is true.
- It does **not** interpret evidence contents.
- It does **not** import Aletheia evidence metadata.
- It does **not** import Sentinel action data.
- It is **not connected to Coordinator or Companion yet**.
- One ODIN reasoning output only; no signing, no external anchoring.

## How to run `import-reasoning`

```bash
python3 histor_odin.py import-reasoning \
  --odin-root /path/to/odin_claim_reasoner_v01 \
  --run /path/to/odin_output \
  --out /path/to/odin_case
```

The importer checks the ODIN root and run exist; runs frozen ODIN verify and refuses
if it fails; reads the three ODIN files; requires an importable reasoning status
(refusing `INVALID_INPUT`); refuses a non-empty output directory; then copies the
three files verbatim and writes the summary, replay report, and checksums — exactly
six files.

## How to run `verify-case`

```bash
python3 histor_odin.py verify-case --case /path/to/odin_case
```

Verification checks: required files exist; no unknown extra files; the summary and
the three copies are valid **and canonical**; the checksums file parses strictly
(lowercase digests only, uppercase rejected) and matches recomputed hashes; case_id
matches across the summary and all three copies; source_reasoning_status matches the
report copy; claim_count matches the report copy and the claims copy length;
contradiction_count matches the report copy; proof_step_count matches the trace
copy; `import_status = IMPORTED_VERIFIED_ODIN`; the source status is `CONSISTENT` or
`CONTRADICTION_DETECTED` (refusing `INVALID_INPUT`); and no truth-like claim appears
in the summary or replay report.

## How to run selfcheck

```bash
python3 histor_odin.py selfcheck
```

In-process invariant gates only (uses an in-process fake verifier); it never
launches the unit suite or any subprocess.

## How to run the release commands

See [RELEASE_COMMANDS.md](RELEASE_COMMANDS.md). The freeze gate is the explicit list
of individual commands plus the static `verify_release_manifest.py`. The default
unit suite uses an in-process fake ODIN verifier, so the gate spawns no subprocesses.
There is no wrapper orchestrator in the gate.

## Honesty boundary

The importer records structural reasoning metadata only. A recorded
`CONTRADICTION_DETECTED` means ODIN found a structural contradiction among the
claims — it does not mean any claim is false, just as `CONSISTENT` does not mean any
claim is true. Because nothing is signed or anchored, a self-consistent whole-folder
fabrication remains possible — this is tamper-evidence within the case record, not
tamper-proofness, and not production evidence custody. It does not prove that any
claim is true.
