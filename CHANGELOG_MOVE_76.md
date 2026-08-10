# Changelog - Move 76 (CANDIDATE)

Move: 76
Name: Rust receipt chain verification (declared-value layer)
Date: 2026-07-10
Status: CANDIDATE. ADOPTION BLOCKED until a real cargo build + cargo test
PASS transcript exists (sh tools/check_rust_workspace.sh PASS, exit 0, on
Cargo/Termux internal storage). This Rust has NOT been compiled.
Base: adopted Move 75 v2
(zip sha256 b52c92054fff09264aff1a2f22eaec725311387731eee6b4a9bba56c6cc68a09).

## Added

- rust/witness-verify/src/receipts.rs: verifies the Sentinel receipt
  chain in coordinator_output/sentinel_run/sentinel_run.json, mirroring
  the DECLARED-VALUE checks of Python ReceiptChain.verify_chain:
  exact 21-key receipt contract (computed from the frozen reference,
  enforced by the alignment guard); receipt order and IDs (gaps and
  duplicates); GENESIS start; prior-hash linkage; run_id and
  manifest_hash consistency across receipts, manifest and seal; hash
  field formats; seal cross-checks (count, final id, final hash);
  session continuity. Reason codes: RUN_RECORD_MISSING,
  RUN_RECORD_READ_ERROR, RUN_RECORD_JSON_INVALID, RUN_RECORD_MALFORMED,
  RECEIPTS_MISSING, RECEIPT_MALFORMED, RECEIPT_ID_SEQUENCE_BROKEN,
  RECEIPT_RUN_ID_MISMATCH, RECEIPT_MANIFEST_HASH_MISMATCH,
  RECEIPT_HASH_MALFORMED, GENESIS_PRIOR_HASH_INVALID,
  RECEIPT_LINKAGE_BROKEN, SESSION_CONTINUITY_BROKEN, SEAL_MISSING,
  SEAL_MALFORMED, SEAL_MISMATCH.
- json.rs: as_array and as_number helpers.
- Fixture upgraded with a valid two-receipt chain; seven new negative
  tests (missing run record, id gap, broken linkage, invalid genesis,
  seal count mismatch, session continuity break, malformed key set).
  32 Rust tests total. One test was retargeted during authoring after
  re-reading the fixture key order showed it would have mutated the
  wrong receipt (recorded here per the correlated-error discipline).

## Depth honesty (stated in code, output, and docs)

Linkage is verified against DECLARED hash values only. Canonical hash
recomputation for receipts, manifests and seals requires the canonical
JSON tool (Step 77) and is NOT implemented: a tamperer who rewrites a
receipt AND its declared canonical_hash AND every downstream prior_hash
link is not caught at this stage (Python catches that case by
recomputation). Verdict on a fully-linking chain: INCONCLUSIVE /
RECEIPT_CHAIN_LINKAGE_OK. PASS remains unreachable.

## Changed

- tools/check_rust_workspace.sh: banner rolled to Move 76; alignment
  guard extended with the computed 21-key receipt contract
  (negative-tested); new structural rules including the declared-value
  depth limit statement. One rule initially failed on a line-wrapped
  grep target - the same single-line-match class found in the Move 74
  v2 round - fixed by keeping the phrase on one line.
- State model rolled proactively: Move 75 recorded adopted (Termux
  facts: 25 tests, all eight reference hashes recomputed); Move 76
  candidate; Steps 77-130 not started; markers in all 18 docs; both
  coupled checkers updated.

## Not changed / not claimed

Python src/ untouched. Move 71 freeze records untouched. SHA-256
untouched. NO canonical JSON (Step 77), NO ZipGuard (Step 78), NO
canonical-hash recomputation, NO full bundle verification claim.
