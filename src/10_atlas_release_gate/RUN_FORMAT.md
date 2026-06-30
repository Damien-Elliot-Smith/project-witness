# Run Format — Atlas Release Gate v0.1

## Release-gate output folder

A successful `check` produces an output folder containing exactly:

    atlas_release_gate_report.json
    atlas_release_gate_steps.json
    atlas_release_gate_checksums.txt
    atlas_export/
        atlas_registry_copy.json
        atlas_summary.json
        atlas_checksums.txt

No other top-level files are permitted, and `atlas_export/` may contain only the
three files listed above.

## atlas_release_gate_report.json

Deterministic canonical JSON (sorted keys, tight separators, no trailing
newline). Fields:

    atlas_release_gate_version       "0.1.0"
    checked_component                "atlas_registry"
    checked_component_version        "0.1.0"
    release_gate_status              one allowed gate status
    registry_status                  REGISTRY_VERIFIED on success
    export_status                    EXPORT_VERIFIED on success
    required_files_present           bool
    documentation_present            bool
    honesty_boundary_present         bool
    forbidden_features_absent        bool
    known_limitations                list of honest limitation sentences

Allowed `release_gate_status` values:

    RELEASE_GATE_PASSED
    FAILED_ATLAS_ROOT_MISSING
    FAILED_REQUIRED_FILE_MISSING
    FAILED_REGISTRY_VERIFY
    FAILED_EXPORT_VERIFY
    FAILED_DOCUMENTATION_CHECK
    FAILED_HONESTY_CHECK
    FAILED_FORBIDDEN_FEATURE_CHECK
    FAILED_CHECKSUMS_INVALID

## atlas_release_gate_steps.json

Canonical JSON. An ordered list of nine steps:

    step_001 CHECK_REQUIRED_FILES
    step_002 VERIFY_ATLAS_REGISTRY
    step_003 EXPORT_ATLAS_REGISTRY
    step_004 VERIFY_ATLAS_EXPORT
    step_005 CHECK_DOCUMENTATION
    step_006 CHECK_HONESTY_BOUNDARY
    step_007 CHECK_FORBIDDEN_FEATURES
    step_008 WRITE_RELEASE_GATE_REPORT
    step_009 VERIFY_RELEASE_GATE_OUTPUT

Allowed step statuses: COMPLETED, FAILED, SKIPPED_AFTER_FAILURE. If a step
fails, no later step runs; every later step is marked SKIPPED_AFTER_FAILURE.

## atlas_release_gate_checksums.txt

One line per canonical output file, in fixed order:

    <lowercase-sha256><two spaces><relative-path>

Keys (relative paths) must appear exactly once. Duplicate, missing, or unknown
keys fail. Uppercase or malformed digests fail. A recomputed-hash mismatch
fails. Only lowercase SHA-256 digests are accepted.

## Manual integration smoke test (not part of the freeze gate)

This exercises the real frozen Atlas v0.1 via subprocess and is documented for
convenience only. It is NOT run by the freeze gate.

The adapter (`SubprocessAtlasRunner`) targets the frozen Atlas Registry v0.1 CLI
contract:

    atlas.py verify        --registry registry/atlas_registry.json
    atlas.py export        --registry registry/atlas_registry.json --out <export_dir>
    atlas.py verify-export --export <export_dir>

`verify` and `export` are run with the working directory set to the Atlas root
(so `registry/atlas_registry.json` resolves), and `verify-export` is also run
from the Atlas root (so `atlas.py` is found; the `--export` path is absolute).
The Atlas `export` is expected to write exactly `atlas_registry_copy.json`,
`atlas_summary.json`, and `atlas_checksums.txt` into the export directory.

Run:

    python3 atlas_release_gate.py check \
      --atlas-root /path/to/atlas_registry_v01 \
      --out /tmp/atlas_release_gate_output

    python3 atlas_release_gate.py verify \
      --run /tmp/atlas_release_gate_output

Expected on success:

    release_gate_status = RELEASE_GATE_PASSED
    registry_status     = REGISTRY_VERIFIED
    export_status       = EXPORT_VERIFIED
    required_files_present    = true
    documentation_present     = true
    honesty_boundary_present  = true
    forbidden_features_absent = true
    verify passes
