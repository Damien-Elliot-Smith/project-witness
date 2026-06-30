# Coordinator Workflow v0.3.2 — case bundle evidence_id compatibility repair

**v0.3.2 is a narrow blocker repair for Move 30, not a new feature.** After the
real Case Bundle v0.2 build/verify succeeds (`BUNDLED_VERIFIED_CASE`), the
coordinator now writes a clearly-labelled compatibility summary at
`coordinator_output/case_bundle_v02/case_manifest.json` carrying the workflow
`evidence_id` (plus `case_id` and `bundle_status`), and preserves the raw Case
Bundle manifest byte-for-byte at `raw_case_bundle_manifest.json`. Case Bundle
v0.2 itself records no `evidence_id`; Unified Case Manifest v0.1 and Stack
Verifier v0.1 require it, and the old fake runner had hidden the gap. The
summary is labelled `source = coordinator_compatibility_summary` with
`raw_case_bundle_manifest_preserved = true`, so no reader mistakes it for native
Case Bundle output, and it is only written after a genuine BUNDLED_VERIFIED_CASE.
The output schema and `coordinator_workflow_version` stay **0.3.0**; nothing
else changed. (v0.3.1 wired the real lower-component CLIs; that behaviour is
retained below.)

# Coordinator Workflow v0.3.1 — real lower-component runner repair

**v0.3.1 is a blocker repair for Move 30, not a new feature.** The package
folder/zip is named `coordinator_workflow_v031`, but the output schema and
`coordinator_workflow_version` stay **0.3.0** so Companion CLI v0.3 and the
Connected Demo remain compatible. v0.3.0 shipped `SubprocessComponentRunner`
as an unwired manual-integration stub (every method raised
`NotImplementedError`), so a real connected run could never complete. v0.3.1
wires the same nine workflow steps to the already-frozen lower-component CLIs
(Sentinel Core v0.2.2, Histor-lite v0.1.2 + Aletheia/ODIN importers, Aletheia
Evidence Bundle v0.1, Aletheia->ODIN Bridge v0.1, ODIN Claim Reasoner v0.1,
Case Bundle v0.2) via subprocess. No frozen lower component was modified; no
workflow step, action type, or Atlas term was added or changed. A real
integration run against the frozen chain reaches `WORKFLOW_COMPLETED` and
`verify_ok: true` (see TEST_RESULTS.md). The default unit suite and freeze
gate stay fully in-process via an injectable executor and never spawn a
subprocess.

# Coordinator Workflow v0.3 — Atlas-connected Coordinator

Coordinator Workflow v0.3 runs the same one-case evidence-and-reasoning workflow
as v0.2, but validates workflow vocabulary against Atlas Registry v0.1. Atlas is
read-only and does not prove truth.

## What it is

Coordinator Workflow v0.3 extends Coordinator v0.2 with Atlas vocabulary
validation. Before any lower component runs, it reads the frozen Atlas Registry
v0.1 and confirms that the workflow's vocabulary — the workflow type, the action
type, the required components, the statuses the workflow will observe, and the
claim predicates from Bridge/ODIN — all exist in Atlas, that Atlas is truth-free,
and that Atlas contains no forbidden future action types. Only then does it run
the v0.2 pipeline: Sentinel, Histor (Sentinel), Aletheia, Histor (Aletheia),
Bridge, ODIN, Histor (ODIN), Case Bundle v0.2 build, and Case Bundle v0.2 verify.

Atlas is read-only. Coordinator v0.3 does not modify Atlas, does not add terms to
Atlas, and does not use Atlas to prove truth. It uses Atlas only as a canonical
vocabulary boundary. Coordinator v0.3 does not prove truth: it records and
verifies structure and vocabulary, never the truth of evidence, claims, files, or
sources.

Companion is not connected yet. Coordinator v0.3 does not connect Companion.

## The eleven steps

    step_001 ATLAS_VALIDATE_REGISTRY
    step_002 SENTINEL_CREATE_DIRECTORY
    step_003 HISTOR_IMPORT_SENTINEL
    step_004 ALETHEIA_BUNDLE_FILE
    step_005 HISTOR_IMPORT_ALETHEIA
    step_006 BRIDGE_CONVERT_ALETHEIA_TO_ODIN
    step_007 ODIN_REASON
    step_008 HISTOR_IMPORT_ODIN
    step_009 CASE_BUNDLE_V02_BUILD
    step_010 CASE_BUNDLE_V02_VERIFY
    step_011 COORDINATOR_VERIFY_OUTPUT

If Atlas validation fails, no lower component runs: step_001 is FAILED and every
later step is SKIPPED_AFTER_FAILURE.

## How to run

    python3 coordinator_v03.py run \
      --request /path/to/workflow_request.json \
      --out /path/to/workflow_output

## How to verify

    python3 coordinator_v03.py verify \
      --run /path/to/workflow_output

## How to selfcheck

    python3 coordinator_v03.py selfcheck

Or, equivalently:

    python3 selfcheck.py

## How to run the release commands

The authoritative freeze gate is the explicit list of commands in
`RELEASE_COMMANDS.md`. Run each one individually from a clean extraction.

## Boundaries

- Coordinator Workflow v0.3 extends Coordinator v0.2 with Atlas vocabulary validation.
- Atlas is read-only.
- Coordinator Workflow v0.3 does not modify Atlas.
- Coordinator Workflow v0.3 does not prove truth.
- Coordinator Workflow v0.3 does not connect Companion yet.

## Runtime and test boundary

At runtime, lower components are invoked via subprocess (manual integration, see
`RUN_FORMAT.md`). The default unit tests inject in-process fake component runners
and an in-process Atlas verifier; they require no real frozen component folders
and spawn no subprocesses. Atlas validation is in-process and read-only.
