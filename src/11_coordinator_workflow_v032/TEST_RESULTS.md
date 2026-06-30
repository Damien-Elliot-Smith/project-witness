# Coordinator Workflow v0.3.2 — Test Results

## 1. Freeze gate (clean extraction, in-process, no subprocess)

All eight gate commands pass from a clean extraction of `coordinator_workflow_v032/`:

    python3 -m compileall -q .                                      -> OK
    python3 -m unittest discover -s tests -v                        -> OK (82 tests)
    python3 -O -m unittest discover -s tests -v                     -> OK (82 tests)
    python3 selfcheck.py                                            -> all 8 gates passed
    python3 -O selfcheck.py                                         -> all 8 gates passed
    python3 -W error::ResourceWarning -m unittest discover -s tests -> OK
    sha256sum -c coordinator_workflow_v032.sha256                   -> OK
    python3 verify_release_manifest.py                              -> OK (launched no subprocesses)

New tests in `tests/test_real_runner.py` (20 tests total): the compatibility
summary includes evidence_id; it is labelled `coordinator_compatibility_summary`
with `raw_case_bundle_manifest_preserved`; the raw Case Bundle manifest is
preserved without evidence_id; the summary is only written after a real
BUNDLED_VERIFIED_CASE (otherwise the step fails closed and writes nothing).

## 2. Smoke test 1 — Coordinator v0.3.2 vs real frozen lower components

    python3 coordinator_v03.py run    --request ... --out OUT  -> WORKFLOW_COMPLETED
    python3 coordinator_v03.py verify --run OUT                -> verify_ok: true

    workflow_status            = WORKFLOW_COMPLETED
    atlas_validation_status    = ATLAS_VALIDATED
    atlas_registry_status      = REGISTRY_VERIFIED
    sentinel_status            = PASS_STRICT
    aletheia_status            = VERIFIED_PRESENT
    bridge_status              = CONVERTED
    odin_reasoning_status      = CONSISTENT
    case_bundle_status         = BUNDLED_VERIFIED_CASE
    coordinator_workflow_version = 0.3.0   (schema unchanged)

`case_bundle_v02/` now contains both `case_manifest.json` (the labelled
compatibility summary, with `evidence_id`) and `raw_case_bundle_manifest.json`
(the preserved raw Case Bundle manifest, without `evidence_id`).

## 3. Smoke test 2 — Companion v0.3.1 vs Coordinator v0.3.2

    companion.py create-evidence-case ... --coordinator-root <v032> ... --out OUT
      -> companion_status = COMPANION_COMPLETED
    companion.py verify --run OUT
      -> companion_status = COMPANION_COMPLETED, verify_ok: true
    coordinator_workflow_status = WORKFLOW_COMPLETED

## 4. Smoke test 3 — downstream tools on the repaired Companion output

    unified_manifest.py build --source-type companion_v03_output --source-run OUT --out UM
      -> source_status = SOURCE_VERIFIED, verify_ok: true
    unified_manifest.py verify --run UM
      -> SOURCE_VERIFIED, verify_ok: true
    stack_verify.py check --source-type companion_v03_output --source-run OUT --manifest-run UM --out SV
      -> stack_verification_status = STACK_VERIFIED, source_status = SOURCE_VERIFIED,
         manifest_status = MANIFEST_VERIFIED, verify_ok: true
    stack_verify.py verify --run SV
      -> STACK_VERIFIED, verify_ok: true

**The evidence_id mismatch is RESOLVED.** Unified Manifest and Stack Verifier both
accept the repaired output and reach SOURCE_VERIFIED / STACK_VERIFIED.

### Stack Selfcheck v0.1 — blocked by a SEPARATE, distinct issue

    stack_selfcheck.py check --inventory <real 22-component inventory>
        --stack-verifier-run SV --out SS
      -> {"stack_selfcheck_status": "FAILED_DOCUMENTATION_BOUNDARY",
          "error": "sentinel_core_v022 missing KNOWN_LIMITATIONS.md"}

Cause (NOT evidence_id, NOT this repair): Stack Selfcheck v0.1 requires every
component listed in its frozen `REQUIRED_COMPONENT_IDS` to carry README.md +
KNOWN_LIMITATIONS.md + RELEASE_COMMANDS.md in its root. Four early frozen
components predate that convention:

    sentinel_core_v022          (no KNOWN_LIMITATIONS.md, no RELEASE_COMMANDS.md)
    histor_lite_v012            (no RELEASE_COMMANDS.md)
    case_bundle_v011            (no RELEASE_COMMANDS.md)
    atlas_red_blue_pack_v01     (no KNOWN_LIMITATIONS.md, no RELEASE_COMMANDS.md)

This is independent of the Coordinator and of evidence_id; it cannot be addressed
without modifying Stack Selfcheck v0.1 or those frozen components, all of which
are out of scope for this repair. It is reported exactly, not worked around.

## 5. Consequence for Move 30

- evidence_id blocker: **REPAIRED.** Unified Manifest = SOURCE_VERIFIED, Stack
  Verifier = STACK_VERIFIED, both verify_ok.
- End-to-end Connected Demo to `DEMO_COMPLETED` / `STACK_SELFCHECK_PASSED`:
  **still blocked**, now at Stack Selfcheck on the documentation-boundary gap in
  four early frozen components — a distinct issue, out of scope here.

### Suggested next repair (out of scope here)

A Stack Selfcheck v0.1.1 that tolerates components frozen before the
README/KNOWN_LIMITATIONS/RELEASE_COMMANDS documentation convention (e.g. an
inventory flag marking a component's available doc set), OR adding the missing
doc files to those four components, would let the demo reach
STACK_SELFCHECK_PASSED.
