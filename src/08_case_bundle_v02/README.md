# Case Bundle v0.2

Case Bundle v0.2 is a portable case-bundle exporter for **Project Witness**. It
combines three already-verified Histor-lite case records — a Sentinel **action**
case, an Aletheia **evidence** case, and an ODIN **reasoning** case — into one
deterministic, self-checked bundle.

> **Case Bundle v0.2 packages verified Project Witness case records. It does not
> prove evidence contents are true and does not prove ODIN claims are true.**

Case Bundle v0.2 packages verified case records only. It does not prove evidence contents are true and does not prove ODIN claims are true. It does not execute actions or run reasoning, and it is not connected to Coordinator or Companion yet.

It is the first Case Bundle version that combines action, evidence, and reasoning
records in a single bundle (Case Bundle v0.1.1 packaged a Sentinel action case
only).

## What it packages

Three verified input case records, produced by the frozen upstream importers:

- **Sentinel action case** — output of Histor-lite v0.1.2 `import-sentinel`
  (`case_summary.json`, `sentinel_replay_report.txt`, `checksums.txt`).
- **Aletheia evidence case** — output of Histor-lite Aletheia Importer v0.1
  (`evidence_case_summary.json`, `aletheia_manifest_copy.json`,
  `aletheia_replay_report.txt`, `evidence_case_checksums.txt`).
- **ODIN reasoning case** — output of Histor-lite ODIN Importer v0.1
  (`odin_case_summary.json`, `odin_reasoning_report_copy.json`,
  `odin_proof_trace_copy.json`, `odin_claims_copy.json`, `odin_replay_report.txt`,
  `odin_case_checksums.txt`).

At build time it verifies each input case, confirms all three share one `case_id`,
copies each record **byte-for-byte** into the bundle, writes a canonical
`case_manifest.json` and a strict `bundle_checksums.txt`, then self-verifies before
returning success.

## What it does NOT do

- It **does not prove** the evidence contents are true.
- It **does not prove** ODIN claims are true.
- It **does not execute** Sentinel actions, **does not run** Aletheia bundling, and
  **does not run** ODIN reasoning — it only packages already-verified records.
- It does not reinterpret evidence, and adds no natural-language interpretation, no
  LLM, no signing, and no external anchoring.
- It is **not connected to Coordinator or Companion** yet.
- Like the rest of the stack it uses unkeyed hashes, so a self-consistent
  whole-folder fabrication remains possible. The bundle proves structural chain
  integrity, not truth. It is not production evidence custody.

## ODIN status rule

An ODIN reasoning case is packageable when its status is either `CONSISTENT` or
`CONTRADICTION_DETECTED` — a structural contradiction is a valid, packageable
outcome, **not** a bundle failure. `INVALID_INPUT` is never packageable.

## Bundle layout

```
project_witness_case_bundle/
  case_manifest.json
  bundle_checksums.txt
  sentinel_case/   (case_summary.json, sentinel_replay_report.txt, checksums.txt)
  aletheia_case/   (evidence_case_summary.json, aletheia_manifest_copy.json,
                    aletheia_replay_report.txt, evidence_case_checksums.txt)
  odin_case/       (odin_case_summary.json, odin_reasoning_report_copy.json,
                    odin_proof_trace_copy.json, odin_claims_copy.json,
                    odin_replay_report.txt, odin_case_checksums.txt)
```

See `RUN_FORMAT.md` for the manifest fields and the 14-line bundle checksums.

## Field-mapping note

The frozen Histor-lite Sentinel case uses `import_status` (real value `IMPORTED`)
and `sentinel_replay_verdict` (e.g. `PASS_STRICT`). The manifest maps these to
`sentinel.case_status` and `sentinel.action_status` respectively, preserving the
real subcase field names inside the copied record.

## Usage

Build a bundle from three verified case folders:

```
python3 case_bundle_v02.py build \
  --sentinel-case /path/to/histor_sentinel_case \
  --aletheia-case /path/to/histor_aletheia_case \
  --odin-case /path/to/histor_odin_case \
  --out /path/to/project_witness_case_bundle
```

Verify a built bundle:

```
python3 case_bundle_v02.py verify --bundle /path/to/project_witness_case_bundle
```

Run the in-process self-check:

```
python3 case_bundle_v02.py selfcheck
# or
python3 selfcheck.py
```

## Release commands

The authoritative freeze gate is the explicit list of individual commands in
`RELEASE_COMMANDS.md` (run each from a clean extraction). There is no subprocess
orchestrator in the gate; `verify_release_manifest.py` is a static checker that
launches no subprocesses.

Standard library only.
