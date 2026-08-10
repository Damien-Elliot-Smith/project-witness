# Current Release State - Project Witness

Date: 2026-07-12 (Move 79 candidate)

This is the single authoritative statement of the current release state.
If any other document appears to contradict this file, this file wins, and the
contradiction is a documentation bug to be repaired.

Status: Roadmap One (Steps 1-70) complete as a local review/demo stack. Not production-ready. Post-completion repairs Move 70.6 and RT-004 are adopted. The Move 71 Python behaviour freeze is adopted. Rust Moves 72-78 are adopted. Part Two has started. Move 79 is a verification-only Python/Rust agreement harness candidate.

Status exact marker: Project Witness Roadmap One, Steps 1-70, is complete as a local review/demo stack. Post-completion repairs Move 70.6 and RT-004 are adopted. The Move 71 Python behaviour freeze is adopted. Rust Moves 72-78 are adopted, including ZipGuard archive safety. Part Two has started. Move 79 (verification-only Python/Rust agreement harness) is the current candidate; no full bundle verification capability exists or is claimed.

## Current source release package

Current source release package:
`releases/rt_004_repair/Project_Witness_SRC_v21_RT004.zip`
(RT-004 repair candidate source; see `RELEASE_BLOCKER_REGISTER.md` RB-EXT-002
and `CHANGELOG_RT_004_REPAIR.md`). The declared final Roadmap One package
below is historical and unchanged. `tools/check_src_matches_release.sh`
compares the live `src/` against this current source release package.

## What is complete

- Project Witness Roadmap One, Steps 1-70, is complete as a local review/demo stack.
- Move 72 Rust workspace skeleton adopted: zero-crate Cargo workspace
  outside `src/`; cargo build and cargo test PASS verified on Termux
  (internal storage) during adoption.
- Move 73 witness-verify CLI skeleton adopted: controlled FAIL /
  INCONCLUSIVE output contract, PASS unreachable, cargo-verified on
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

- Move 79 is a verification-only Python/Rust agreement harness
  candidate under verify/agreement_harness_v01/. It cross-checks the
  adopted stack (bundle lane: Python companion verify vs Rust
  witness-verify; archive lane: an independent Python ZipGuard test
  oracle vs the adopted Rust ZipGuard) three ways against independently
  declared expectations. It changes NO adopted runtime; deleting it
  changes no behaviour. It is not adopted until the full three-way
  comparison runs in Termux with an explicit --rust-bin
  (INCONCLUSIVE / RUST_TOOLCHAIN_UNAVAILABLE on the builder machine).
- Rust verification capability currently covers manifest structure,
  top-level declared file hashes, declared receipt-chain linkage,
  receipt canonical-hash recomputation, and adopted ZIP archive safety inspection (central directory + local
  headers). Archive safety does not prove archive-content
  validity. No full or production Rust bundle verifier exists or is
  claimed.
- Part Two Steps 80-130 have not started.
- No Android app has been built (Move 68 is a planning pack only).
- No Windows app has been built (Move 69 is a planning pack only).
- No external human reviewer has reviewed this stack. The feedback ledger
  records `NO_EXTERNAL_FEEDBACK_RECORDED`.

## What the current release proves

Under tested local conditions only, the stack preserves and verifies structured
provenance relationships between files, hashes, manifests, receipts, statuses,
and declared workflow outputs, using standard-library Python with no network
and no third-party packages.

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
sh tools/check_current_release_state.sh   # authoritative current-state checker
sh tools/run_all_tests.sh                 # all component test suites
sh tools/validate_handoff.sh              # handoff validation wrapper
sh tools/check_local_v1_release.sh        # release/doc consistency (updated in Move 70.5)
sh tools/check_src_matches_release.sh     # live src/ vs declared release source
sh tools/check_rust_workspace.sh          # Rust workspace (PASS/FAIL/INCONCLUSIVE)
sh tools/run_demo.sh                      # end-to-end demo
```

The authoritative current-state checker is
`tools/check_current_release_state.sh`. Older `tools/check_*.sh` scripts were
updated in Move 70.5 to the Roadmap One completion state and remain useful, but
they are not authoritative for current status.

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

## What happens next

Step 79 adds the Python/Rust agreement harness: the same bundles run
through both implementations, and any mismatch in verdict, reason
code, or hash is a failure until explained.













