# Run Format — Companion CLI v0.3

## Output folder

`create-evidence-case` produces exactly these top-level entries:

    workflow_request.json
    companion_report.json
    companion_steps.json
    companion_checksums.txt
    coordinator_output/

No unknown extra top-level files. `coordinator_output/` is the full Coordinator
Workflow v0.3 output, preserved exactly, including `atlas_validation_report.json`,
`atlas_registry_copy.json`, `workflow_report.json`, `workflow_steps.json`,
`workflow_checksums.txt`, and the eight component subfolders.

## Canonical forms

Companion JSON (`workflow_request.json`, `companion_report.json`,
`companion_steps.json`) is canonical with sorted keys, tight separators, and NO
trailing newline. The preserved Coordinator files keep their own forms:
Coordinator JSON has no trailing newline, and `atlas_registry_copy.json` keeps the
Atlas trailing-newline canonical form.

## companion_checksums.txt

Exactly eight lines, each `<lowercase-sha256>  <relative-path>`:

    workflow_request.json
    companion_report.json
    companion_steps.json
    coordinator_output/workflow_report.json
    coordinator_output/workflow_steps.json
    coordinator_output/atlas_validation_report.json
    coordinator_output/atlas_registry_copy.json
    coordinator_output/case_bundle_v02/case_manifest.json

Keys (the paths) must appear exactly once; missing, duplicate, or unknown keys
fail; uppercase or malformed digests fail; a recomputed hash mismatch fails.

## Companion statuses

    COMPANION_COMPLETED
    FAILED_INPUT_VALIDATION
    FAILED_COORDINATOR_RUN
    FAILED_COORDINATOR_VERIFY
    FAILED_ATLAS_VALIDATION
    FAILED_COMPANION_VERIFY
    FAILED_CHECKSUMS_INVALID

If Coordinator reports a failed Atlas validation, Companion fails with
`FAILED_ATLAS_VALIDATION`.

## Manual integration smoke test (NOT part of the freeze gate)

This uses the real frozen Coordinator Workflow v0.3 (and, through it, the real
frozen components). It is documented for convenience only. The default unit tests
never construct the subprocess runner.

    python3 companion.py create-evidence-case \
      --case-id case_001 \
      --evidence-id evidence_001 \
      --evidence-file /tmp/evidence.txt \
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
      --out /tmp/companion_v03_output

    python3 companion.py verify --run /tmp/companion_v03_output

Expected on success:

    companion_status            = COMPANION_COMPLETED
    coordinator_workflow_status = WORKFLOW_COMPLETED
    atlas_validation_status     = ATLAS_VALIDATED
    atlas_registry_status       = REGISTRY_VERIFIED
    sentinel_status             = PASS_STRICT
    aletheia_status             = VERIFIED_PRESENT
    bridge_status               = CONVERTED
    odin_reasoning_status       = CONSISTENT or CONTRADICTION_DETECTED
    case_bundle_status          = BUNDLED_VERIFIED_CASE
    verify passes
