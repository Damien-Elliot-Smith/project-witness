# Handoff Notes

Scope and boundary notes for anyone receiving this package.

## What this package is

This is the **runnable working stack** of Project Witness: the current latest
version of each component, plus the frozen verification artifacts and the scripts
to run them. It is meant to be extracted and run as-is.

## Relationship to the archive

`MOVE_INDEX.md` indexes the whole stack across roadmap moves 1–51. Some of those
moves point at items that live in a **separate** historical archive
(`Project_Witness_ARCHIVE`), not in this zip — for example superseded component
versions, red/blue adversarial packs, review/documentation packs, the hardening
rounds, and the large review bundles. If the archive was not delivered alongside
this zip, those `MOVE_INDEX.md` entries will refer to items you do not have
locally. That is expected; nothing in this zip depends on the archive to run.

## Component-local documentation

Each component carries its own README and a `_frozen/` folder containing the
original frozen zip, checksum sidecar, and that component's TEST_RESULTS /
REPAIR_LEDGER. Those component-local documents describe the **freeze-time state**
of that specific component and were written when it was frozen. They are accurate
for that component but are not the overall stack index.

## Authoritative index

`MOVE_INDEX.md` is the current overall stack index. Where a component-local
document and `MOVE_INDEX.md` appear to differ in scope, `MOVE_INDEX.md` describes
the assembled stack; the component doc describes that one component at its freeze.

## Roadmap status — read carefully

- The roadmap is complete **through Move 51** (Build Termux Run Instructions).
- Moves **52–70 remain future work** and are not present or verified here, unless
  a specific later move has been explicitly added and independently verified in a
  future package.
- Do **not** describe "Roadmap One" / the 70-step roadmap as complete.
- This is a Local v1 **Candidate**, not a final Local v1 **Release**.

## Honesty boundary

This stack verifies structured provenance relationships under tested local
conditions. It does not prove external truth, authenticate real-world identity,
establish source trust, sign outputs, or externally anchor outputs. It is not
production-ready. Treat every PASS marker as "the structural checks held under
local test conditions," nothing more.

## Licence

No licence has been chosen yet. See `LICENSE_DECISION_NEEDED.md`. Public release
requires an explicit licensing decision first.
