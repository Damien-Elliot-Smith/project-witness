# Test results — Atlas Registry v0.1

Atlas Registry v0.1 is a read-only registry of Project Witness vocabulary and
component metadata. Standard library only. It runs no workflows, calls no
components, and decides no truth. All commands below were run from a **clean
extraction** of `atlas_registry_v01.zip`.

## Authoritative freeze gate — each command passes individually (clean extraction)

The freeze gate is the explicit list of individual commands (see
RELEASE_COMMANDS.md) plus the static manifest check. No subprocess orchestrator is
in the gate; the whole suite and selfcheck run in process and spawn no subprocesses.

| Command | Result |
|---------|--------|
| `python3 -m compileall -q .` | PASS |
| `python3 -m unittest discover -s tests -v` | PASS — 63 tests |
| `python3 -O -m unittest discover -s tests -v` | PASS — 63 tests |
| `python3 selfcheck.py` | PASS — 8/8 gates |
| `python3 -O selfcheck.py` | PASS — 8/8 gates |
| `python3 -W error::ResourceWarning -m unittest discover -s tests` | PASS |
| `python3 atlas.py verify --registry registry/atlas_registry.json` | REGISTRY_VERIFIED |
| `sha256sum -c atlas_registry_v01.sha256` | OK |
| `python3 verify_release_manifest.py` | PASS — 11/11 static checks, **no subprocesses** |

## Required behaviours (spec tests 1–42, all covered)

Registry schema (1–5): a valid registry verifies; a missing file, non-canonical
JSON, a missing top-level field, and an extra top-level field are all refused.

Sections (6–25): duplicate component id / workflow type / action type /
status-within-group / predicate are refused; unsafe component id / workflow type /
action type are refused; invalid component_type and frozen_status are refused;
missing required component / workflow type / action type / predicate are refused;
`truth_claim: true` on a status and on a predicate are refused; truth-like status
names and truth-like predicates are refused; the required current statuses and
predicates are present.

Export (26–37): export writes the three required files; summary counts match the
registry; checksums are written; a valid export verifies; mutated registry copy and
mutated summary fail; missing / duplicate / unknown / malformed / uppercase checksum
cases fail; an unknown extra export file fails.

Honesty + discipline (38–42): README disclaimers present; `python -O` does not
change behaviour; selfcheck passes; no bare runtime asserts in runtime modules;
`verify_release_manifest.py` passes and is AST-verified to launch no subprocesses.

Additional coverage: bad registry version refused; component version-not-string
refused; the same status name allowed in two different groups; truth_claim-not-bool
refused; forbidden action types (WRITE_FILE / DELETE_FILE / SHELL_COMMAND /
NETWORK_CALL) refused; export count mismatch refused; non-empty export output dir
refused; the shipped registry's statuses and predicates all carry
`truth_claim: false`.

## Registry contents

`registry/atlas_registry.json` verifies to `REGISTRY_VERIFIED` with 15 components,
2 workflow types, 1 action type, 19 statuses, 2 claim predicates, and 6 case record
types.

## Repairs recorded this build

Clean first build — no behavioural self-fixes were required. The only initial
failures were the expected documentation-dependent tests (README disclaimers, the
RELEASE_COMMANDS list, and the manifest-verifier presence check), which cleared once
the docs were written. See REPAIR_LEDGER.md.

## Manual smoke test (NOT part of the freeze gate)

```
python3 atlas.py verify --registry registry/atlas_registry.json   -> REGISTRY_VERIFIED
python3 atlas.py export --registry registry/atlas_registry.json --out /tmp/atlas_export
python3 atlas.py verify-export --export /tmp/atlas_export          -> Export verified
```

Export writes `atlas_registry_copy.json`, `atlas_summary.json`, and
`atlas_checksums.txt`; verify-export passes.

## Scope

canonical registry -> registry verification -> registry export -> export
verification. Nothing else. No Coordinator or Companion integration, no LLM, no
natural language, no signing, no anchoring.
