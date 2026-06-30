# Run Format — Coordinator Workflow v0.3

## Request

Deterministic canonical JSON. Required fields:

    coordinator_workflow_request_version  "0.3.0"
    workflow_type                         "CREATE_EVIDENCE_REASONING_CASE"
    requested_case_id                     e.g. "case_001"
    evidence_id                           e.g. "evidence_001"
    allowed_root                          e.g. "/tmp/project_witness_cases"
    case_directory_name                   e.g. "case_001"
    evidence_file                         path to the evidence file
    component_roots                       object of frozen component roots

`component_roots` includes: `atlas_registry_root`, `sentinel_root`,
`histor_lite_root`, `aletheia_root`, `bridge_root`, `odin_root`,
`histor_aletheia_root`, `histor_odin_root`, `case_bundle_v02_root`.

The only allowed workflow type is `CREATE_EVIDENCE_REASONING_CASE`. The only
action type is `CREATE_DIRECTORY`.

## Output folder

A run produces exactly these top-level entries:

    workflow_request_copy.json
    workflow_report.json
    workflow_steps.json
    workflow_checksums.txt
    atlas_validation_report.json
    atlas_registry_copy.json
    sentinel_run/
    histor_sentinel_case/
    aletheia_bundle/
    histor_aletheia_case/
    bridge_output/
    odin_output/
    histor_odin_case/
    case_bundle_v02/

No unknown extra top-level files.

## Canonical forms

Coordinator JSON (`workflow_request_copy.json`, `workflow_report.json`,
`workflow_steps.json`, `atlas_validation_report.json`) is canonical with sorted
keys, tight separators, and NO trailing newline. `atlas_registry_copy.json` keeps
the Atlas canonical form (sorted keys, tight separators, trailing newline) so the
copy is byte-identical to the verified Atlas registry.

## workflow_checksums.txt

One line per present canonical output file: `<lowercase-sha256>  <relative-path>`
(exactly two spaces). Keys (the relative paths) must appear exactly once; missing,
duplicate, unknown keys fail; uppercase or malformed digests fail; a recomputed
hash mismatch fails.

## atlas_validation_report.json

Canonical JSON with `atlas_validation_status` (one of the allowed Atlas
validation statuses), `atlas_registry_status`, the per-check booleans, and honest
`known_limitations`.

Allowed Atlas validation statuses: `ATLAS_VALIDATED`, `FAILED_ATLAS_ROOT_MISSING`,
`FAILED_ATLAS_REGISTRY_MISSING`, `FAILED_ATLAS_VERIFY`,
`FAILED_ATLAS_WORKFLOW_TYPE_MISSING`, `FAILED_ATLAS_ACTION_TYPE_MISSING`,
`FAILED_ATLAS_COMPONENT_MISSING`, `FAILED_ATLAS_STATUS_MISSING`,
`FAILED_ATLAS_PREDICATE_MISSING`, `FAILED_ATLAS_TRUTH_CLAIM`,
`FAILED_ATLAS_FORBIDDEN_ACTION`.

## Manual integration smoke test (NOT part of the freeze gate)

This uses the real frozen components and is documented for convenience only.
Atlas validation runs in-process against the real Atlas Registry v0.1; the lower
components are invoked via subprocess (the `SubprocessComponentRunner` adapter,
which must be wired to each frozen component's CLI before use).

    python3 coordinator_v03.py run \
      --request /tmp/workflow_request_v03.json \
      --out /tmp/coordinator_v03_output

    python3 coordinator_v03.py verify \
      --run /tmp/coordinator_v03_output

Frozen components: Atlas Registry v0.1, Sentinel Core v0.2.2, Histor-lite v0.1.2,
Aletheia Evidence Bundle v0.1, Aletheia to ODIN Bridge v0.1, ODIN Claim Reasoner
v0.1, Histor-lite Aletheia Importer v0.1, Histor-lite ODIN Importer v0.1, Case
Bundle v0.2.

Expected on success:

    workflow_status        = WORKFLOW_COMPLETED
    atlas_validation_status = ATLAS_VALIDATED
    atlas_registry_status  = REGISTRY_VERIFIED
    sentinel_status        = PASS_STRICT
    aletheia_status        = VERIFIED_PRESENT
    bridge_status          = CONVERTED
    odin_reasoning_status  = CONSISTENT or CONTRADICTION_DETECTED
    case_bundle_status     = BUNDLED_VERIFIED_CASE
    verify passes
