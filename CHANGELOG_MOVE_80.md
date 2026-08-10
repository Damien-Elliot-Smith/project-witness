# CHANGELOG — Move 80: Corrupted Bundle Test Pack

Status: CANDIDATE v07. Not adopted. Adoption requires independent
hostile review followed by a real Termux run of
`tools/check_move80_corrupted_bundle_adoption.sh` ending
`MOVE_80_CORRUPTED_BUNDLE_ADOPTION_GATE: PASS` / `exit_code: 0`.

Candidate v01 (ec255745137bc033f2e22b41286cda83ff72e6d96233c19edb6830bec4b59429)
and candidate v02
(97e3f3bcb7ec859a237138b2800a170790604244976eb92e6567e6d7b8dec5a5)
candidate v03
(29e06119c1278ecbf9973657d48da1c0adc76dce9b2024ad6f53e4578fed07c5),
candidate v04
(8e4d71b86bffc8f79bddca4dc617c269fad7c1f5f77effa6010d10c4f2c9942f)
and candidate v05
(aa0a06466cf1415da78bfbd8c3d23d796f049a8f0b9c7c020b0ab5523940d8e5)
were REJECTED at hostile review before any Termux run. Candidate v06
(84552076545038eb236deb91913cb8c8edcd67f34186bf987d698475e0171439)
was the first candidate to reach a genuine Termux adoption run, and it
was REJECTED there. All are preserved unchanged as audit history. v02
remediated the first five blockers; v03 fixed three further blockers; v04
fixed the deterministic focused-test stderr blocker and strengthened the
independent contract assertions; v05 corrected the 58-test count
inconsistency; v06 corrected the required-input and FAIL-lane count
statements; v07 is a Termux-portability and failure-evidence repair. The
approved eight-case per-lane outcome matrix is unchanged throughout.

## v06 genuine Termux rejection (first real on-device run)

Candidate v06 was run on a real Termux device for the first time
(first-run transcript SHA-256
e9898921a54b7eaa6c7bbe42d7300f10bb42d8c60bac66066b63442321e994d6). What
the run actually established, and nothing beyond it:
- trusted bootstrap PASS;
- Stage A baseline immutability PASS: the genuine Move 79 v27 ZIP hash
  verified, 849/849 inherited files byte-identical, 17/17 additions
  matched the allowlist, and the committed live-diff report matched;
- Stage B executed all 58 focused tests but ended with errors=1;
- the outer adoption gate returned exit 1.

The gate FAILED at Stage B and therefore never reached the fresh Rust
build, the eight-fixture runner, or the composed Move 79 regression
child. No fixture outcome, no Rust verification result, and no Move 79
regression result was established by the v06 run; those stages did not
execute.

The sole error was test_real_zip_comparison_passes_and_detects_
modification failing with "AttributeError: module 'os' has no attribute
'link'" at move80_tests.py line 781: that test cloned the candidate tree
with os.link, which the Termux Python 3.13.13 environment does not
expose. The v06 gate also printed only a truncated "Ran 58 tests /
FAILED (errors=1)" summary, hiding the failing test name and traceback
and forcing a separate diagnostic run.

## v07 changes (Termux-portability + failure-evidence repair)

1. **Portable clone, no os.link.** test_real_zip_comparison_passes_and_
   detects_modification now clones the candidate tree with a standard-
   library portable byte copy (shutil.copyfile) instead of os.link — no
   hardlinks, symlinks, reflinks, external ln or cp -l, no shared
   inodes, and the original extracted tree is never modified. It retains
   the __pycache__, rust/target and *.pyc exclusions, appends the fixed
   bytes b"tampered" to only the clone's START_HERE.md, runs the live
   comparison against the clone and requires exit 1, then proves the
   original START_HERE.md is byte-identical, the clone differs only at
   START_HERE.md, the modification is reported, and the temporary clone
   is removed. The docstring now says portable independent byte copy.
2. **Complete failure evidence.** When the focused suite returns nonzero
   (or emits stderr, skips, a wrong count, or a forbidden marker), the
   adoption gate now prints the COMPLETE focused-test stdout and stderr
   between explicit BEGIN/END markers — never truncated, no tail — plus
   the exact focused-suite exit code, before failing. Successful
   execution still requires exactly 58 tests, final OK, and no failures,
   errors, skips, or stderr bytes. An existing focused test was
   strengthened to drive the gate's real gate_dump_focused_failure
   helper over a controlled failing test and prove its full name and
   traceback survive between the markers untruncated.

