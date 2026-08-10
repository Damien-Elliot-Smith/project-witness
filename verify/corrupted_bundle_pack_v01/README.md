# Corrupted Bundle Test Pack (Move 80)

One clean control plus seven deliberately corrupted fixtures, generated
deterministically from the pinned frozen clean seed, executed against the
adopted verifiers, and evaluated against DECLARED per-lane expectations.

## Scope and threat statement

This pack tests one question only: **when a bundle is corrupted in a
specific declared way, do the adopted verifiers produce exactly the
rejection (or documented blindness) that the adopted Move 79 v27 contract
says they produce?**

It defends against these failure classes:

- a verifier silently ACCEPTING a corruption it is contracted to reject;
- a verifier rejecting for the WRONG reason, wrong stage, or wrong exit
  code (misattribution would poison later diagnosis);
- fixture rot: fixtures drifting from their declared mutations, mutating
  the frozen seed, or becoming non-reproducible;
- dishonest evaluation: collapsing different lane verdicts into a fake
  common verdict, or describing the Rust verifier's honest
  INCONCLUSIVE ceiling as PASS.

It does NOT test: real-world truth of evidence, legal validity, external
identity, trusted timestamping, or any corruption class outside the eight
declared fixtures. It does not extend either verifier's detection power;
it measures the adopted contract exactly as it stands, including its
blind spots.

## The eight fixtures

| Fixture | Corruption | Expected outcome (declared) |
|---|---|---|
| M80-CLEAN-001 | none (control) | Python PASS/0; Rust INCONCLUSIVE/3 RECEIPT_CHAIN_HASHES_RECOMPUTED — its honest clean-bundle ceiling, never described as PASS |
| M80-MISSING-MANIFEST-001 | companion_report.json deleted | both reject at the manifest boundary: Python FAIL/1 "missing required file: companion_report.json", Rust FAIL/1 MANIFEST_MISSING (honest per-lane class split) |
| M80-CHANGED-EVIDENCE-001 | one evidence byte flipped, stale nested hash retained | Python FAIL/1 deep checksum mismatch; Rust INCONCLUSIVE/3 (documented capability limit: no nested-evidence inspection) |
| M80-BAD-RECEIPT-HASH-001 | one receipt's canonical_hash field replaced with a fixed invalid value (0*64); no other field or receipt changed | Python PASS/0 (documented receipt blindness); Rust FAIL/1 RECEIPT_HASH_RECOMPUTATION_MISMATCH |
| M80-DUPLICATE-RECEIPT-001 | final receipt duplicated | Python PASS/0 (documented receipt blindness); Rust FAIL/1 RECEIPT_ID_SEQUENCE_BROKEN |
| M80-MALFORMED-JSON-001 | companion_report.json truncated | both reject, at DIFFERENT stages (declared divergence pattern: Python canonical_report vs Rust manifest); never reshaped into fake agreement |
| M80-PATH-TRAVERSAL-001 | ZIP entry named ../evil | archive boundary rejects: Rust inspect-archive and the Python ZipGuard oracle both FAIL/1 ARCHIVE_PATH_TRAVERSAL; no preliminary extraction anywhere; the runner proves the REAL ../evil destination (sandbox/evil) is neither created (creation test) nor overwritten nor deleted when pre-created as the outside sentinel (overwrite/deletion test) |
| M80-UNKNOWN-SCHEMA-001 | companion_cli_version = "9.9.9", canonical serialization, checksums repaired | Python PASS/0 (documented blindness to this field); Rust FAIL/1 SCHEMA_VERSION_UNSUPPORTED |

Full declarations with match types, stages, reason classes and per-lane
evidence tiers: `expected_results.json`. Byte-level mutation record:
`mutation_ledger.json`. Pinned fixture hashes: `fixture_hashes.json`.

## What "MOVE_80_REQUIRED_CASES: 8/8 PASS" means

A case PASSES when every DECLARED per-lane expectation was met exactly.
**8/8 PASS therefore means the verifiers behaved exactly as contracted —
for seven of the eight fixtures the expected outcome on at least one lane
is FAIL.** It never means the corrupted bundles verified successfully, and
the adopted Rust verifier cannot emit a bundle PASS at all (exit 0 is
unreachable in its verify path; INCONCLUSIVE/3 is its honest ceiling on a
clean bundle).

