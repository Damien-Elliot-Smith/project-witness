# Stack Status — Verification Record

Date verified: 2026-06-29
Environment: standard library only, no network, stdlib `unittest` runner.

> **v02 handoff hardening (2026-06-29):** the top-level `tools/run_all_tests.sh`
> wrapper was repaired (pass/fail now read from unittest exit codes, not text
> parsing; no `tail -3` dependency; missing test-count parsing no longer crashes
> it). Wrapper verifier scripts and a top-level `tools/validate_handoff.sh` were
> added. No component behaviour, schema, or architecture was changed. All results
> below were re-confirmed after the repair. See `CHANGELOG_REPAIR_v02.md`.

> **Move 52 — Linux desktop run instructions (2026-06-29):** added
> `LINUX_DESKTOP_RUN_INSTRUCTIONS.md` and `tools/check_linux_desktop_instructions.sh`.
> The instruction check passes (`LINUX_DESKTOP_INSTRUCTIONS_CHECK: PASS`) and the
> existing `validate_handoff.sh` still passes (`HANDOFF_VALIDATION: PASS`). No
> component behaviour, schema, or architecture changed; no roadmap features added.
> Roadmap complete through Move 52; Moves 53–70 remain future work. See
> `CHANGELOG_MOVE_52.md`.

> **Move 53 — Windows notes (2026-06-29):** added `WINDOWS_NOTES.md` and
> `tools/check_windows_notes.sh`. The Windows notes check passes
> (`WINDOWS_NOTES_CHECK: PASS`); the Move 52 Linux check and the existing
> `validate_handoff.sh` still pass. Native Windows execution has **not** been
> directly tested — the notes recommend WSL2 + Ubuntu and do not claim native
> support. No component behaviour, schema, or architecture changed; no roadmap
> features added; Step 54 not started. Roadmap complete through Move 53; Moves
> 54–70 remain future work. See `CHANGELOG_MOVE_53.md`.

This record states only what was actually run and observed. No result is implied
or carried over from documentation; every line below was reproduced directly
against the code in `src/`.

---

## 1. Component test suites — PASS (18/18, 1,234 tests)

Each component's own `tests/` suite, run via `python3 -m unittest`:

| Component | Tests | Result |
|---|---:|---|
| 01_sentinel_core | 144 | OK |
| 02_histor_lite | 37 | OK |
| 03_aletheia_evidence_bundle | 55 | OK |
| 04_aletheia_odin_bridge | 62 | OK |
| 05_odin_claim_reasoner | 70 | OK |
| 06_histor_aletheia_importer | 68 | OK |
| 07_histor_odin_importer | 76 | OK |
| 08_case_bundle_v02 | 80 | OK |
| 09_atlas_registry | 63 | OK |
| 10_atlas_release_gate | 75 | OK |
| 11_coordinator_workflow_v032 | 82 | OK |
| 12_companion_cli_v031 | 79 | OK |
| 13_unified_case_manifest | 65 | OK |
| 14_stack_verifier | 86 | OK |
| 15_stack_selfcheck_v012 | 96 | OK |
| 16_evidence_reasoning_demo | 68 | OK |
| 17_connected_demo | 4 | OK |
| 18_one_command_demo | 24 | OK |
| **Total** | **1,234** | **OK** |

Reproduce: `sh tools/run_all_tests.sh`

---

## 2. Live end-to-end pipeline — PASS

A real `companion create-evidence-case` run drove the full core chain by
subprocess (not fakes). Observed terminal statuses:

```
sentinel_status:            PASS_STRICT
aletheia_status:            VERIFIED_PRESENT
bridge_status:              CONVERTED
odin_reasoning_status:      CONSISTENT
atlas_validation_status:    ATLAS_VALIDATED
case_bundle_status:         BUNDLED_VERIFIED_CASE
coordinator_workflow_status: WORKFLOW_COMPLETED
companion_status:           COMPANION_COMPLETED
```

Companion verifier on the produced output: `verify_ok: true`.

Reproduce: `sh tools/run_live_e2e_demo.sh`

---

## 3. Independent verification — PASS

`independent_verify_project_witness.py` against the Move 45 full-stack component
version freeze (`verify/full_stack_component_version_freeze_v01.zip`):

```
PROJECT_WITNESS_INDEPENDENT_VERIFICATION_PASSED
verify_ok = true
```

---

## 4. Freeze record integrity — PASS

- Move 50 Local v1 Candidate verifier: `LOCAL_V1_CANDIDATE_VERIFIED`, `verify_ok = true`.
- Embedded baseline (36 component zips) sha-record validation: PASS.
- All latest-component frozen zips are byte-identical to the verified baseline.
- Key top-level zip checksums (candidate, freeze, independent verifier): PASS.

---

## What is NOT claimed

This stack does not prove external truth, authenticate sources, sign outputs,
externally anchor outputs, or claim production readiness. It is a Local v1
Candidate, not a final Local v1 Release. Roadmap moves beyond 51 remain future
work.
