# Companion CLI v0.3.1 — Test Results

## 1. Freeze gate (clean extraction, in-process, no subprocess)

All eight gate commands pass from a clean extraction of `companion_cli_v031/`:

    python3 -m compileall -q .                                      -> OK
    python3 -m unittest discover -s tests -v                        -> OK
    python3 -O -m unittest discover -s tests -v                     -> OK
    python3 selfcheck.py                                            -> all gates passed
    python3 -O selfcheck.py                                         -> all gates passed
    python3 -W error::ResourceWarning -m unittest discover -s tests -> OK
    sha256sum -c companion_cli_v031.sha256                          -> OK
    python3 verify_release_manifest.py                              -> OK (launched no subprocesses)

`tests/test_request_hygiene.py` (7 tests) drives the real `run()`/`verify()`
hygiene path with an in-process Coordinator stub (no subprocess), asserting:
no `_coordinator_request.json` at top level; the request is written outside the
output and cleaned up; Companion verify passes after a real Coordinator
completion; only allowed top-level entries remain; unknown top-level files are
still refused.

## 2. Real smoke test — Companion v0.3.1 vs frozen Coordinator v0.3.1

Run against frozen Coordinator Workflow v0.3.1 and the real frozen lower
components (Sentinel Core v0.2.2, Histor-lite v0.1.2 + importers, Aletheia
Evidence Bundle v0.1, Aletheia->ODIN Bridge v0.1, ODIN Claim Reasoner v0.1,
Case Bundle v0.2):

    python3 companion.py create-evidence-case ... --coordinator-root <v031> ... --out OUT
      -> {"companion_status": "COMPANION_COMPLETED", "out": "OUT"}
    python3 companion.py verify --run OUT
      -> {"companion_status": "COMPANION_COMPLETED", "reason": "companion completed",
          "verify_ok": true}

Mirrored statuses (all required values met):

    companion_status            = COMPANION_COMPLETED
    coordinator_workflow_status = WORKFLOW_COMPLETED
    atlas_validation_status     = ATLAS_VALIDATED
    atlas_registry_status       = REGISTRY_VERIFIED
    sentinel_status             = PASS_STRICT
    aletheia_status             = VERIFIED_PRESENT
    bridge_status               = CONVERTED
    odin_reasoning_status       = CONSISTENT
    case_bundle_status          = BUNDLED_VERIFIED_CASE
    companion_cli_version       = 0.3.0   (schema unchanged)

Final Companion output top level (no stray file):

    workflow_request.json  companion_report.json  companion_steps.json
    companion_checksums.txt  coordinator_output/

**The Companion blocker is repaired.** `companion verify` passes; the stray
`_coordinator_request.json` is gone.

## 3. Downstream compatibility — Unified Manifest exposes a SEPARATE blocker

Required proof against Unified Case Manifest v0.1 / Stack Verifier v0.1 /
Stack Selfcheck v0.1, run on the repaired Companion output:

    unified_manifest.py build --source-type companion_v03_output --source-run OUT --out UM
      -> {"source_status": "FAILED_EVIDENCE_ID_MISMATCH",
          "error": "evidence_id mismatch across records"}
    stack_verify.py check --source-type companion_v03_output --source-run OUT ... 
      -> {"stack_verification_status": "FAILED_EVIDENCE_ID_MISMATCH",
          "error": "evidence_id mismatch"}

### Exact cause (NOT Companion, NOT this repair)

Unified Case Manifest v0.1 `_check_ids` requires `evidence_id` to be present and
equal across records, including `coordinator_output/case_bundle_v02/case_manifest.json`:

    evidence_ids = [coordinator_report.evidence_id, case_manifest.evidence_id,
                    companion_report.evidence_id, workflow_request.evidence_id]
    if any(e != evidence_id ...) or not evidence_id: raise FAILED_EVIDENCE_ID_MISMATCH

Every record carries `evidence_id = evidence_demo_001` EXCEPT
`case_bundle_v02/case_manifest.json`, where it is absent. The **real Case Bundle
v0.2** manifest records `case_id` + `bundle_status` but no `evidence_id`; only the
old in-process fake runner injected one. Coordinator v0.3.1 (frozen) emits the raw
Case Bundle manifest unchanged, so the field is genuinely missing.

This is a distinct blocker in the Coordinator output / Case Bundle manifest, not
in Companion. The Companion output is otherwise fully compatible (its own verify
passes; every Companion-owned record carries the right `evidence_id`). Per the
Move 30 brief, this repair must not modify Coordinator v0.3.1, Case Bundle, or
Unified Manifest, so it is reported exactly rather than worked around or faked.

## 4. Consequence for Move 30

- Companion blocker: **REPAIRED.** Real run reaches COMPANION_COMPLETED and verifies.
- End-to-end Connected Demo to `DEMO_COMPLETED` / `STACK_VERIFIED` /
  `STACK_SELFCHECK_PASSED`: **still blocked**, now at the Unified Manifest step on
  the missing `evidence_id` in the real Case Bundle manifest — a distinct
  component, out of scope for this Companion repair.

### Suggested next repair (out of scope here)

A Coordinator Workflow v0.3.2 that, in its `case_bundle_build` step, writes a
coordinator summary `case_bundle_v02/case_manifest.json` carrying `evidence_id`
(and `case_id` + `bundle_status`) beside the raw Case Bundle output — the same
pattern v0.3.1 already uses for `sentinel_run/run_report.json` — would satisfy
Unified Manifest `_check_ids` without modifying any frozen lower component.