Lane results are stored separately per fixture — python_expected,
rust_expected, archive_oracle_expected — and are never collapsed into one
common verdict. The classifications used are: AGREEMENT_CASE,
BOTH_REJECT_CLASS_SPLIT, PYTHON_ONLY_DETECTION, RUST_ONLY_DETECTION,
KNOWN_DIVERGENCE_PATTERN, ARCHIVE_AGREEMENT_CASE.

## Known limits (documented, deliberate)

- **Rust evidence blindness.** The adopted Rust verifier checks only the
  eight declared top-level/coordinator hashes; it does not recurse into
  nested component checksums, so evidence-byte tampering is invisible to
  it (M80-CHANGED-EVIDENCE-001). Move 80 does not modify Rust to add
  nested inspection.
- **Python receipt blindness.** The frozen Python verifier performs no
  receipt verification: stale receipt hashes and duplicated receipts pass
  it (M80-BAD-RECEIPT-HASH-001, M80-DUPLICATE-RECEIPT-001).
- **Python schema blindness.** The frozen Python verifier never checks
  companion_cli_version (M80-UNKNOWN-SCHEMA-001). The
  coordinator_workflow_version variant is deliberately not used: its
  Python rejection is unmapped in the adopted reason map.
- **Two named seed tree-hash algorithms, never interchangeable.** The
  APPROVED contract-inventory pin is `seed_tree_hash_v0` =
  `70e6e975b3d5fab8d4a513573ef4d0d12ea0ca697ad287d46ea11b789abe7a24`
  (files only, sorted walk; per file: relpath bytes, NUL, raw file
  bytes, NUL). The fixture-identity algorithm is `entry_tree_hash_v1`
  (sorted entries of relpath / type F|D / per-file SHA-256; the seed's
  value under it is
  `3a7ad566696155cd86a4ebe707927715495253eee4b404041eb5d4bc8cfcbb19`,
  recorded as a separately named secondary). Both are pinned by name in
  the mutation ledger; tests fail if either value is assigned to the
  wrong algorithm name. Permission bits are excluded from
  entry_tree_hash_v1 pins (extraction umask varies across hosts);
  permission drift relative to the seed is checked by the integrity
  checker's undeclared-mutation comparison instead.
- **Selective checksum repair; the frozen stale entry stays frozen.**
  The frozen seed contains ONE pre-existing stale checksum entry
  (`coordinator_output/case_bundle_v02/bundle_checksums.txt` line 1,
  declaring `case_manifest.json` = cb1fc67c... while the file hashes to
  57572633...). The adopted corpus `_rewrite_checksums` helper would
  silently repair it; Move 80 therefore uses a fixture-local SELECTIVE
  dependency-closure repair that touches only entries declaring the
  principal mutated file and the strict chain above it. That stale line
  remains byte-identical to the seed in every fixture; the integrity
  checker and the focused tests enforce this, and every repaired line
  is pinned in the mutation ledger with file, line number, old/new
  digest and reason.
- The declared divergence and class splits above are recorded honestly.
  Nothing is added to or altered in the frozen 85-case agreement corpus.

## Evidence tiers

Each declared expectation carries its evidence tier in
`expected_results.json`:

- **OBSERVED** — executed directly against the v27 baseline during the
  Phase 1 inventory (frozen Python verifier / ZipGuard oracle).
- **SOURCE_VERIFIED** — established from the exact v27 source and tests.
- **TERMUX_CONFIRMED** — supported by the preserved real v27 Termux
  adoption evidence (85-case agreement run; 124 cargo unit tests).
- **REQUIRES_NEW_TERMUX_CONFIRMATION** — cannot be honestly executed
  off-device; the Move 80 Termux adoption run is the confirming
  evidence. This applies to the Rust-side verdicts for
  M80-MISSING-MANIFEST-001, M80-CHANGED-EVIDENCE-001 (blindness),
  M80-DUPLICATE-RECEIPT-001 and M80-UNKNOWN-SCHEMA-001.

## Binary handoff discipline

The focused runner (`run_move80.py`) REQUIRES `--rust-bin` as an absolute
path to an existing regular executable file and executes exactly that
binary. It never searches PATH, never invokes Cargo, never builds, never
selects a default or previously built binary, and makes no trust claim.
Proving the binary is the freshly built reviewed-source binary is the
adoption gate's job: `tools/check_move80_corrupted_bundle_adoption.sh`
owns bootstrap, LD_PRELOAD validation, trusted toolchain resolution,
clean-target removal, the fresh build, version verification
(0.0.8-step79-diagnostics), stale-executable rejection, and hands the
resolved absolute path down. The runner reports the SHA-256 of the binary
it executed and the gate requires it to equal the freshly built binary's
hash. Controlled test executables appear only inside `move80_tests.py`,
as ruled.

