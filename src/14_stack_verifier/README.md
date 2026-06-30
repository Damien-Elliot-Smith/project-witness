# Stack Verifier v0.1

Stack Verifier v0.1 verifies one existing Project Witness case output, optionally
cross-checks its Unified Case Manifest, and writes a canonical verification
report. It does not run workflows, copy evidence contents, or prove truth.

## What it is

Stack Verifier v0.1 is a standalone, read-only verifier. It reads existing
Coordinator v0.3 or Companion v0.3 outputs and can cross-check a Unified Case
Manifest v0.1 output. It confirms that the case output is structurally consistent,
checksum-valid, Atlas-bounded, and truth-bounded — without running the workflow.
It is standard-library only.

It does not run workflows. It does not call Sentinel, Aletheia, ODIN, Histor-lite,
the Bridge, Case Bundle, Coordinator, Companion, Atlas, or Unified Manifest. It
does not modify the source output, and it does not copy evidence contents. It
records checked artifact paths and hashes only — relative paths, never absolute,
and never the evidence bytes. It does not prove truth: it records that the source
and manifest were structurally verified, that IDs matched, that statuses were
consistent, that artifact hashes were checked, and that the Atlas and truth
boundaries were checked. It never asserts that evidence is true, that ODIN claims
are true, that a file is authentic, that a source is trusted, or that a case
proves reality.

For a Companion v0.3 source, the verifier reads the preserved Coordinator output
at `coordinator_output/`. For a Coordinator v0.3 source, it reads the Coordinator
output directly. The `--manifest-run` path is optional; if provided it is verified
and cross-checked.

## How to run check

    python3 stack_verify.py check \
      --source-type companion_v03_output \
      --source-run /path/to/companion_v03_output \
      --manifest-run /path/to/unified_manifest_output \
      --out /path/to/stack_verifier_output

Coordinator source is also supported with `--source-type coordinator_v03_output`.
`--manifest-run` may be omitted.

## How to run verify

    python3 stack_verify.py verify --run /path/to/stack_verifier_output

Verifying the Stack Verifier output does not require the original source or
manifest folders to still exist.

## How to selfcheck

    python3 stack_verify.py selfcheck

## Optional: summary (read-only)

    python3 stack_verify.py summary --run /path/to/stack_verifier_output

`summary` prints only fixed fields from `stack_verification_report.json`. It does
not infer evidence contents, explain claims, or use an LLM.

## How to run the release commands

The authoritative freeze gate is the explicit list in `RELEASE_COMMANDS.md`. Run
each command individually from a clean extraction.

## Boundaries

- Stack Verifier v0.1 reads existing Coordinator v0.3 or Companion v0.3 outputs.
- It can cross-check Unified Case Manifest v0.1 output.
- It does not run workflows.
- It does not copy evidence contents.
- It records checked artifact paths and hashes.
- It does not prove truth.

## A note on ATLAS_VALIDATED

`ATLAS_VALIDATED` is the Coordinator v0.3 Atlas-validation result, not an Atlas
Registry v0.1 vocabulary term. The report records `atlas_validation_status` as a
fixed expected value and confirms `REGISTRY_VERIFIED`, but it does not look
`ATLAS_VALIDATED` up in the copied Atlas status vocabulary, because the frozen
Atlas Registry v0.1 does not contain it. Every other observed status is confirmed
present in the copied Atlas registry.