The suite total stays at exactly 58 (both changes strengthen existing
tests; no test added). No fixture, fixture hash, mutation_ledger.json,
fixture_manifest.json, expected_results.json, selective checksum repair,
real-v27 comparison, approved eight-case matrix, or Rust/Python
behaviour changed.

## v06 change (two documentation truth-state repairs)

v05 correctly repaired the 58-test inconsistency but was rejected because
two packaged texts still contradicted the actual contract:
1. verify/corrupted_bundle_pack_v01/README.md said the gate takes "two
   required real inputs" while it requires three (REAL_MOVE78, REAL_705,
   REAL_MOVE79; REAL_V20 stays optional);
2. both README.md and expected_results.json's _meaning_of_case_pass said
   six of eight fixtures have a FAIL lane, while the declared matrix
   proves seven (only M80-CLEAN-001 has none).

v06 corrects both texts (README to "three required real inputs" and both
locations to "seven of the eight fixtures ... at least one lane is FAIL")
and hardens against recurrence WITHOUT increasing the suite above 58:
- an existing usage test now proves the README states "three required
  real inputs" exactly once, its invocation block names exactly
  REAL_MOVE78/REAL_705/REAL_MOVE79, and the gate's own usage validation
  exits 2 identifying all three when absent and the omitted one when each
  is individually omitted (these run before the Termux bootstrap, so they
  execute off-device);
- an existing matrix test now derives the FAIL-lane set directly from
  expected_results.json and requires exactly seven such fixtures with
  M80-CLEAN-001 the sole exception, and requires both the README and
  _meaning_of_case_pass to carry the seven-of-eight statement and not the
  obsolete six-of-eight one;
- the adoption gate's Stage B gains a trusted-Python truth-state check
  that derives the seven-count from expected_results.json and fails if
  the declared matrix, README or _meaning_of_case_pass disagree.

No per-case verdict, fixture, mutation, hash, verifier, or Rust/Python
behaviour changed. The only content edits are the two corrected prose
statements; expected_results.json's per-lane expectations are byte-for-
byte identical apart from the _meaning_of_case_pass prose.

## v05 change (documentation truth-state repair)

v04 was rejected SOLELY because verify/corrupted_bundle_pack_v01/README.md
still stated "focused tests (44)", the obsolete pre-v02 count, while the
actual loaded suite, the committed EXPECTED_TEST_COUNT.txt and the
changelog all correctly said 58 — a false packaged claim that could ship
even though the gate passed. v05 corrects the README count to 58 (the
only functional change) and hardens against recurrence:
- an EXISTING focused test (no new test; the suite stays at 58) now
  mechanically proves the three values agree: the live
  loadTestsFromModule(...).countTestCases(), the integer in
  EXPECTED_TEST_COUNT.txt, and the count parsed from the committed
  README text (exactly one match required; missing, duplicate, malformed
  or divergent fails) — all required to equal 58;
- the adoption gate's Stage B, after reading EXPECTED_TEST_COUNT.txt,
  parses the README focused-test count with the trusted interpreter and
  fails unless it equals the pinned count, so future documentation drift
  cannot hide even if the suite is modified incorrectly.

No fixture bytes, hashes, expected results, generation logic, gate
composition, or v04 runner/assertions changed.

## v04 changes (focused-test stream blocker + stronger assertions)

Decisive blocker: move80_tests.py ended with unittest.main(), whose
runner writes its progress and "Ran N tests / OK" summary to STDERR. The
gate's zero-stderr policy would reject even a fully successful run, so v03
could not pass its own adoption gate. v04 replaces the implicit
unittest.main with an explicit loader + TextTestRunner(stream=sys.stdout)
over this module's own suite (setUpModule/tearDownModule preserved, no
recursive reload), exiting 0/1 on wasSuccessful(). Verified: a successful
run now writes its summary to stdout with EXACTLY zero stderr bytes.

The gate's focused-test stage additionally requires, on stdout: the exact
"Ran <N> tests" line (N pinned in the committed EXPECTED_TEST_COUNT.txt),
a final "OK", and none of "FAILED", "errors=", "failures=" or "skipped=";
while still rejecting any focused-suite stderr bytes, any
ResourceWarning/"Exception ignored in:"/"unclosed file" diagnostic, any
skipped test, and any nonzero exit. The stderr channel is preserved as a
pure warning/error channel -- the policy was not weakened.

Strengthened independent contract assertions (all parsed from seed and
fixture bytes, never from the generator mutation table, ledger or pins):
- CHANGED EVIDENCE: differing-offset list is exactly [5]; byte 5 equals
  seed byte 5 XOR 0xFF; every other byte identical; nested declared
  checksum line byte-identical to the seed.
