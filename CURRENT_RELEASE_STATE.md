# Current Release State - Project Witness

Date: 2026-08-10 (Move 85 v08 adopted publication state)

This is the single authoritative statement of the current release state.
If any other document appears to contradict this file, this file wins, and the
contradiction is a documentation bug to be repaired.

Current publication state (2026-08-10): Roadmap One, Steps 1–70, is complete as a local review/demo stack. Move 70.6 and RT-004 are adopted post-completion repairs. Move 71 Python behaviour freeze is adopted. Rust-hardening Moves 72–85 are adopted. Move 85 v08 is the current adopted technical authority for this publication state. Project Witness is not production-ready.

Status exact marker: Current publication state (2026-08-10): Roadmap One, Steps 1–70, is complete as a local review/demo stack. Move 70.6 and RT-004 are adopted post-completion repairs. Move 71 Python behaviour freeze is adopted. Rust-hardening Moves 72–85 are adopted. Move 85 v08 is the current adopted technical authority for this publication state. Project Witness is not production-ready.

Move 85 v08 artifact SHA-256: `f512cc9933153d2a6a97c3158515766fc3c9db0a226153cbb010b37fccb59665`
Frozen technical-authority commit: `0ae018bc00b5a59f6dcbb6629a2706cb9059280b`

## Inherited Roadmap One source release package

The Roadmap One source package retained by the adopted tree is:
`releases/rt_004_repair/Project_Witness_SRC_v21_RT004.zip`
(RT-004 repair source; the repair is now adopted; see `RELEASE_BLOCKER_REGISTER.md` RB-EXT-002
and `CHANGELOG_RT_004_REPAIR.md`). The declared final Roadmap One package
below is historical and unchanged. `tools/check_src_matches_release.sh`
compares the live Roadmap One `src/` against this retained Roadmap One source package.

## What is complete

- Project Witness Roadmap One, Steps 1-70, is complete as a local review/demo stack.
- Move 72 Rust workspace skeleton adopted: zero-crate Cargo workspace
  outside `src/`; cargo build and cargo test PASS verified on Termux
  (internal storage) during adoption.
- Move 73 witness-verify CLI skeleton adopted: controlled FAIL /
  INCONCLUSIVE output contract; the adopted source declares `VERDICT_FAIL` and `VERDICT_INCONCLUSIVE` and no PASS verdict constant; cargo-verified on
  Termux during adoption.
- Move 74 Rust case manifest validator adopted: nineteen-field report
  contract computationally aligned with the frozen reference,
  cargo-verified on Termux during adoption (17 tests), and confirmed
  INCONCLUSIVE / MANIFEST_STRUCTURE_OK against the Move 71 reference
  bundle.
- Move 75 Rust top-level file hash verification adopted: stdlib
  SHA-256 (FIPS vectors + CPython hashlib cross-check), all eight
  declared hashes of the reference bundle independently recomputed on
  Termux during adoption (25 tests), confirmed INCONCLUSIVE /
  TOP_LEVEL_HASHES_OK.
- Move 76 Rust declared receipt-chain linkage adopted: 21-key receipt
  contract, order/linkage/seal/continuity checks, cargo-verified on
  Termux (32 tests), confirmed INCONCLUSIVE / RECEIPT_CHAIN_LINKAGE_OK
  on the reference 3-receipt chain.
- Move 78 Rust ZipGuard archive-safety adopted: read-only central +
  local header inspection, extra-field allowlist (0x5455/0x7875),
  cargo-verified on Termux (123 tests, 3 clean parallel runs), accepts
  all three real archives (970/819/935) as INCONCLUSIVE / ARCHIVE_SAFETY_OK.
- Move 77 Rust canonical JSON + receipt hash recomputation adopted:
  byte-identical to the Python recipe (CPython vectors), receipt
  canonical_hash recomputed, cargo-verified on Termux (39 tests),
  confirmed INCONCLUSIVE / RECEIPT_CHAIN_HASHES_RECOMPUTED.
- Rust-hardening Moves 79-85 are adopted. Move 85 v08 is the current adopted
  technical authority for this publication state.
- Move 85 audit pack v1 is the Move 85 roadmap deliverable. The standalone
  Android/Termux AArch64 `witness-verify` binary and provenance record are
  supporting measurement artefacts rather than the primary deliverable.
- Across the adopted tested corpus and audit-pack surfaces, no Rust PASS was
  observed. This is an empirical statement, not a proof that a PASS-producing
  path is globally unreachable.
- All 18 working components under `src/` with passing stdlib `unittest` suites.
- The Move 70 final review verifier passed: `MOVE_70_LOCAL_V1_FINAL_REVIEW_VERIFIED`, `verify_ok = true`.
- Move 70.6 reconciliation adopted: live `src/` matches the declared
  release source (`tools/check_src_matches_release.sh`).
- RT-004 repair adopted: Companion deep verification (v0.3.2) rejects
  tampered nested evidence in all four tamper classes.
