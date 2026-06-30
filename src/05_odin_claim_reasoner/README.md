# ODIN Claim Reasoner v0.1

A small, deterministic reasoning component that operates over **already-structured
claims**. It validates a claim set, detects **direct structural contradictions**,
preserves support references, and emits a canonical reasoning report and proof
trace. It is the first piece of ODIN in Project Witness.

It does **not** prove claims true. It does not interpret natural language, use an
LLM, or execute actions. It only reasons over structured claims that already
exist.

## What it is

```
structured claims (claims.json)
  → ODIN Claim Reasoner
    → claims_canonical.json   (the validated claim set, canonical)
    → reasoning_report.json   (status + per-claim + contradictions, canonical)
    → proof_trace.json        (deterministic step-by-step trace, canonical)
    → odin_checksums.txt       (sha256 of the three files)
  → verify output
```

This component is **not connected to the workflow** yet. It prepares the stack for
a later path (Companion / Coordinator → Aletheia evidence bundle → ODIN claims →
Histor / Case Bundle), but v0.1 stands alone.

## What it does NOT do

- No natural-language parsing, no LLM.
- No ontology expansion, no probabilistic reasoning, no full rule engine.
- No action gating, no Coordinator integration yet.
- No signing, no external anchoring.
- It does **not** prove claims true. A consistent claim set is structurally
  consistent — nothing more.

## Claims it accepts (structured only)

Each claim has exactly: `claim_id`, `subject`, `predicate`, `object`, `polarity`,
`support`. `polarity` is `AFFIRMED` or `DENIED`. `object` is a string, boolean,
integer, or null (no floats in v0.1). `support` is a non-empty list, each item
with exactly `support_id`, `source_component`, `source_id`, `source_sha256`. A
claim with an empty support list is refused as invalid input.

## Direct contradiction rules (only these in v0.1)

Two claims with the **same subject and same predicate** contradict if either:
- they have **different objects** (`SAME_SUBJECT_PREDICATE_DIFFERENT_OBJECT`); or
- they have the **same object but opposite polarity**
  (`SAME_SUBJECT_PREDICATE_SAME_OBJECT_OPPOSITE_POLARITY`).

No other inference is performed. (Note: `true` and `1` are treated as different
objects — JSON booleans and integers are distinct.)

## How to validate claims

```bash
python3 odin.py validate-claims --claims /path/to/claims.json
```

## How to run reasoning

```bash
python3 odin.py reason --claims /path/to/claims.json --out /path/to/odin_output
```

The output directory must be empty or absent. `reasoning_status` is `CONSISTENT`,
`CONTRADICTION_DETECTED`, or (for invalid input) the run is refused with
`INVALID_INPUT` and no successful output is written.

## How to verify ODIN output

```bash
python3 odin.py verify --run /path/to/odin_output
```

Verification checks: required files exist; no unknown extra files; all three JSON
files are valid **and canonical**; the checksums file parses strictly and matches
the recomputed hashes; the report's contradiction count and status match a fresh
recomputation from the claims; and the proof trace references only valid claim IDs.

## Optional: import from Aletheia

```bash
python3 odin.py import-aletheia --manifest /path/to/evidence_manifest.json \
  --out /path/to/claims.json
```

This converts an Aletheia Evidence Bundle manifest (which must be
`VERIFIED_PRESENT`) into structured **integrity/presence** claims only
(`evidence.present`, `evidence.integrity_verified`). It never creates a claim about
the truth of the file's contents.

## How to run the release commands

See [RELEASE_COMMANDS.md](RELEASE_COMMANDS.md). The freeze gate is the explicit
list of individual commands plus the static `verify_release_manifest.py`. There is
no wrapper orchestrator in the gate.

## Not full ODIN

ODIN v0.1 is a deterministic mini-reasoner over structured claims. It is **not** a
full theorem prover, not a truth oracle, and not connected to the workflow. It
reports structural consistency only.
