# Changelog - Move 75 (CANDIDATE)

Move: 75
Name: Rust file hash verification
Date: 2026-07-10
Status: CANDIDATE. ADOPTION BLOCKED until a real cargo build + cargo test
PASS transcript exists (sh tools/check_rust_workspace.sh PASS, exit 0, on
Cargo/Termux internal storage). The builder sandbox has no Rust
toolchain: this Rust has NOT been compiled, and the SHA-256
implementation has NOT been executed anywhere. Its correctness gate is
the unit tests on your machine: three FIPS 180-4 vectors and two
CPython-hashlib-precomputed digests. If any vector test fails, the
implementation is wrong - paste the output back.
Base: adopted Move 74 v3
(zip sha256 0b26fafd058fb53da27d9707dd8e32e13486e12fc5693b8d01908c44e65409b4).

## Added

- rust/witness-verify/src/sha256.rs: SHA-256 per FIPS 180-4, stdlib
  only. Unit tests: empty-string, "abc", and two-block NIST vectors;
  cross-implementation digests precomputed by CPython hashlib during
  grounding; padding-boundary cases (55/56/64/119/120 bytes).
- rust/witness-verify/src/hashes.rs: verifies every digest declared in
  companion_checksums.txt by recomputation; digest format enforced (64
  lowercase hex); the eight critical paths of the Python
  checksums.REQUIRED_PATHS contract must be declared
  (REQUIRED_PATH_UNDECLARED otherwise). New reason codes:
  MALFORMED_DIGEST, FILE_HASH_MISMATCH, HASH_READ_ERROR,
  REQUIRED_PATH_UNDECLARED.
- Depth honesty, stated in code and output: this stage verifies
  TOP-LEVEL declared hashes only. Nested component checksums, manifest
  bindings, and the Sentinel source-run binding (the Python RT-004
  deep layer) are NOT implemented; a passing bundle yields
  INCONCLUSIVE / TOP_LEVEL_HASHES_OK - never PASS. Claiming more would
  recreate in Rust the depth illusion RT-004 repaired in Python.
- Test fixture upgraded: real computed digests over all eight required
  paths (vector tests prove the hasher independently; the fixture uses
  it for consistency). Three new negative tests: hash mismatch,
  malformed digest, undeclared required path. 25 Rust tests total.

## Changed

- tools/check_rust_workspace.sh: banner rolled to Move 75; alignment
  guard extended to a computed three-way hash-paths check (Rust
  constant, Python checksums.REQUIRED_PATHS, reference declared paths -
  plus declared-length arithmetic); negative-tested. New structural
  rules: sha256 module, FIPS vectors, hashlib cross-check,
  mismatch/undeclared detection present.
- State model rolled proactively: Move 74 recorded adopted (with the
  Termux transcript facts and the reference-bundle INCONCLUSIVE
  confirmation); Move 75 candidate; Steps 76-130 not started; markers
  in all 18 docs; both coupled checkers updated.

## Not changed / not claimed

Python src/ untouched. Move 71 freeze records untouched. NO receipt
chain verification (Step 76), NO canonical JSON tooling (Step 77), NO
ZipGuard (Step 78), NO full bundle verification claim, PASS still
unreachable.

## Move 75 candidate v2 addendum (2026-07-10)

The v1 Termux cargo gate failed on ONE stale unit test:
version_marks_step74 still asserted the Move 74 version string after the
v1 VERSION bump to 0.0.4-step75-hash-verification. cargo build passed,
and the bonus binary check independently verified all 8 declared hashes
of the Move 71 reference bundle (INCONCLUSIVE / TOP_LEVEL_HASHES_OK) -
the SHA-256 implementation passed its first execution in full. The
SHA-256 code is untouched in v2, per repair rule 3.

Repairs in v2:

- version_marks_step75 now asserts the current version string.
- Stale-reference sweep of rust/ found one more: rust/README.md still
  described "Step 73 status" (stale since Move 74, unwatched by any
  checker). Updated to the Step 75 status with the depth-honesty
  limits, and annotated that it is now mechanically checked.
- Guard extended (same lesson, third application): the checker now
  computes agreement between the VERSION step marker, the version-
  marker unit test (name and asserted substring), and the rust/README
  status heading. Negative-tested in both directions. A version bump
  without a matching test and README update can no longer reach
  packaging.
