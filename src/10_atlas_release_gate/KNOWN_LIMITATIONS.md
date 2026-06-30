# Known Limitations — Atlas Release Gate v0.1

Atlas Release Gate v0.1 is intentionally narrow. The following limitations are
explicit and by design.

- It checks Atlas Registry v0.1 only.
- It performs a release-structure check only.
- It does not modify the registry.
- It does not add registry terms.
- It does not run workflows.
- It does not connect Atlas to Coordinator.
- It does not connect Atlas to Companion.
- It does not prove truth.
- It does not verify external reality.
- It performs no natural-language interpretation.
- It uses no LLM.
- It performs no signing.
- It performs no external anchoring.
- It is not the Atlas Red/Blue Pack.

## Scope of the truth boundary

The gate proves structural facts only: that the release folder is complete, that
the registry and export verified, that documentation and honesty statements are
present, and that the documentation makes no forbidden affirmative claim. It does
not and cannot establish that any registry term, claim, evidence item, file, or
source corresponds to reality.

## Subprocess boundary

The default unit tests use an in-process fake Atlas runner and spawn no
subprocesses. The real frozen-Atlas subprocess integration is a manual,
best-effort adapter, documented in `RUN_FORMAT.md`, and is not part of the
freeze gate.
