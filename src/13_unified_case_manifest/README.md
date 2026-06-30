# Unified Case Manifest v0.1

Unified Case Manifest v0.1 summarizes one existing Project Witness case output
into a canonical manifest of IDs, statuses, artifacts, hashes, Atlas validation
fields, and known limitations. It does not run workflows, copy evidence contents,
or prove truth.

## What it is

Unified Case Manifest v0.1 is a standalone, read-only summariser. It reads
existing Coordinator v0.3 or Companion v0.3 outputs that were already produced and
verified, and writes one canonical top-level manifest describing the case. It is
standard-library only.

It does not run workflows. It does not call Sentinel, Aletheia, ODIN, Histor-lite,
the Bridge, Case Bundle, Coordinator, Companion, or Atlas. It does not modify the
source output, and it does not copy evidence contents. It records relative
artifact paths and hashes only — never absolute paths and never the evidence
bytes themselves. It does not prove truth: it records that the source was
structurally verified at build time, that case and evidence IDs matched, that
statuses were recorded, that artifacts were hashed, and that the Atlas validation
status was recorded. It never asserts that evidence is true, that ODIN claims are
true, that a file is authentic, that a source is trusted, or that a case proves
reality.

For a Companion v0.3 source, the builder reads the preserved Coordinator output at
`coordinator_output/`. For a Coordinator v0.3 source, it reads the Coordinator
output directly.

## How to build a manifest

    python3 unified_manifest.py build \
      --source-type coordinator_v03_output \
      --source-run /path/to/coordinator_v03_output \
      --out /path/to/unified_manifest_output

    python3 unified_manifest.py build \
      --source-type companion_v03_output \
      --source-run /path/to/companion_v03_output \
      --out /path/to/unified_manifest_output

## How to verify a manifest

    python3 unified_manifest.py verify --run /path/to/unified_manifest_output

Verifying the manifest package does not require the original source folder to
still exist.

## How to selfcheck

    python3 unified_manifest.py selfcheck

## Optional: summary (read-only)

    python3 unified_manifest.py summary --run /path/to/unified_manifest_output

`summary` prints only fixed fields from `unified_case_manifest.json`. It does not
infer, explain evidence contents, or use an LLM.

## How to run the release commands

The authoritative freeze gate is the explicit list in `RELEASE_COMMANDS.md`. Run
each command individually from a clean extraction.

## Boundaries

- Unified Case Manifest v0.1 reads existing Coordinator v0.3 or Companion v0.3 outputs.
- It does not run workflows.
- It does not copy evidence contents.
- It records relative artifact paths and hashes.
- It does not prove truth.

## A note on ATLAS_VALIDATED

`ATLAS_VALIDATED` is the Coordinator v0.3 Atlas-validation result, not an Atlas
Registry v0.1 vocabulary term. The manifest records `atlas_validation_status` as a
fixed expected value (`ATLAS_VALIDATED`) and confirms `REGISTRY_VERIFIED`, but it
does not look `ATLAS_VALIDATED` up in the copied Atlas status vocabulary, because
the frozen Atlas Registry v0.1 does not contain it. Every other observed status is
confirmed present in the copied Atlas registry.
