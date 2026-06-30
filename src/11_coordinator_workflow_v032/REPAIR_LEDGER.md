# Coordinator Workflow v0.3.2 — Repair Ledger

## What this is

v0.3.2 is a **narrow blocker repair for Move 30** (Project Witness Connected
Demo v0.1). It is not a new feature. The package folder/zip is named
`coordinator_workflow_v032`; the output schema and `coordinator_workflow_version`
remain **0.3.0** for compatibility with Companion v0.3.1, Unified Case Manifest
v0.1, Stack Verifier v0.1, Stack Selfcheck v0.1, and the Connected Demo.

## The blocker

With Coordinator v0.3.1 (real lower components) and Companion v0.3.1 (request-file
hygiene) both fixed, the Connected Demo reached the downstream tools and failed:

    Unified Manifest v0.1 build -> FAILED_EVIDENCE_ID_MISMATCH
    Stack Verifier v0.1 check   -> FAILED_EVIDENCE_ID_MISMATCH

Cause: Unified Manifest `_check_ids` (and the Stack Verifier equivalent) require
`evidence_id` present and equal across records, including
`coordinator_output/case_bundle_v02/case_manifest.json`. Every record carried
`evidence_id = evidence_demo_001` except that one: the **real Case Bundle v0.2**
manifest records `case_id` + `bundle_status` but no `evidence_id`. The old
in-process fake runner had injected one, hiding the gap; the real Case Bundle does
not, so the field was genuinely absent.

## The repair

In the `case_bundle_verify` step, **after** the real `case_bundle_v02.py verify`
returns `BUNDLED_VERIFIED_CASE` and the raw `case_id` is confirmed to match the
workflow `case_id`, the coordinator now:

1. Preserves the raw Case Bundle manifest byte-for-byte at
   `coordinator_output/case_bundle_v02/raw_case_bundle_manifest.json`.
2. Writes a coordinator compatibility summary in its place at
   `coordinator_output/case_bundle_v02/case_manifest.json` containing the raw
   fields plus:

       "case_id": <same case_id used across Sentinel/Aletheia/ODIN>,
       "evidence_id": <same evidence_id from workflow_request>,
       "bundle_status": "BUNDLED_VERIFIED_CASE",
       "source": "coordinator_compatibility_summary",
       "raw_case_bundle_manifest_preserved": true,
       "raw_case_bundle_manifest": "raw_case_bundle_manifest.json"

The summary is honest and clearly labelled: it does **not** claim Case Bundle
produced `evidence_id`; the raw output is preserved separately and pointed to by
name. The summary is written **only** after a genuine `BUNDLED_VERIFIED_CASE`.

This is safe for every consumer: neither Unified Manifest nor Stack Verifier
re-verifies the Case Bundle's *internal* `bundle_checksums.txt` (they read
`case_manifest.json` for ids and hash it externally), and the coordinator- and
companion-level checksums that *do* cover `case_manifest.json` are computed after
this step, so they cover the summary.

## Invariants preserved

- **No frozen component modified.** Case Bundle v0.2, Companion v0.3.1, Unified
  Manifest, Stack Verifier, Stack Selfcheck, Atlas, Sentinel, Histor-lite,
  Aletheia, Bridge, and ODIN are untouched.
- **No new workflow, action type, or Atlas term.** Same nine steps, same plan.
- **Output schema unchanged.** `coordinator_workflow_version` stays `0.3.0`; the
  output still passes the v0.3.0 verifier (id-consistency now finds `evidence_id`
  present and matching in the summary).
- **Honesty preserved.** Raw Case Bundle output kept; summary explicitly labelled.
- **Freeze gate stays in-process.** `subprocess` remains confined to
  `component_runners.py`; the default suite uses an injectable executor.

## R-numbers

- **R1 — compatibility summary.** After a real BUNDLED_VERIFIED_CASE, write the
  evidence_id-carrying summary at `case_manifest.json`.
- **R2 — preserve raw.** Keep the raw Case Bundle manifest byte-for-byte at
  `raw_case_bundle_manifest.json`.
- **R3 — gated + labelled.** Summary written only after BUNDLED_VERIFIED_CASE and
  a case_id match; `source` + `raw_case_bundle_manifest_preserved` make its origin
  explicit.
- **R4 — tests.** `tests/test_real_runner.py` adds: summary includes evidence_id;
  summary labelled as coordinator summary; raw manifest preserved without
  evidence_id; summary only written after BUNDLED_VERIFIED_CASE.
