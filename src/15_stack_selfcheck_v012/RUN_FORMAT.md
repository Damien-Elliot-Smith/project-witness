# Run Format — Stack Selfcheck v0.1.2

## Output folder

`check` produces exactly these top-level entries:

    stack_selfcheck_report.json
    stack_selfcheck_steps.json
    stack_selfcheck_checksums.txt

No unknown extra top-level files. The inventory and any Stack Verifier output are
NOT copied; only labels, component metadata, and result booleans are recorded.

## Canonical forms

`stack_selfcheck_report.json` and `stack_selfcheck_steps.json` use canonical JSON
with sorted keys, tight separators, and NO trailing newline. The input
`stack_inventory.json` must also be canonical.

## stack_selfcheck_checksums.txt

Exactly two lines, each `<lowercase-sha256>  <relative-path>`:

    stack_selfcheck_report.json
    stack_selfcheck_steps.json

Keys must appear exactly once; missing, duplicate, or unknown keys fail; uppercase
or malformed digests fail; a recomputed hash mismatch fails.

## stack_selfcheck_status values

    STACK_SELFCHECK_PASSED
    FAILED_INVENTORY_MISSING
    FAILED_INVENTORY_INVALID
    FAILED_REQUIRED_COMPONENT_MISSING
    FAILED_COMPONENT_ROOT_MISSING
    FAILED_COMPONENT_VERSION_MISMATCH
    FAILED_ZIP_SIDECAR_INVALID
    FAILED_DOCUMENTATION_BOUNDARY
    FAILED_STACK_VERIFIER_OUTPUT
    FAILED_TRUTH_CLAIM
    FAILED_CHECKSUMS_INVALID

`inventory_status` is `INVENTORY_VERIFIED` on success.
`documentation_boundary_status` is `DOCUMENTATION_BOUNDARY_VERIFIED` on success.
`stack_verifier_status` is `STACK_VERIFIER_OUTPUT_VERIFIED`, `NOT_PROVIDED`, or
`FAILED_STACK_VERIFIER_OUTPUT`.

## Steps (fixed order)

    step_001 VALIDATE_INVENTORY
    step_002 CHECK_REQUIRED_COMPONENTS
    step_003 CHECK_COMPONENT_ROOTS
    step_004 CHECK_ZIP_SIDECARS
    step_005 CHECK_DOCUMENTATION_BOUNDARIES
    step_006 CHECK_TRUTH_BOUNDARY
    step_007 CHECK_OPTIONAL_STACK_VERIFIER_OUTPUT
    step_008 WRITE_STACK_SELFCHECK_REPORT
    step_009 VERIFY_STACK_SELFCHECK_OUTPUT

If a step fails, later steps are marked SKIPPED_AFTER_FAILURE. The legacy
documentation allowance is resolved inside step_003 (CHECK_COMPONENT_ROOTS), at
the same point the expected documentation files are checked.

## legacy_documentation_allowances

A top-level list, sorted by `component_id`. Present (possibly empty) on every
successful report. Each record has exactly:

    component_id
    legacy_documentation_profile          (always "pre_documentation_convention_v0")
    legacy_documentation_allowance_used   (true iff a permitted file was omitted)
    missing_docs_allowed                  (the exact permitted files omitted)
    reason                                ("component frozen before documentation convention")

Only `sentinel_core_v022`, `histor_lite_v012`, `case_bundle_v011`, and
`atlas_red_blue_pack_v01` may appear, and `missing_docs_allowed` may never exceed
the registry allowance for that component. The verifier re-derives entitlement
from its own registry and rejects any over-broad, unknown, false, or
inconsistently-marked allowance.

## checked_components

Each entry records `component_id`, `expected_version`, `component_type`,
`required`, `root_present`, `zip_checksum_valid`, `documentation_boundary_present`,
`truth_boundary_present`, `legacy_documentation_profile` (the profile string when
a legacy allowance was used, else null), and `check_status`
(`COMPONENT_CHECKED`, or `COMPONENT_LEGACY_DOCUMENTATION_ACCEPTED` when a legacy
allowance was used). No absolute paths are stored.

## Stack inventory format

`stack_inventory.json` is canonical JSON with `stack_inventory_version`,
`stack_name`, a `components` list, and `known_limitations`. Each component has
`component_id`, `expected_version`, `component_type`, `root_path`, and `required`,
plus optional `zip_path`, `sha256_path`, `sidecar_optional`, `read_only`,
`evidence_component`, `atlas_connected`, `cli_file`, `version_file`, and
`legacy_documentation_profile`. The inventory may contain absolute local paths
because it is an input configuration; the output report never stores them.

## Manual smoke test (NOT part of the freeze gate)

This uses real frozen component folders and a real Stack Verifier output. It is
documented for convenience only; the default unit tests use synthetic component
folders, a synthetic inventory, and a synthetic Stack Verifier output, and spawn
no subprocesses.

    python3 stack_selfcheck.py check \
      --inventory /path/to/stack_inventory.json \
      --stack-verifier-run /path/to/stack_verifier_output \
      --out /tmp/stack_selfcheck_output

    python3 stack_selfcheck.py verify --run /tmp/stack_selfcheck_output
