# Known Limitations — Stack Verifier v0.1

- one source case output only
- optional one Unified Case Manifest output only
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
- original source folder is not required for stack verification output verification

## Scope

Stack Verifier v0.1 reads one existing Coordinator v0.3 or Companion v0.3 case
output and, optionally, one Unified Case Manifest v0.1 output. It writes one
canonical stack verification report, one verification steps file, and one
verification checksum file. It records checked artifact relative paths and SHA-256
hashes; it never stores absolute paths and never copies evidence contents.

At check time the source output is located, its required files are checked, and
the preserved Coordinator output (and, for a Companion source, the Companion
output) is structurally re-verified and checksum-verified. A provided Unified Case
Manifest is structurally verified and cross-checked for matching IDs, statuses,
and artifact hashes. Verification of the Stack Verifier output itself (`verify`)
checks the verifier package and does not require the original source or manifest
folders to still exist.

## Honesty boundary

The report records structural and vocabulary facts only. It does not, and the
verifier rejects any attempt to, claim that evidence is true, that ODIN claims are
true, that a file is authentic, that a source is trusted, or that a case proves
reality.

## ATLAS_VALIDATED

`ATLAS_VALIDATED` is the Coordinator v0.3 validation result, not an Atlas Registry
v0.1 term. It is recorded and checked as a fixed expected value, not looked up in
the copied Atlas status vocabulary.
