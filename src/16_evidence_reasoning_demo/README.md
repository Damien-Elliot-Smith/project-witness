# Evidence Reasoning Demo v0.1

A deterministic demo runner that proves the local Project Witness chain works end
to end:

```
one local evidence file
  -> Aletheia Evidence Bundle v0.1   (bundle the file, hash it, verify)
  -> Aletheia -> ODIN Bridge v0.1     (convert to integrity/presence claims)
  -> ODIN Claim Reasoner v0.1         (reason over the claims, verify)
  -> verified demo output
```

It is Move 14 of Project Witness: a harness that drives four frozen components and
shows that a local file can be bundled as evidence, converted into ODIN
integrity/presence claims, reasoned over, and verified — all deterministically.

> Evidence Reasoning Demo v0.1 proves only that the local evidence-integrity
> reasoning chain executes and verifies. It does not prove the evidence contents
> are true.

## Which frozen components it calls

- Aletheia Evidence Bundle v0.1 (`aletheia.py bundle-file`, `verify`)
- Aletheia -> ODIN Bridge v0.1 (`bridge.py convert`, `verify`)
- ODIN Claim Reasoner v0.1 (`odin.py reason`, `verify`)

It calls them via subprocess at runtime and never modifies them. The component
outputs are copied into the demo folder and preserved exactly.

## What the demo proves

That the chain runs to completion and every component output verifies: the Aletheia
bundle is `VERIFIED_PRESENT`, the bridge conversion is `CONVERTED`, the generated
claims are exactly `evidence.present` and `evidence.integrity_verified`, ODIN
reasons `CONSISTENT`, and every produced folder verifies.

## What the demo does NOT prove

- It does **not** prove the evidence contents are true, accurate, authentic, or
  real. It only proves the integrity-reasoning chain executes and verifies.
- It does not interpret the evidence file, use an LLM, parse natural language, or
  gate actions.
- It does not sign or externally anchor outputs.
- It is **not connected to Companion or Coordinator yet**.
- One evidence file only — no multiple files, directories, web, sensors, or OCR.

## How to run `demo.py run`

```bash
python3 demo.py run \
  --evidence-file /path/to/evidence.txt \
  --case-id case_001 \
  --evidence-id evidence_001 \
  --aletheia-root /path/to/aletheia_evidence_bundle_v01 \
  --bridge-root /path/to/aletheia_odin_bridge_v01 \
  --odin-root /path/to/odin_claim_reasoner_v01 \
  --out /path/to/demo_output
```

The runner validates the IDs and evidence source (refusing missing/directory/
symlink sources), refuses a non-empty output directory, checks the three component
roots exist, then runs the six chain steps in order. If any step fails, later steps
do not run and the failure is reported with a specific `demo_status`. On success it
writes `demo_report.json`, `demo_steps.json`, and `demo_checksums.txt`, alongside
the preserved component output subfolders.

## How to run `demo.py verify`

```bash
python3 demo.py verify --run /path/to/demo_output
```

Verification checks: required files and subfolders exist; no unknown extra top-level
files; `demo_report.json` and `demo_steps.json` are valid **and canonical**; the
checksums file parses strictly and matches recomputed hashes of the demo files and
the referenced component files; `case_id` matches across the demo report, demo
steps, bridge report, and ODIN report; `evidence_id` matches the Aletheia manifest
and bridge output; `generated_claims` contains only the two allowed predicates and
no truth-like predicate; `odin_reasoning_status = CONSISTENT`; and
`demo_status = DEMO_COMPLETED`.

## How to run selfcheck

```bash
python3 selfcheck.py
```

In-process invariant gates only (uses an in-process fake runner); it never launches
the unit suite or any subprocess.

## How to run the release commands

See [RELEASE_COMMANDS.md](RELEASE_COMMANDS.md). The freeze gate is the explicit list
of individual commands plus the static `verify_release_manifest.py`. The default
unit suite uses an in-process fake component runner, so the gate spawns no
subprocesses. There is no wrapper orchestrator in the gate.

## Honesty boundary

Because nothing is signed or anchored, a self-consistent whole-folder fabrication
remains possible — this is tamper-evidence within the demo output, not
tamper-proofness, and not production evidence custody. The demo proves the chain
executes and verifies; it does not prove the evidence contents are true.
