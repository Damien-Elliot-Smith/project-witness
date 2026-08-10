# Changelog - Move 77 (CANDIDATE)

Move: 77
Name: Rust strict canonical JSON tool + receipt hash recomputation
Date: 2026-07-10
Status: CANDIDATE. ADOPTION BLOCKED until a real cargo build + cargo test
PASS transcript exists (sh tools/check_rust_workspace.sh PASS, exit 0, on
Cargo/Termux internal storage). This Rust has NOT been compiled.
Base: adopted Move 76
(zip sha256 5aca4fb94e0e65461d05e17f96a496f834b8179a9efcba305834878f32b37a22).

## Grounding (done before any Rust was written)

The Python canonicalization recipe (canonical.py: sort_keys=True,
separators=(",",":"), ensure_ascii=False, allow_nan=False; SHA-256 over
UTF-8) was PROVEN by reproducing all three stored canonical_hash values
of the frozen Move 71 reference receipts independently in Python. A
computed scan of the reference found ZERO floats and ZERO non-ASCII
strings. Four cross-implementation vectors (exact canonical string +
digest) were precomputed with CPython json.dumps + hashlib and embedded
as Rust unit tests.

## Added

- rust/witness-verify/src/canonical.rs: strict canonical JSON tool,
  byte-identical to Python. Key sort by code point (Rust &str Ord ==
  UTF-8 byte order == code point order). ensure_ascii=False escaping
  (backslash, quote, control chars only; raw UTF-8 otherwise).
  FAILS CLOSED on non-integer numbers (CANONICAL_FLOAT_UNSUPPORTED)
  rather than risk diverging from CPython float repr - safe because the
  stack emits integers only. Six unit tests (4 CPython vectors + float
  fail-closed + integer preservation).
- json.rs: Int(i64) value variant so integers round-trip exactly and
  are re-emitted without a decimal point (matching Python); integral
  values outside i64 stay float so canonicalization fails closed.
- receipts.rs: each receipt canonical_hash is now RECOMPUTED over its
  hashable payload (all keys except canonical_hash, mirroring Python
  Receipt._hashable_payload) and compared to the declared value. This
  CLOSES the Move 76 declared-value blind spot FOR RECEIPTS: the tamper
  Move 76 could not catch (rewrite a payload field + its declared hash +
  downstream links) is now caught. Recomputation runs AFTER the
  structural chain checks so a structural break reports its own reason
  code. New codes: RECEIPT_HASH_RECOMPUTATION_MISMATCH,
  RECEIPT_CANONICALIZATION_ERROR.
- New verdict reason on a fully-recomputed chain:
  RECEIPT_CHAIN_HASHES_RECOMPUTED (still INCONCLUSIVE, still no PASS).
- Tests: dedicated recomputation-mismatch test (tamper reason_code
  without updating the hash); three Move 76 tests rebuilt to recompute
  real hashes after re-reading that the fixture now computes them.
  37 Rust tests total.

## Depth honesty (unchanged discipline)

RECEIPT canonical hashes are now recomputed. manifest_hash and
seal_hash recomputation, nested component checksums, manifest bindings,
and archive safety (Step 78) are still NOT implemented. Verdict stays
INCONCLUSIVE; PASS unreachable. No full Python/Rust agreement is claimed
(that is Step 79).

## Changed

- tools/check_rust_workspace.sh: banner rolled to Move 77; alignment
  guard extended to (a) reproduce the reference receipt hashes via the
  canonical recipe in Python and (b) require the canonical vector tests
  present; the stale Move 76 "declared-value depth limit" rule updated
  to the recomputation-gaps statement; negative-tested.
- State model rolled proactively (Move 76 adopted; Move 77 candidate;
  Steps 78-130 not started; 18 markers; both coupled checkers). One
  coupled-checker phrase initially mismatched the wrapped state-doc
  wording (the single-line-match class again) - fixed by aligning the
  required phrase to the actual text.

## Not changed / not claimed

Python src/ untouched. Move 71 freeze records untouched. SHA-256
untouched. NO ZipGuard (Step 78), NO manifest/seal recomputation, NO
full bundle verification claim, NO full Python/Rust agreement claim.

## Move 77 candidate v2 addendum (2026-07-10)

External review found a current-state contradiction the per-move rolls
had missed for three moves: CURRENT_RELEASE_STATE.md top-line status was
correct (Moves 72-76 adopted, Move 77 candidate), but its "What is not
complete" section still carried a fossilized Move 74 candidate block and
the sentence "Rust workspace exists, but no Rust verification capability
exists yet." Both false since Move 74 adopted. Worse,
check_current_release_state.sh REQUIRED that no-capability sentence,
making it a false-green checker enforcing outdated state - the same class
repaired in the Move 72 rebuild and the Move 74 v2 round.

Root cause: per-move edits updated a Move 77 candidate block elsewhere in
the file while this second, older block was never rewritten. The
capability claim was narrated once and never rechecked - the same
"narrate once, never recompute" failure as the field count, one level up
at the prose layer.

Repairs in v2:

- The fossil block is replaced with a precise current-capability
  statement: "Rust verification capability currently covers manifest
  structure, top-level declared file hashes, declared receipt-chain
  linkage, and candidate receipt canonical-hash recomputation. No full
  or production Rust bundle verifier exists or is claimed."
- check_current_release_state.sh now REQUIRES that precise sentence,
  FORBIDS the stale Move 74 candidate wording, FORBIDS the no-capability
  sentence, requires Moves 72-76 adopted + Move 77 candidate, and
  forbids three full/production-verifier-complete claims. Negative-tested
  in all three required directions.
- check_rust_workspace.sh header corrected from "Contract tracked:
  Move 74" to Move 77.
- Two of my own repair rules initially failed on line-wrapped grep
  targets, and one forbid used grep -F alternation (\|) that matched
  literally and never fired - both the single-line-match and the
  literal-grep classes, caught and fixed here, recorded for the pattern.

Rust implementation unchanged (repair rule 8); this is a truth-state
repair only.

## Move 77 candidate v3 addendum (2026-07-11) - CORRECTION OF RECORD

The v1/v2 changelog text "37 Rust tests total" is WRONG and is
superseded by this addendum. The actual count, computed from the source
tree (grep -rh "#[test]" rust/witness-verify/src | wc -l) and executed
by the Termux Cargo gate, is 39 tests, all passed. Per-file: canonical.rs
6, json.rs 5, main.rs 23, sha256.rs 5 (hashes.rs and manifest.rs carry
their coverage via main.rs integration tests).

This is the fourth narrated-count drift in Part Two (field count 16/17/19;
now test count 37/39). The prior three were data-layer; this one is the
audit record itself. The wrong "37" claim in the v1/v2 sections above is
retained ONLY as superseded history; this addendum is the correction of
record.

Root cause: the count was written by recollection after several test
edits (added the recomputation-mismatch test, rebuilt three Move 76
tests) rather than computed from source. Fix, same shape as every prior
drift: make it computable and check it.

Repairs in v3 (Rust source byte-for-byte unchanged from v2, verified by
tree hash):

- tools/check_rust_workspace.sh: new guard computes the Rust #[test]
  count from source and requires CHANGELOG_MOVE_77.md to state that exact
  number in a machine-checkable line; when Cargo is present it also
  asserts the "N passed" line of cargo test output matches. Negative-
  tested.
- STATED_RUST_TEST_COUNT recorded as a checkable line below.

<!-- RUST_TEST_COUNT: 39 -->
Move 77 Rust test count (computed and Termux-executed): 39.
