# Run Format — Unified Case Manifest v0.1

## Output folder

`build` produces exactly these top-level entries:

    unified_case_manifest.json
    unified_manifest_checksums.txt
    source_index.json

No unknown extra top-level files. The whole source run is NOT copied; only source
artifact relative paths and hashes are recorded.

## Canonical forms

`unified_case_manifest.json` and `source_index.json` use canonical JSON with
sorted keys, tight separators, and NO trailing newline.

## unified_manifest_checksums.txt

Exactly two lines, each `<lowercase-sha256>  <relative-path>`:

    unified_case_manifest.json
    source_index.json

Keys must appear exactly once; missing, duplicate, or unknown keys fail; uppercase
or malformed digests fail; a recomputed hash mismatch fails.

## source_status values

    SOURCE_VERIFIED
    FAILED_SOURCE_MISSING
    FAILED_SOURCE_TYPE_INVALID
    FAILED_SOURCE_STRUCTURE_INVALID
    FAILED_SOURCE_VERIFY
    FAILED_CASE_ID_MISMATCH
    FAILED_EVIDENCE_ID_MISMATCH
    FAILED_STATUS_INVALID
    FAILED_ATLAS_INVALID
    FAILED_TRUTH_CLAIM
    FAILED_CHECKSUMS_INVALID

For a `coordinator_v03_output` source, `companion_status` is `NOT_APPLICABLE`.

## source_artifacts

Each entry records `artifact_id`, `relative_path` (relative to the source root,
never absolute), `sha256` (lowercase), `artifact_type`, and `produced_by`. No
duplicate artifact_id, no duplicate relative_path.

## component_versions

Versions are recorded only where observable from the source reports
(`coordinator_workflow_v03`, `atlas_registry_v01`, and `companion_cli_v03` for a
Companion source, plus `unified_case_manifest_v01` itself). Components whose
versions cannot be observed from the source output are recorded as
`UNKNOWN_FROM_SOURCE`; that is not a failure.

## Manual smoke test (NOT part of the freeze gate)

This uses a real previously-produced case output. It is documented for convenience
only; the default unit tests use synthetic source outputs and spawn no
subprocesses.

    python3 unified_manifest.py build \
      --source-type companion_v03_output \
      --source-run /path/to/companion_v03_output \
      --out /tmp/unified_manifest_output

    python3 unified_manifest.py verify --run /tmp/unified_manifest_output

Expected on success:

    source_status            = SOURCE_VERIFIED
    case_id recorded
    evidence_id recorded
    workflow_type            = CREATE_EVIDENCE_REASONING_CASE
    action_type              = CREATE_DIRECTORY
    atlas_validation_status  = ATLAS_VALIDATED
    atlas_registry_status    = REGISTRY_VERIFIED
    artifact hashes recorded
    verify passes
