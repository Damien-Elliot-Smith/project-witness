# Companion CLI v0.3.1 — coordinator request-file hygiene repair

**v0.3.1 is a narrow blocker repair for Move 30, not a new feature.** The
package folder/zip is named `companion_cli_v031`, but the output schema and
`companion_cli_version` stay **0.3.0** so the output remains compatible with
Unified Case Manifest v0.1, Stack Verifier v0.1, Stack Selfcheck v0.1, and the
Connected Demo. v0.3.0's `SubprocessCoordinatorRunner` wrote
`_coordinator_request.json` into the Companion-output top level and never
removed it, so Companion's own verifier rejected the stray file
(`companion_status = FAILED_COMPANION_VERIFY`). v0.3.1 writes that request to a
private temp directory **outside** the output tree and deletes it, so the final
Companion output contains only allowed top-level entries. Nothing else changed:
same CLI shape, same steps, same schema, same in-process freeze gate. A real
run against frozen Coordinator v0.3.1 and the frozen lower components reaches
`COMPANION_COMPLETED` and `verify_ok: true` (see TEST_RESULTS.md).

# Companion CLI v0.3 — Atlas Terms Connected

Companion CLI v0.3 wraps Coordinator Workflow v0.3 for one Atlas-validated
evidence-and-reasoning case workflow. Atlas is read-only, and Companion does not
modify Atlas, add Atlas terms, or prove truth.

## What it is

Companion CLI v0.3 is a human-facing wrapper around Coordinator Workflow v0.3. It
lets a user run one Atlas-validated evidence-and-reasoning case and preserves the
Atlas validation result in the Companion output. It does what Companion CLI v0.2
did, but it now calls Coordinator Workflow v0.3 (instead of v0.2) and mirrors the
Atlas validation fields into its own report.

Coordinator Workflow v0.3 validates the workflow vocabulary against Atlas Registry
v0.1. Atlas is read-only. Companion CLI v0.3 does not modify Atlas and does not
add Atlas terms; it uses Atlas only as a read-only vocabulary boundary, through
Coordinator v0.3. Companion CLI v0.3 does not prove truth: it records and verifies
structure and vocabulary, never the truth of evidence, claims, files, or sources.

Companion CLI v0.3 does not call lower components directly. It calls only
Coordinator Workflow v0.3 (run and verify). It never calls Sentinel, Histor-lite,
Aletheia, the Bridge, ODIN, or Case Bundle directly, and it never mutates Atlas.

## How to run create-evidence-case

    python3 companion.py create-evidence-case \
      --case-id case_001 \
      --evidence-id evidence_001 \
      --evidence-file /path/to/evidence.txt \
      --allowed-root /tmp/project_witness_cases \
      --case-directory-name case_001 \
      --coordinator-root /path/to/coordinator_workflow_v03 \
      --atlas-registry-root /path/to/atlas_registry_v01 \
      --sentinel-root /path/to/sentinel_core_v022 \
      --histor-lite-root /path/to/histor_lite_v012 \
      --aletheia-root /path/to/aletheia_evidence_bundle_v01 \
      --bridge-root /path/to/aletheia_odin_bridge_v01 \
      --odin-root /path/to/odin_claim_reasoner_v01 \
      --histor-aletheia-root /path/to/histor_lite_aletheia_importer_v01 \
      --histor-odin-root /path/to/histor_lite_odin_importer_v01 \
      --case-bundle-v02-root /path/to/case_bundle_v02 \
      --out /path/to/companion_output

## How to run verify

    python3 companion.py verify --run /path/to/companion_output

## How to run selfcheck

    python3 companion.py selfcheck

## Optional: list-atlas-terms (read-only)

    python3 companion.py list-atlas-terms --run /path/to/companion_output --section statuses

`list-atlas-terms` reads only the preserved
`coordinator_output/atlas_registry_copy.json`. It does not call Atlas directly,
modify anything, infer new terms, or interpret natural language.

## How to run the release commands

The authoritative freeze gate is the explicit list in `RELEASE_COMMANDS.md`. Run
each command individually from a clean extraction.

## Boundaries

- Companion CLI v0.3 wraps Coordinator Workflow v0.3.
- Atlas is read-only.
- Companion CLI v0.3 does not modify Atlas.
- Companion CLI v0.3 does not add Atlas terms.
- Companion CLI v0.3 does not prove truth.
- Companion CLI v0.3 does not call lower components directly.

## Runtime and test boundary

At runtime, Companion calls the frozen Coordinator Workflow v0.3 via subprocess
(the `SubprocessCoordinatorRunner` adapter). The default unit tests inject an
in-process fake Coordinator runner; they require no real frozen components and
spawn no subprocesses. `subprocess` appears only in the runtime adapter, never in
the freeze gate.
