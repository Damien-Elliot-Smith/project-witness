# RUN_FORMAT — Atlas Registry v0.1

## registry/atlas_registry.json

Deterministic canonical JSON (UTF-8, sorted keys, `(",",":")` separators, no NaN,
trailing newline). Required top-level fields (no unknown fields):

```
atlas_registry_version   "0.1.0"
registry_id              "project_witness_local_v1_registry"
components               [ {component_id, component_name, component_version,
                            component_type, frozen_status, description}, ... ]
workflow_types           [ {workflow_type, introduced_by_component, description,
                            allowed_statuses, known_limitations}, ... ]
action_types             [ {action_type, introduced_by_component, description,
                            known_limitations}, ... ]
statuses                 [ {status, status_group, meaning, truth_claim,
                            allowed_contexts}, ... ]
claim_predicates         [ {predicate, meaning, allowed_object_types, truth_claim,
                            introduced_by_component}, ... ]
case_record_types        [ {record_type, produced_by_component, required_files,
                            description}, ... ]
known_limitations        [ ... ]
```

Allowed `component_type`: ACTION_GATE, IMPORTER, BUNDLER, COORDINATOR, COMPANION,
EVIDENCE_BUNDLE, REASONER, BRIDGE, DEMO, REGISTRY, REVIEW_PACK. Allowed
`frozen_status`: FROZEN, DONE, IN_PROGRESS, NOT_STARTED.

Every `truth_claim` is a boolean and must be `false`. Truth-like status names
(`TRUE`, `PROVEN_TRUE`, `AUTHENTIC`, `VERIFIED_TRUE`, `SOURCE_TRUSTED`,
`REALITY_PROVEN`) and truth-like predicates (`contents.true`, `file.authentic`,
`source.trusted`, `statement.proven`, `reality.proven`) are refused. Out-of-roadmap
action types (`WRITE_FILE`, `DELETE_FILE`, `SHELL_COMMAND`, `NETWORK_CALL`) are
refused.

## verify (registry rules 1-23, summarised)

Registry file exists; loads as JSON; is canonical; required top-level fields present
with no unknowns; no duplicate component ids / workflow types / action types /
predicates / statuses-within-a-group; all ids safe; component versions are strings;
component_type and frozen_status are from the allowed sets; every status and
predicate `truth_claim` is `false`; no truth-like status names or predicates; and
all required current components, workflow types, action types, statuses, and
predicates are present. Verdict `REGISTRY_VERIFIED` only if every check passes;
otherwise one of `FAILED_SCHEMA_INVALID`, `FAILED_DUPLICATE_ENTRY`,
`FAILED_NON_CANONICAL_JSON`, `FAILED_TRUTH_CLAIM`.

## Export folder

`atlas.py export` writes exactly:

```
atlas_registry_copy.json   (byte-identical canonical registry)
atlas_summary.json         (counts + registry_status)
atlas_checksums.txt        (2 lines)
```

No unknown extra files.

### atlas_summary.json

```
atlas_registry_version   "0.1.0"
registry_id              "project_witness_local_v1_registry"
component_count          actual
workflow_type_count      actual
action_type_count        actual
status_count             actual
claim_predicate_count    actual
registry_status          "REGISTRY_VERIFIED"
known_limitations        [ ... ]
```

### atlas_checksums.txt

Exactly 2 lines, each `<sha256>  <relative-path>` (two spaces), lowercase digests:

```
<sha256>  atlas_registry_copy.json
<sha256>  atlas_summary.json
```

Required keys exactly once; duplicate / missing / unknown keys fail; malformed or
uppercase digests fail; hash mismatch fails.

## verify-export (export rules 1-8, summarised)

Required export files exist; no unknown extra files; registry copy and summary are
canonical JSON; checksums parse strictly (uppercase rejected) and recompute; the
registry copy re-verifies as a valid truth-free registry; the summary counts match
the registry copy and `registry_status = REGISTRY_VERIFIED`. Success only if every
check passes.
