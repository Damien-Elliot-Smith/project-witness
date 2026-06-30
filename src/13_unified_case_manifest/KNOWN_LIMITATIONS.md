# Known Limitations — Unified Case Manifest v0.1

- one source case output only
- does not run workflows
- does not call frozen components
- does not copy evidence contents
- does not prove truth
- does not verify external reality
- does not sign
- does not externally anchor
- does not merge cases
- does not provide search
- does not provide GUI
- does not use LLM
- original source folder is not required for manifest verification

## Scope

Unified Case Manifest v0.1 reads one existing Coordinator v0.3 or Companion v0.3
case output and writes one canonical manifest, one source artifact index, and one
manifest checksum file. It records relative artifact paths and SHA-256 hashes; it
never stores absolute source paths and never copies evidence contents.

At build time the source output is located, its required files are checked, and
the preserved Coordinator v0.3 output (and, for a Companion source, the Companion
output) is structurally re-verified from its own checksums. Manifest verification
(`verify`) checks the manifest package itself and does not require the original
source folder to still exist; re-verifying the source belongs to build time and to
future audit tooling.

## Honesty boundary

The manifest may record that the source was structurally verified at build time,
that IDs matched, that statuses were recorded, that artifacts were hashed, and that
the Atlas validation status was recorded. It must not, and does not, claim that
evidence is true, that ODIN claims are true, that a file is authentic, that a
source is trusted, or that a case proves reality. The verifier rejects any
truth-like claim found in the manifest or the source index.

## ATLAS_VALIDATED

`ATLAS_VALIDATED` is the Coordinator v0.3 validation result, not an Atlas Registry
v0.1 term. It is recorded and checked as a fixed expected value, not looked up in
the copied Atlas status vocabulary.
