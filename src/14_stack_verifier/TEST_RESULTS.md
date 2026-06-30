# Test Results — Stack Verifier v0.1

Release artifact: `stack_verifier_v01.zip`
Version: 0.1.0

## Authoritative freeze gate (RELEASE_COMMANDS.md)

All commands were run from a clean extraction. All passed.

    python3 -m compileall -q .                               -> OK
    python3 -m unittest discover -s tests -v                 -> OK, 86 tests
    python3 -O -m unittest discover -s tests -v              -> OK, 86 tests
    python3 selfcheck.py                                     -> all 8 gates passed
    python3 -O selfcheck.py                                  -> all 8 gates passed
    python3 -W error::ResourceWarning -m unittest discover -s tests  -> OK, 86 tests
    sha256sum -c stack_verifier_v01.sha256                   -> OK (all files match)
    python3 verify_release_manifest.py                       -> OK (launched no subprocesses)

The `ResourceWarning` sweep was also run in verbose form
(`python3 -W error::ResourceWarning -m unittest discover -s tests -v`) and
completes with no unclosed-file warnings, following a test-fixture hygiene repair
that closed a leaked file handle in `tests/synthetic.py` (see REPAIR_LEDGER). No
Stack Verifier behaviour, schema, or freeze-gate command changed.

86 tests across thirteen files cover all 73 required scenarios: input validation;
source location and structural/checksum re-verification (missing root, missing
coordinator_output for a Companion source, missing workflow report/steps, Atlas
validation/registry, Case Bundle manifest, Bridge claims, ODIN report, and source
checksum mismatch); id matching; the full status rule set (workflow / Atlas
validation / registry / Sentinel / Aletheia / Bridge / ODIN / Case Bundle, with
ODIN CONSISTENT and CONTRADICTION_DETECTED accepted and INVALID_INPUT refused);
Atlas vocabulary membership / missing-predicate / truth-claim / forbidden-action
refusals; the optional Unified Case Manifest cross-check (valid accept, not-
provided accept, manifest checksum / case_id / evidence_id / status / artifact-hash
mismatches refused); the checked-artifact index (hashes recorded, relative-only
paths, unique ids/paths per label, MANIFEST_RUN/SOURCE_RUN labels, Companion path
prefixing); the strict two-key checksum manifest; the nine-step fixed order and
short-circuit; the full verifier rule set (mutation detection, unknown top-level
files, invalid stack/source/manifest status, invalid case_id/evidence_id, wrong
action type, all five boolean flags forced true, manifest_consistent required when
MANIFEST_VERIFIED, absolute and duplicate artifact paths/ids); the honesty
truth-scan (truth-like claims in report and steps refused, negated limitations
allowed); selfcheck; and the no-bare-assert / no-subprocess checks.

## Honesty boundary

The report records structural and vocabulary facts only. It does not prove that
evidence contents are true, that ODIN claims are true, or that any file or source
is authentic. The verifier rejects any truth-like claim in the report or steps.

## ATLAS_VALIDATED handling

`ATLAS_VALIDATED` is the Coordinator v0.3 validation result and is NOT a term in
the frozen Atlas Registry v0.1. The report records it as a fixed expected value and
confirms `REGISTRY_VERIFIED` (which IS an Atlas term). Every other observed status
is confirmed present in the copied Atlas registry.

## Cross-package integration check performed in this build

A genuine three-package chain was exercised end-to-end with no synthetic data:

1. A real Companion CLI v0.3 output was produced with the actual Companion package
   (engine + in-process fake Coordinator runner) -> COMPANION_COMPLETED.
2. The actual Unified Case Manifest v0.1 package built a manifest from that
   Companion output -> SOURCE_VERIFIED, verify_ok = true.
3. The Stack Verifier CLI checked the Companion source together with the Unified
   Manifest:
       check  -> stack_verification_status = STACK_VERIFIED,
                 source_status = SOURCE_VERIFIED, manifest_status = MANIFEST_VERIFIED,
                 manifest_consistent = true, 17 checked artifacts (15 SOURCE_RUN +
                 2 MANIFEST_RUN), all booleans true
       verify -> verify_ok = true

This exercised the full read and cross-check path against real (non-synthetic)
Companion and Unified Manifest outputs: source structure + checksums, id matching,
status and Atlas vocabulary checks, manifest structural verification and
ID/status/artifact-hash cross-check, truth-boundary scan, and self-verification.

## What was NOT tested

No end-to-end run was performed against a fully green real case produced by the
frozen lower components (Sentinel, Aletheia, ODIN, Bridge, Histor-lite, Case
Bundle), because those frozen components are not available in this build
environment. The default unit suite uses synthetic Coordinator/Companion source
outputs and a synthetic Unified Case Manifest output and spawns no subprocesses;
the cross-package check above used real Companion and Unified Manifest outputs
whose Coordinator layer came from the Companion package's in-process fake runner.
