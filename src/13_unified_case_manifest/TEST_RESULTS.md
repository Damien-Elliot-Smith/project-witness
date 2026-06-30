# Test Results — Unified Case Manifest v0.1

Release artifact: `unified_case_manifest_v01.zip`
Version: 0.1.0

## Authoritative freeze gate (RELEASE_COMMANDS.md)

All commands were run from a clean extraction. All passed.

    python3 -m compileall -q .                               -> OK
    python3 -m unittest discover -s tests -v                 -> OK, 65 tests
    python3 -O -m unittest discover -s tests -v              -> OK, 65 tests
    python3 selfcheck.py                                     -> all 8 gates passed
    python3 -O selfcheck.py                                  -> all 8 gates passed
    python3 -W error::ResourceWarning -m unittest discover -s tests  -> OK, 65 tests
    sha256sum -c unified_case_manifest_v01.sha256            -> OK (all files match)
    python3 verify_release_manifest.py                       -> OK (launched no subprocesses)

65 tests across ten files cover all 55 required scenarios: input validation
(source-type, safe IDs, output dir, relative paths), source location and
structural re-verification (missing root, missing coordinator_output for a
Companion source, missing workflow/Atlas-validation/Atlas-registry/Case-Bundle
files), id matching, the full status rule set (workflow / Atlas validation /
registry / Sentinel / Aletheia / Bridge / ODIN / Case Bundle, including ODIN
CONSISTENT and CONTRADICTION_DETECTED accepted and INVALID_INPUT refused), Atlas
vocabulary membership / missing-predicate / truth-claim / forbidden-action
refusals, the artifact index (hashes recorded, relative-only paths, unique
ids/paths, Companion path prefixing), the strict two-key checksum manifest, the
full verifier rule set (mutation detection, unknown top-level files, invalid
source_status / case_id / evidence_id / workflow / action, absolute and duplicate
artifact paths/ids), the honesty truth-scan (truth-like claims and truth-claim
flags refused, negated limitations allowed), selfcheck, and the no-bare-assert /
no-subprocess checks.

## Honesty boundary

The manifest records structural and vocabulary facts only. It does not prove that
evidence contents are true, that ODIN claims are true, or that any file or source
is authentic. The verifier rejects any truth-like claim in the manifest or source
index, and rejects any copied truth-claim status/predicate flag.

## ATLAS_VALIDATED handling

`ATLAS_VALIDATED` is the Coordinator v0.3 validation result and is NOT a term in
the frozen Atlas Registry v0.1. The manifest records it as a fixed expected value
and confirms `REGISTRY_VERIFIED` (which IS an Atlas term). Every other observed
status — Companion (`COMPANION_COMPLETED`), Coordinator workflow
(`WORKFLOW_COMPLETED`), Sentinel, Aletheia, Bridge, ODIN, Case Bundle — is
confirmed present in the copied Atlas registry.

## Cross-package integration check performed in this build

A real Companion CLI v0.3 output was produced using the actual Companion CLI v0.3
package (its engine with the in-process fake Coordinator runner), yielding a
genuine `COMPANION_COMPLETED` output folder. The Unified Manifest CLI was then run
against it:

    unified_manifest.py build --source-type companion_v03_output --source-run <companion_out> --out <unified_out>
        -> source_status = SOURCE_VERIFIED, verify_ok = true, 15 source artifacts
    unified_manifest.py verify --run <unified_out>
        -> verify_ok = true

This exercised the full read path against a real (non-synthetic) Companion v0.3
output: structural re-verification of both the Companion and preserved Coordinator
outputs, id matching, status and Atlas vocabulary checks, artifact hashing, and
manifest self-verification. The derived case_id, mirrored statuses, and Atlas
fields all matched.

## What was NOT tested

No end-to-end run was performed against a fully green real case produced by the
frozen lower components (Sentinel, Aletheia, ODIN, Bridge, Histor-lite, Case
Bundle), because those frozen components are not available in this build
environment. The default unit suite uses synthetic Coordinator/Companion source
outputs and spawns no subprocesses; the cross-package check above used a real
Companion v0.3 output whose Coordinator layer was produced by the Companion
package's in-process fake Coordinator runner.
