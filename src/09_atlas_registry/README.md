# Atlas Registry v0.1

Atlas Registry v0.1 is the dictionary for **Project Witness**. It is a **read-only**
registry that records the canonical vocabulary the stack already uses — components
and their versions, workflow types, action types, the status vocabulary, claim
predicates, and case record types — so later components can stop hard-coding these
terms and refer to one source instead.

Atlas Registry v0.1 records Project Witness vocabulary and component metadata. It does not run workflows, does not prove truth, and is not connected to Coordinator or Companion yet.

It is the first Atlas Registry build.

## What it records

- **components** — the 15 Project Witness components up to Move 21, each with id,
  name, version, type, frozen status, and description.
- **workflow_types** — `CREATE_CASE_DIRECTORY` and `CREATE_EVIDENCE_REASONING_CASE`.
- **action_types** — `CREATE_DIRECTORY` (the only roadmap action for v0.1).
- **statuses** — the status vocabulary across Sentinel, Aletheia, ODIN, the Bridge,
  the Histor importers, Case Bundle, Coordinator, Companion, workflow steps, and
  verification. Every status carries `truth_claim: false`.
- **claim_predicates** — `evidence.present` and `evidence.integrity_verified`, both
  `truth_claim: false`.
- **case_record_types** — sentinel_case, aletheia_case, odin_case, case_bundle_v02,
  coordinator_output, companion_output.

## What it does NOT do

- It is **read-only**: it **does not run workflows** and does not call any component.
- It **does not prove truth** and does not verify external reality.
- It does not decide truth, does not replace Coordinator, and does not replace
  Companion.
- It is **not connected to Coordinator** yet and **not connected to Companion** yet.
- No natural language, no LLM, no signing, no external anchoring, no queue, no
  concurrency.

Atlas refuses any status or predicate that claims truth: a `truth_claim: true`
entry, a truth-like status name (e.g. `PROVEN_TRUE`, `AUTHENTIC`), or a truth-like
predicate (e.g. `contents.true`, `source.trusted`) makes verification fail with
`FAILED_TRUTH_CLAIM`. It also refuses out-of-roadmap action types (`WRITE_FILE`,
`DELETE_FILE`, `SHELL_COMMAND`, `NETWORK_CALL`).

## Registry file

`registry/atlas_registry.json` is deterministic canonical JSON with strict schema:
required top-level fields only, no unknown fields, no duplicate ids, no duplicate
names within a section, safe ids only, explicit version strings only.

## Usage

Verify the registry:

```
python3 atlas.py verify --registry registry/atlas_registry.json
```

Export a portable registry summary:

```
python3 atlas.py export --registry registry/atlas_registry.json --out /tmp/atlas_export
```

Verify an export folder:

```
python3 atlas.py verify-export --export /tmp/atlas_export
```

List a section (entries only; no inference):

```
python3 atlas.py list --registry registry/atlas_registry.json --section statuses
```

Run the in-process self-check:

```
python3 atlas.py selfcheck
# or
python3 selfcheck.py
```

## Export output

`atlas.py export` writes exactly `atlas_registry_copy.json`, `atlas_summary.json`,
and `atlas_checksums.txt`. The summary records the actual counts and
`registry_status = REGISTRY_VERIFIED`. See `RUN_FORMAT.md` for the fields and the
2-line export checksums.

## Release commands

The authoritative freeze gate is the explicit list of individual commands in
`RELEASE_COMMANDS.md` (run each from a clean extraction). There is no subprocess
orchestrator in the gate; `verify_release_manifest.py` is a static checker that
launches no subprocesses.

Standard library only.
