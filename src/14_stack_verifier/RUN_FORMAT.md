# Run Format — Stack Verifier v0.1

## Output folder

`check` produces exactly these top-level entries:

    stack_verification_report.json
    stack_verification_steps.json
    stack_verification_checksums.txt

No unknown extra top-level files. The source run and manifest run are NOT copied;
only checked artifact relative paths and hashes are recorded.

## Canonical forms

`stack_verification_report.json` and `stack_verification_steps.json` use canonical
JSON with sorted keys, tight separators, and NO trailing newline.

## stack_verification_checksums.txt

Exactly two lines, each `<lowercase-sha256>  <relative-path>`:

    stack_verification_report.json
    stack_verification_steps.json

Keys must appear exactly once; missing, duplicate, or unknown keys fail; uppercase
or malformed digests fail; a recomputed hash mismatch fails.

## stack_verification_status values

    STACK_VERIFIED
    FAILED_SOURCE_MISSING
    FAILED_SOURCE_TYPE_INVALID
    FAILED_SOURCE_STRUCTURE_INVALID
    FAILED_SOURCE_CHECKSUMS
    FAILED_MANIFEST_MISSING
    FAILED_MANIFEST_STRUCTURE_INVALID
    FAILED_MANIFEST_CHECKSUMS
    FAILED_CASE_ID_MISMATCH
    FAILED_EVIDENCE_ID_MISMATCH
    FAILED_STATUS_INVALID
    FAILED_ATLAS_INVALID
    FAILED_MANIFEST_MISMATCH
    FAILED_TRUTH_CLAIM
    FAILED_CHECKSUMS_INVALID

For a `coordinator_v03_output` source, `companion_status` is `NOT_APPLICABLE`. When
no manifest is provided, `manifest_status` is `NOT_PROVIDED`.

## Steps (fixed order)

    step_001 VALIDATE_INPUTS
    step_002 VERIFY_SOURCE_STRUCTURE
    step_003 VERIFY_SOURCE_CHECKSUMS
    step_004 VERIFY_ATLAS_VOCABULARY
    step_005 VERIFY_UNIFIED_MANIFEST
    step_006 CROSS_CHECK_IDS_AND_STATUSES
    step_007 CHECK_TRUTH_BOUNDARY
    step_008 WRITE_STACK_VERIFICATION_REPORT
    step_009 VERIFY_STACK_VERIFIER_OUTPUT

If a step fails, later steps are marked SKIPPED_AFTER_FAILURE.

## checked_artifacts

Each entry records `artifact_id`, `source_label` (`SOURCE_RUN` or `MANIFEST_RUN`),
`relative_path` (never absolute), `sha256` (lowercase), `artifact_type`, and
`check_status`. No duplicate artifact_id and no duplicate relative_path within the
same source_label.

## Manual smoke test (NOT part of the freeze gate)

This uses real previously-produced outputs. It is documented for convenience only;
the default unit tests use synthetic source and manifest outputs and spawn no
subprocesses.

    python3 stack_verify.py check \
      --source-type companion_v03_output \
      --source-run /path/to/companion_v03_output \
      --manifest-run /path/to/unified_manifest_output \
      --out /tmp/stack_verifier_output

    python3 stack_verify.py verify --run /tmp/stack_verifier_output

Expected on success:

    stack_verification_status = STACK_VERIFIED
    source_status             = SOURCE_VERIFIED
    manifest_status           = MANIFEST_VERIFIED
    case_id_consistent        = true
    evidence_id_consistent    = true
    checksums_valid           = true
    atlas_vocabulary_valid    = true
    manifest_consistent       = true
    truth_boundary_valid      = true
    verify passes
