# Atlas Release Gate v0.1

Atlas Release Gate v0.1 checks whether an Atlas Registry v0.1 release is
structurally complete, verified, documented, and truth-bounded. It does not
modify the registry, run workflows, or prove truth.

It is a deterministic, read-only release-gate checker. Given the path to an
Atlas Registry v0.1 release folder, it answers a single question:

> Is this Atlas Registry v0.1 release folder structurally complete,
> checksum-valid, documented, truth-bounded, and freeze-ready?

## What it is

Atlas Registry v0.1 already verifies the registry and its export. Atlas Release
Gate v0.1 sits one layer above: it confirms that a *release package* of the
registry is complete, reproducible, correctly documented, and honest about its
own boundaries before that package is frozen.

It does this by:

1. checking that the Atlas release folder contains the required files;
2. invoking Atlas registry verification (refusing the release if it fails);
3. invoking the Atlas export and Atlas export verification (refusing on failure);
4. checking that the release documentation, boundary statements, and honesty
   statements are present;
5. checking that the documentation makes no affirmative claim to any forbidden
   future feature;
6. writing a canonical release-gate report, an ordered step record, and a
   checksums file;
7. re-verifying its own output.

## What it does NOT do

- It does **not** modify the registry.
- It does **not** add registry terms.
- It does **not** run workflows.
- It does **not** prove truth.
- It does **not** connect Atlas to Coordinator.
- It does **not** connect Atlas to Companion.
- It does **not** sign or externally anchor the release.
- It is **not** the Atlas Red/Blue Pack. That work is not part of this version.

## Boundary statements

For the avoidance of doubt, stated plainly:

- Atlas Release Gate v0.1 does not modify the registry.
- Atlas Release Gate v0.1 does not run workflows.
- Atlas Release Gate v0.1 does not prove truth.
- Atlas Release Gate v0.1 does not connect Atlas to Coordinator or Companion.

## Honesty boundary

Atlas Release Gate v0.1 reports only structural facts: that the release
structure was verified, that the registry was verified, that the export was
verified, and that the documentation was checked. It never claims that registry
terms are true, that evidence is true, that claims are true, that files are
authentic, that sources are trusted, or that a case proves reality. The verifier
actively rejects any such truth-like claim found in its own output.

## Running it

Run the release gate against an Atlas Registry v0.1 release folder:

    python3 atlas_release_gate.py check \
      --atlas-root /path/to/atlas_registry_v01 \
      --out /path/to/atlas_release_gate_output

Verify a previously produced release-gate output folder:

    python3 atlas_release_gate.py verify \
      --run /path/to/atlas_release_gate_output

Run the in-process self-checks:

    python3 atlas_release_gate.py selfcheck

Or, equivalently:

    python3 selfcheck.py

## Release commands

The authoritative freeze gate is the explicit list of commands in
`RELEASE_COMMANDS.md`. Run each of them individually from a clean extraction.

## Component boundary

At runtime, `check` may call a frozen Atlas v0.1 via subprocess. The default
unit tests do **not** spawn subprocesses: they inject an in-process fake Atlas
runner. Real frozen-Atlas integration lives only in the documented manual smoke
test (see `RUN_FORMAT.md`) and is not part of the freeze gate.