- Move 71 Python behaviour freeze adopted:
  `freeze_record/python_behaviour_freeze_v01/` (reference bundle, ten
  recorded verdicts, 302 reason codes, nondeterminism registry,
  `verify_move_71.py` passing).
- Final Roadmap One package:
  `releases/roadmap_one_complete/move_70_final/Project_Witness_WORKING_STACK_v20_MOVE_70.zip`
- SHA-256:
  `1248bc46fa555cc50ed7b63c9284baffd1e95a6972cdfbc4a40a0201fea81aba`

## What is not complete

- Project Witness is not production-ready and no production Rust bundle-verifier claim is made.
- The Rust source-level contract contains FAIL and INCONCLUSIVE verdict constants and no PASS verdict constant. Separately, no Rust PASS was observed across the adopted tested corpus/audit surfaces. Neither statement is a global reachability proof.
- A clean bundle reaches `INCONCLUSIVE`, exit `3`, in the adopted Rust measurements; `INCONCLUSIVE` is not PASS.
- Python/Rust behavioural equivalence is not established. Two adopted divergence IDs remain:
  `stage_manifest_json_invalid` and `stage_report_field_missing_repaired`.
  `SYSTEM_AGREEMENT_RESULT: FAIL` / `SYSTEM_AGREEMENT_REASON: BEHAVIOURAL_DIVERGENCE_DETECTED`
  are expected evidence for those known divergences, not a Move 85 adoption failure.
- The Rust verifier detects the demonstrated top-level tamper but does not detect
  the demonstrated nested evidence tamper at
  `coordinator_output/aletheia_bundle/evidence/evidence_001.bin`; the Python lane does detect it.
- Held Rust build/runtime evidence establishes Android/Termux AArch64 only.
  Linux x86_64, Linux AArch64, and Windows x86_64 remain unestablished.
  The Android/Termux AArch64 binary is not a generic Linux AArch64 binary.
- No Android app has been built (Move 68 is a planning pack only).
- No Windows app has been built (Move 69 is a planning pack only).
- No external human reviewer has reviewed this stack. The feedback ledger
  records `NO_EXTERNAL_FEEDBACK_RECORDED`.

## What the current release proves

Under tested local conditions only, the stack preserves and verifies structured
provenance relationships between files, hashes, manifests, receipts, statuses,
and declared workflow outputs. The inherited Roadmap One path uses
standard-library Python with no third-party Python packages. The adopted Rust
verifier is source-built with Cargo/Rust; held build/runtime evidence establishes
Android/Termux AArch64 only.

## What it does not prove

- It does not prove real-world truth or that any evidence is factually correct.
- It does not prove legal validity.
- It does not prove external identity or authenticate people.
- It does not prove trusted timestamping. Move 66 anchoring is local simulation
  only, not real external anchoring, blockchain anchoring, or public witnessing.
- It does not provide production-valid signing. Move 65 signing is test-only.
- It is not production-ready.
- It does not claim external reviewer approval.
- Move 67 web UI is read-only and does not execute actions.
- It has no cloud operation claim and no autonomy claim.

## Which commands verify it

Run from the repository root:

```sh
sh tools/check_current_release_state.sh   # inherited checker; contains pre-Move-85 publication assertions
sh tools/run_all_tests.sh                 # all component test suites
sh tools/validate_handoff.sh              # handoff validation wrapper
sh tools/check_local_v1_release.sh        # release/doc consistency (updated in Move 70.5)
sh tools/check_src_matches_release.sh     # live src/ vs declared release source
sh tools/check_rust_workspace.sh          # Rust workspace (PASS/FAIL/INCONCLUSIVE)
sh tools/run_demo.sh                      # end-to-end demo
```

`tools/check_current_release_state.sh` is an inherited technical checker whose
publication-text assertions predate Move 85. It remains frozen technical-authority
code and is not the authority for this documentation-only publication overlay.
Older `tools/check_*.sh` scripts remain useful for their adopted scopes, but their
hard-coded documentation strings do not override this current-state document.

## Which docs are historical

Historical records are preserved unedited (or banner-marked) and do not
describe the current state:

- `LOCAL_V1_RELEASE.md` - Move 60 "Local v1 Release" milestone (banner-marked historical).
- `freeze_record/` - Move 50 candidate, Move 51 Termux, and Move 60 release
  freeze records. Freeze records are frozen snapshots and are never rewritten;
  the Move 60 wording inside them is historical by definition.
- `CHANGELOG_MOVE_52.md` through `CHANGELOG_MOVE_60.md` and
  `CHANGELOG_REPAIR_v02.md` - per-move historical changelogs.
- Historical notes inside `STACK_STATUS.md` below the "Roadmap One final
  status" section, which are explicitly labelled as historical records.
- `src/*/_frozen/` - frozen component records.

If Move 60 is mentioned anywhere in current documentation, it refers to an
earlier milestone, not the current state.

## Current publication endpoint

Moves 71-85 are adopted as a completed Rust-hardening block. Move 85 audit pack
v1 is the roadmap deliverable for Move 85. This publication reconciliation is
documentation-only and is not Move 86; it does not imply that Project Witness as
a whole is finished or production-ready.













