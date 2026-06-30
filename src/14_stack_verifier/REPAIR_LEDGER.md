# Repair Ledger — Stack Verifier v0.1

## Build 0.1.0 — first Stack Verifier build

This is the first Stack Verifier build. It reads an already-produced Project
Witness case output (Coordinator v0.3 or Companion v0.3) and, optionally, its
Unified Case Manifest v0.1 output, and writes one canonical stack verification
report plus verification steps and checksums.

### Design decisions

- **Read-only and standalone.** The verifier never runs workflows and never calls
  Sentinel, Aletheia, ODIN, Histor-lite, the Bridge, Case Bundle, Coordinator,
  Companion, Atlas, or Unified Manifest. It only reads existing files and writes a
  new report package. It never modifies the source and never copies evidence
  contents.
- **Structure, checksums, IDs, statuses, Atlas, manifest, truth.** The check
  verifies source structure and checksums, confirms case/evidence IDs match across
  records, validates the component statuses, confirms the workflow type, action
  type, required statuses, and predicates exist in the copied Atlas registry with
  no truth-claim or forbidden-action terms, cross-checks an optional Unified Case
  Manifest, scans for truth-like claims, and finally self-verifies its own output.
- **Relative paths and hashes only.** `checked_artifacts` records relative paths
  (under `SOURCE_RUN` or `MANIFEST_RUN`) and lowercase SHA-256 hashes. Absolute
  paths are never stored.
- **ATLAS_VALIDATED handled honestly.** `ATLAS_VALIDATED` is the Coordinator v0.3
  validation result, not an Atlas Registry v0.1 term. The frozen Atlas registry
  does not contain it, so it is recorded and checked as a fixed expected value, and
  `REGISTRY_VERIFIED` (which IS an Atlas term) is confirmed. Every other observed
  status is confirmed present in the copied Atlas registry.
- **Standard-library only, no subprocess.** There is no subprocess anywhere in
  this component; the freeze gate is fully in-process. Default unit tests and
  selfcheck use synthetic Coordinator/Companion source outputs and a synthetic
  Unified Case Manifest output, requiring no real frozen components.

### Honesty boundary

The report records structural and vocabulary facts only. It does not prove that
evidence contents are true, that ODIN claims are true, or that any file or source
is authentic. The verifier rejects truth-like claims in the report or steps.

### Repairs

One correction during construction: the shared canonical module (carried over from
the Unified Case Manifest layout) was missing the `is_atlas_canonical_bytes`
helper used by the source structural verifier to confirm the Atlas registry copy
keeps its trailing-newline canonical form; the helper was added. No behavioural
logic changed.

### Release-hygiene repair (post-freeze, behaviour unchanged)

A `ResourceWarning` sweep (`python3 -W error::ResourceWarning -m unittest discover
-s tests -v`) surfaced one unclosed-file leak in the test fixture
`tests/synthetic.py`: the optional `case_id` resolution in
`build_unified_manifest_output` read `workflow_report.json` via
`json.loads(open(...).read().decode())`, which never closed the file object. It was
replaced with a `with open(...) as f:` block so the handle is closed. This is a
test-fixture hygiene fix only: no Stack Verifier behaviour, schema, CLI, library
module, or freeze-gate command changed, and no subprocess was added. After the fix
the full gate — including the `-v` ResourceWarning sweep — completes with no
unclosed-file warnings. The internal manifest (`stack_verifier_v01.sha256`) was
regenerated to reflect the edited fixture.

### Scope

Existing Coordinator/Companion case output + optional Unified Case Manifest output
-> canonical stack verification report -> verification steps -> verification
checksums -> stack verifier output verification. Nothing else.