- BAD RECEIPT HASH: independently RECOMPUTES the seed receipt's canonical
  hash via the declared recipe (drop canonical_hash; sorted keys; compact
  separators; ensure_ascii=False; SHA-256 UTF-8) and requires it to equal
  the seed's stored value (correctness is proved, not assumed); the
  replacement is exactly 64 zeroes and differs from that recomputed value;
  exactly one receipt and one field differ.
- PATH TRAVERSAL: the expected fixture SHA-256 is encoded as a literal
  (286e137fe2fba65d...); exactly one ZIP member; exact name "../evil";
  member content is exactly empty bytes; live hash equals the literal.
- UNKNOWN SCHEMA: independently constructs the expected report bytes
  (parse seed report, replace only companion_cli_version with "9.9.9",
  serialize via the declared canonical recipe) and requires the fixture
  report bytes to equal them exactly, with every other field unchanged.
- DUPLICATE RECEIPT: independently constructs the expected sentinel_run
  (append an exact copy of the seed's final receipt) and serializes it via
  the declared _dump recipe, requiring the fixture bytes to equal that
  exactly -- not merely parse to an equivalent object.
- LEAKY CHILD: explicitly proves the controlled child exits 0, emits
  non-empty stderr, and is rejected by the gate-side stderr policy; a new
  test proves a successful unittest child writes its summary to stdout
  with exactly empty stderr.

The committed EXPECTED_TEST_COUNT.txt (value 58) is a new allowlisted
addition.

## v03 changes (three further review blockers)

1. **Authorised bad-receipt mutation.** v02 wrongly changed
   receipts[0].reason_code and merely left canonical_hash stale — not
   the authorised fixture. v03 corrupts exactly one receipt's
   canonical_hash: receipt index 0 is selected deterministically, its
   canonical_hash is replaced with the fixed deterministic invalid value
   0*64, and every other field of that receipt and every other receipt
   are byte/JSON-value identical to the seed. Re-serialized with the
   declared _dump byte form; only the strict selective enclosing-checksum
   closure applied. Lanes preserved (Python PASS/0 companion completed;
   Rust FAIL/1 RECEIPT_HASH_RECOMPUTATION_MISMATCH at canonical_recompute).
   An independent semantic test parses seed and fixture and proves the
   receipt count is unchanged, exactly one receipt differs, exactly one
   field differs, that field is canonical_hash, all payload fields
   (including reason_code) are identical, and the replacement is
   deterministic and differs from both the seed value and the correct
   recomputation — asserted independently of the generator's mutation
   table and the ledger. The fixture hash changed accordingly.
2. **Resource-leak removal and mechanical warning-clean policy.** The
   two `open(...).read()` reads in integrity_check.py are now
   context-managed. The gate captures focused-test and integrity-check
   stdout and stderr in SEPARATE files, runs integrity under
   `-W error::ResourceWarning`, prints any stderr before failing, and
   fails on any stderr bytes or on the substrings `ResourceWarning`,
   `Exception ignored in:` or `unclosed file` — never treating exit 0 as
   proof of warning-cleanliness. A regression test drives a controlled
   child that leaks a handle yet exits 0 and proves the stderr policy
   rejects it; a direct test proves the real clean integrity run emits
   exactly zero stderr bytes under `-W error::ResourceWarning`.
3. **Committed diff report bound to the live real-v27 comparison.** The
   gate now runs check_inherited_vs_zip.py against the hash-verified
   REAL_MOVE79 zip with `--report <tracked tmp>`, requires checker exit
   0, prints the complete live report into the transcript, and requires
   the committed MOVE_80_ALLOWLIST_DIFF_REPORT.txt to be byte-identical
   to it (failing on any difference). Tests prove a tampered committed
   report and a stale-count report both differ from the live comparison,
   and that the genuine committed report equals it.

Additionally, the focused suite now carries INDEPENDENT semantic
contract assertions for all eight fixtures (parsed from seed and fixture
bytes, encoded as literals, never regenerated from the implementation
under test): clean = exact seed copy; missing-manifest = only
companion_report.json removed; changed-evidence = one fixed byte offset
with the nested declared hash retained; bad-receipt = only one
canonical_hash changed; duplicate-receipt = final receipt appended as an
exact duplicate with no prior receipt changed; malformed-json = exact
deterministic truncation; path-traversal = single ../evil entry with
pinned bytes; unknown-schema = only companion_cli_version changed to
9.9.9 after canonical parse/serialize.

## What Move 80 adds

A corrupted-bundle test pack (`verify/corrupted_bundle_pack_v01/`): one
clean control plus seven deliberately corrupted fixtures, generated
deterministically from the pinned frozen clean seed
(`freeze_record/python_behaviour_freeze_v01/reference_bundle`), executed
against the adopted verifiers, and evaluated against DECLARED per-lane
expectations grounded in a Phase 1 contract inventory of the actual
adopted Move 79 v27 behaviour (accepted at hostile review before
implementation).

Corruption classes: missing manifest, changed evidence bytes, bad
receipt hash, duplicated receipt, malformed report JSON, ZIP path
traversal, declared-but-unsupported schema version, plus the clean
control.

## v02 changes (the five review blockers)

1. **Approved seed pin restored.** The APPROVED contract-inventory pin
   `seed_tree_hash_v0` =
   70e6e975b3d5fab8d4a513573ef4d0d12ea0ca697ad287d46ea11b789abe7a24 is
   reinstated with its exact normalization (files only, sorted walk;
   per file: relpath bytes, NUL, raw file bytes, NUL) and is
   reproduced from seed bytes by generator, integrity checker and
   tests. The v01 value 3a7ad566... is retained ONLY as the separately
   named secondary `entry_tree_hash_v1` (fixture-identity algorithm).
   Tests fail if either value is assigned to the wrong algorithm name.
2. **Selective checksum repair.** The frozen seed contains one
   pre-existing stale checksum entry (bundle_checksums.txt line 1,
   case_manifest.json). v01's use of the adopted global fixpoint
   repair silently rewrote it in four fixtures. v02 implements a
   fixture-local SELECTIVE dependency-closure repair: only entries
   declaring the principal mutated file, entries declaring a checksum
   file changed by that step, and the strictly required enclosing
   chain. The stale line is byte-identical to the frozen seed in every
   fixture (machine-checked per fixture); the mutation ledger declares
   every repaired line with file, line number, entry, old/new digest
   and reason, plus the preserved stale entry.
3. **Baseline immutability bound to the real v27 ZIP.** The
   self-authenticating candidate-contained inventory is removed. The
   gate now REQUIRES `REAL_MOVE79=<path to the adopted v27 zip>`,
   canonicalises it, verifies its SHA-256 with the trusted sha256sum
   (4a95767a3f68ca812c1d543894b65183b82d56f3f8f56e9af61b82c19de1f26b),
   safety-inspects the archive (duplicate names, traversal, absolute
   paths, symlinks, single root), compares every inherited candidate
   file DIRECTLY against the verified member bytes, requires additions
   to equal the allowlist exactly, and generates the diff report from
   that real comparison (`check_inherited_vs_zip.py`). Tests prove a
   wrong-hash zip is rejected, synthetic attack zips are detected, and
   modifying one inherited file fails the direct comparison.
4. **Complete Move 79 regression evidence.** The gate still invokes
   the exact adopted `tools/check_move79_instrument_adoption.sh`
   unmodified, but now retains its COMPLETE output in the Move 80
   transcript (no tail), mechanically reprints the declared divergence
   IDs from the adopted gate bytes, and requires every fact — 63/63
   harness tests, 73/73 gate-unit tests, all 85 cases, 74 agreement, 6
   Python-only, 3 Rust-only, exactly 2 known divergences with exactly
   the two declared IDs, no unmapped reasons, no missing diagnostics,
   gate PASS, SYSTEM_AGREEMENT_RESULT: FAIL with
   BEHAVIOURAL_DIVERGENCE_DETECTED, child exit 0 — via
   `check_move79_evidence.py` (unit-tested: each missing or altered
   fact fails).
5. **Traversal safety proven at the real ../evil destination.** The
   deterministic archive entry `../evil` is retained; the runner now
   executes both archive boundaries (ZIP passed directly, never
   pre-extracted) in fresh sandboxes twice: a creation test proving
   `sandbox/evil` (the entry's real resolved destination) stays
   absent, and an overwrite/deletion test pre-creating it as the
   outside sentinel with recorded bytes and mode and proving it
   survives byte-identically. Tests prove a boundary that creates,
   overwrites or deletes the destination is detected, and all
   sandboxes and temp files are removed.

## Contract honesty properties

- Lane results are stored separately (python_expected / rust_expected /
  archive_oracle_expected) with per-case classifications; different lane
  verdicts are never collapsed into one fake common verdict.
- `MOVE_80_REQUIRED_CASES: 8/8 PASS` means all declared per-lane
  expectations were met — never that corrupted bundles verified
  successfully. The adopted Rust verifier cannot emit bundle PASS at
  all; its clean-bundle ceiling INCONCLUSIVE/3 is never described as
  PASS.
- Documented capability limits are asserted, not hidden: Rust
  evidence-byte blindness, Python receipt blindness, Python schema-field
  blindness (see the pack README).
- The known per-lane divergence pattern (malformed report JSON) and the
  manifest-boundary reason-class split are recorded honestly; the frozen
  85-case agreement corpus is untouched.
- Every declared Rust/archive reason code is required to exist in the
  adopted reason map (no invented codes), and every declared stage must
  equal the adopted reason map's stage for that code.

## Architecture (as ruled at review)

- The focused runner `run_move80.py` takes a REQUIRED `--rust-bin`
  absolute path and executes exactly that binary: no PATH search, no
  Cargo, no builds, no default binary, no trust claim.
- The adoption gate `tools/check_move80_corrupted_bundle_adoption.sh`
  owns the trusted Termux bootstrap, LD_PRELOAD validation, trusted
  toolchain resolution, clean-target removal, fresh build, version
  verification, stale-executable rejection and absolute-path resolution,
  then hands that path to the runner and requires the runner-reported
  binary SHA-256 to equal the freshly built binary.
- Composition, not duplication: the gate sources the adopted
  `tools/gate_bootstrap.sh` and `tools/gate_lib.sh` unchanged and
  invokes the COMPLETE adopted Move 79 regression gate as a child
  process (see v02 change 4 for the retained evidence).
- The generator composes the adopted corpus helpers (entry-resolution
  semantics mirrored exactly for the selective repair) and the frozen
  Move 71 generator by read-only import; the traversal ZIP is
  byte-identical to the TERMUX-confirmed corpus case.

## Integrity machinery

- Deterministic generation proved by building twice into independent
  fresh directories and comparing every byte (gate stage C and
  `integrity_check.py`).
- Pinned fixture hashes, a line-level mutation/repair ledger, and a
  fixture manifest — all required to be exactly reproducible from the
  generator on every run; declared line repairs re-verified from seed
  and fixture bytes.
- Seed immutability: every seed file checked against the frozen Move 71
  sidecar on every run; both named seed pins checked; fixtures built
  only from fresh copies.
- Additions-only allowlist enforced DIRECTLY against the verified real
  v27 ZIP bytes (v02 change 3). `MOVE_INDEX.md` and
  `CURRENT_RELEASE_STATE.md` are untouched: no existing checker
  mechanically requires a Move 80 entry (verified by running the
  adopted doc checkers against this candidate).
- the focused tests: `--rust-bin` handoff discipline (including a
  poisoned-PATH no-lookup test), wrong verdict / reason / stage / exit /
  stderr / malformed / incomplete output, signal termination, timeout,
  missing fixture, duplicate fixture ID, duplicate filename,
  fixture-hash mismatch, undeclared mutation, seed mutation,
  nondeterministic generation, seed-pin algorithm binding,
  selective-repair closure exactness and stale-line preservation,
  baseline-zip binding (wrong hash, attack zips, modified inherited
  file), Move 79 evidence completeness, the ../evil destination
  creation/overwrite/deletion tests, temporary-directory cleanup, and
  original/reversed/shuffled order identity of the canonical output.

## Files added (complete list = allowlist)

- `CHANGELOG_MOVE_80.md` (this file)
- `tools/check_move80_corrupted_bundle_adoption.sh`
- `verify/corrupted_bundle_pack_v01/` — README.md, generate_fixtures.py,
  author_pins.py, fixture_hashes.json, mutation_ledger.json,
  fixture_manifest.json, expected_results.json, integrity_check.py,
  run_move80.py, move80_tests.py, allowlist.json,
  check_inherited_vs_zip.py, check_move79_evidence.py,
  MOVE_80_ALLOWLIST_DIFF_REPORT.txt

No inherited Move 79 v27 path was modified or removed. `src/`, `rust/`,
`freeze_record/`, `verify/agreement_harness_v01/`, all adopted gates,
tools, artifacts and evidence are byte-identical to the adopted
baseline (zip sha256
4a95767a3f68ca812c1d543894b65183b82d56f3f8f56e9af61b82c19de1f26b).

## Evidence status

Off-device, this candidate has: all the focused tests passing (including
the direct real-zip comparison, supplied via M80_BASELINE_ZIP), fixture
integrity PASS with stale-line preservation and line-repair
re-verification, two-generation byte identity PASS, the zip-bound
inherited comparison PASS against the verified real v27 artifact, and
the runner exercised end-to-end with the real frozen Python lane plus a
controlled contract executable (permitted in tests only, as ruled). The
Rust-side verdicts for the missing-manifest, changed-evidence
(blindness), duplicate-receipt and unknown-schema fixtures, and gate
stages D–F as a whole, REQUIRE the Move 80 Termux adoption run for
confirmation.