## Files

- `generate_fixtures.py` — deterministic generator with the named
  tree-hash algorithms and the SELECTIVE dependency-closure repair
  (composes the adopted corpus helpers and the frozen Move 71 generator
  by read-only import; the traversal ZIP is byte-identical to the
  TERMUX-confirmed corpus case).
- `author_pins.py` — pin derivation; committed pins are exactly
  reproducible from it (enforced).
- `fixture_hashes.json`, `mutation_ledger.json`, `fixture_manifest.json`
  — pinned fixture identities, line-level mutation/repair record
  (exact changed lines with reasons, plus the preserved stale entry),
  metadata.
- `expected_results.json` — DECLARED per-lane expectations (provenance:
  Phase 1 contract inventory; never regenerated from current output).
- `integrity_check.py` — seed immutability, both named seed pins,
  declared-mutations-only, stale-line preservation, line-repair
  re-verification from bytes, two-generation byte identity, pin
  reproducibility, reason-code existence in the adopted reason map.
- `run_move80.py` — focused runner (see handoff discipline above).
- `move80_tests.py` — focused tests (58) including handoff discipline,
  wrong-result detection, integrity failure modes, seed-pin algorithm
  binding, selective-repair closure exactness, baseline-zip binding,
  Move 79 evidence validation, the ../evil-destination sandbox, and
  order identity.
- `check_inherited_vs_zip.py`, `allowlist.json`,
  `MOVE_80_ALLOWLIST_DIFF_REPORT.txt` — additions-only proof computed
  DIRECTLY against the verified adopted v27 ZIP bytes supplied at run
  time (a candidate-contained inventory is self-authenticating and is
  deliberately not used).
- `check_move79_evidence.py` — mechanical validator requiring the
  complete Move 79 regression facts in the retained child gate output.

The focused tests include INDEPENDENT semantic contract assertions for
all eight fixtures that parse the seed and fixture bytes directly and
encode the expected contract as literals — never derived from the
generator's mutation table or the mutation ledger — so a
generator-vs-ledger self-consistency proof cannot mask a wrong fixture.

## Running the adoption gate (Termux)

From the repository root on the device, with the three required real
inputs supplied by the operator (never bundled, never searched for):

    REAL_MOVE78=/path/to/project-witness-MOVE_78_candidate_v10.zip \
    REAL_705=/path/to/project-witness-70.5.zip \
    REAL_MOVE79=/path/to/project-witness-MOVE_79_candidate_v27.zip \
    sh tools/check_move80_corrupted_bundle_adoption.sh

Optional: `REAL_V20=<path>` (defaults to the in-repo v20 artifact).

`REAL_MOVE79` is the baseline-immutability source: the gate
canonicalises the path, verifies its SHA-256 with the trusted sha256sum
(must equal
4a95767a3f68ca812c1d543894b65183b82d56f3f8f56e9af61b82c19de1f26b),
safety-inspects the archive (duplicate names, traversal, absolute
paths, symlinks), then compares every inherited candidate file directly
against the verified member bytes and requires additions to equal the
allowlist exactly. The gate retains the COMPLETE Move 79 child gate
output in the Move 80 transcript and mechanically requires every
regression fact (63/63, 73/73, 85/74/6/3, both exact divergence IDs, no
unmapped reasons, no missing diagnostics, agreement FAIL markers,
child exit 0) via check_move79_evidence.py.

The gate composes the adopted Move 79 machinery: it runs the COMPLETE
adopted Move 79 regression gate as a child (same required inputs) and
requires its retained result — 85 cases, 74 agreement, 6 Python-only,
3 Rust-only, the same two divergence IDs, SYSTEM_AGREEMENT_RESULT: FAIL
with SYSTEM_AGREEMENT_REASON: BEHAVIOURAL_DIVERGENCE_DETECTED, exit 0 —
before building fresh and running the eight fixtures three times
(original / reversed / deterministically shuffled orders) with
byte-identical canonical output required.

Off-device, the gate refuses with INCONCLUSIVE_RUST_UNAVAILABLE (exit 3);
`move80_tests.py`, `integrity_check.py` and `check_inherited_vs_zip.py`
run anywhere (the baseline-zip comparison tests need
`M80_BASELINE_ZIP=<path to the v27 zip>`; the gate always supplies it
and rejects a run with skipped tests).
