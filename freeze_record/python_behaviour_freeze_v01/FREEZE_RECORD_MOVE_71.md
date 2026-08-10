# Freeze Record - Move 71: Final Python Behaviour Freeze (CANDIDATE)

Move: 71 (first move of Part Two, Steps 71-130)
Date built: 2026-07-09
Status: CANDIDATE - not adopted.
Base: ADOPTED RT-004 repair state, verified before build:
  candidate zip sha256
  999799419704c7b2bbc207be1998dfab20e0d9de7d6a26f6dd057f0cc04f38aa
  declared current source release
  releases/rt_004_repair/Project_Witness_SRC_v21_RT004.zip
  (adoption chain: Move 70.5 -> Move 70.6 reconciliation -> RT-004 repair,
  each externally checked and owner-adopted)

The earlier Move 71 candidate built on the stale v20-only line is dead.
No freeze data was carried from it. The generator, extractor, and verifier
HELPER SCRIPTS were carried forward as tooling, with one extension (the
evidence_added_unexpectedly case); every DATA artifact in this pack -
reference bundle, hashes, verdicts, reason codes, nondeterminism study,
expected results - was regenerated from the adopted implementation.

## What is frozen

1. reference_bundle/ + reference_bundle_hashes.sha256: one genuine
   verified run of the adopted stack, 52 files, every byte pinned;
   companion verify (with RT-004 deep verification active) accepts it.
2. generate_failure_cases.py + expected_failures.json: TEN behavioural
   fixtures - one clean control and nine tampers, including all four
   RT-004 tamper classes - each rejected with a DISTINCT recorded reason,
   pinning the detection layer, not just the rejection.
3. reason_code_registry.json + extract_reason_codes.py: 302 codes across
   18 components, extracted from the adopted source by a frozen rule;
   drift in either direction fails.
4. nondeterminism_registry.json: empirical (two-run field diff, 48/52
   files vary, 4 deterministic). Roots: wall-clock timestamps and caller
   paths; all else is hash cascade. Byte-equality across runs is NOT a
   frozen property and must not be a Rust agreement criterion.
5. expected_results.json: 18/18 components, 1301 tests, handoff PASS,
   five doc checkers PASS, environment record.

## Verifier

verify_move_71.py: 28 checks - reference hashes (missing/extra/changed),
reference verdict, all ten failure cases replayed against recorded
verdicts, reason-code re-extraction, record parsing. Negative-tested:
tampered reference -> NOT_VERIFIED; restored -> verified.

## Provenance and correlated-verification warning

This pack was machine-built (LLM-assisted; the same model authored the
RT-004 repair code and this reference) and executed on the builder
sandbox. If the same agent authors the repair, the tests, and the
behavioural reference, its blind spots can become frozen ground truth
that the Rust verifier is later rewarded for reproducing. Non-correlated
checks: the owner's independent execution and review before adoption,
the external review loop already operating on this project, and the
independently implemented Rust verifier to come. Carry this warning into
the Part Two audit pack.

## What this freeze does not claim

No truth claims about evidence contents. No signing, no anchoring, no
reviewer approval, no byte-reproducibility across runs. Whole-folder
fabrication remains possible without signing (unchanged, documented).

## Adoption procedure (owner machine, in order)

1. Verify candidate zip sha256; extract fresh.
2. Run the five doc checkers, tools/run_all_tests.sh (expect 18/18, 1301),
   tools/validate_handoff.sh, and
   python3 freeze_record/python_behaviour_freeze_v01/verify_move_71.py.
3. Produce your own transcript; builder results are corroboration only.
4. On adoption: remove CANDIDATE from this record, add your transcript,
   record Move 71 in the register/state doc per the Move 70.5 state model,
   and only then begin Step 72 (Rust workspace).
