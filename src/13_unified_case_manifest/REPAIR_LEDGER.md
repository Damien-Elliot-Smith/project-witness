# Repair Ledger — Unified Case Manifest v0.1

## Build 0.1.0 — first Unified Case Manifest build

This is the first Unified Case Manifest build. It reads an already-produced
Project Witness case output (Coordinator v0.3 or Companion v0.3) and writes one
canonical top-level manifest summarising the case: IDs, statuses, source artifacts
with SHA-256 hashes, Atlas validation fields, component versions, and known
limitations.

### Design decisions

- **Read-only and standalone.** The builder never runs workflows and never calls
  Sentinel, Aletheia, ODIN, Histor-lite, the Bridge, Case Bundle, Coordinator,
  Companion, or Atlas. It only reads existing files and writes a new manifest
  package. It never modifies the source and never copies evidence contents.
- **Relative paths and hashes only.** `source_artifacts` records relative paths
  (relative to the source root, recorded as `SOURCE_ROOT`) and lowercase SHA-256
  hashes. Absolute source paths are never stored in the manifest.
- **Source verified at build, package verified at verify.** At build time the
  source is structurally re-verified from its own checksums (Coordinator output
  always; Companion output too for a Companion source). `verify` checks the
  manifest package itself and does not need the original source folder to still
  exist.
- **ATLAS_VALIDATED handled honestly.** `ATLAS_VALIDATED` is the Coordinator v0.3
  validation result, not an Atlas Registry v0.1 term. The frozen Atlas registry
  does not contain it, so it is recorded and checked as a fixed expected value,
  and `REGISTRY_VERIFIED` (which IS an Atlas term) is confirmed. Every other
  observed status (Coordinator workflow, Companion, Sentinel, Aletheia, Bridge,
  ODIN, Case Bundle) is confirmed present in the copied Atlas registry.
- **Standard-library only, no subprocess.** There is no subprocess anywhere in
  this component; the freeze gate is fully in-process. Default unit tests and
  selfcheck use synthetic source outputs and require no real frozen components.

### Honesty boundary

The manifest records structural and vocabulary facts only. It does not prove that
evidence contents are true, that ODIN claims are true, or that any file or source
is authentic. The verifier rejects truth-like claims in the manifest or source
index, and rejects any copied truth-claim status or predicate flag.

### Repairs

No behavioural self-fixes were required during construction. The build, selfcheck,
and full unit suite passed on first integrated run after the modules were
assembled.

### Scope

Existing Coordinator/Companion case output -> canonical unified case manifest ->
source artifact index -> manifest checksums -> manifest verification. Nothing else.
