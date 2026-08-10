# CHANGELOG — Move 85: Rust audit pack v1

Status: CANDIDATE v08. Not adopted. Not run on Termux.

## v08 changes (no active identifier names a superseded candidate)

The rejected candidate v07
(443c66e9b79b7958779ae6eed631b41cd920f15d96b307e2c6003e36dbbb0af2) is
preserved unchanged as audit history.

v07's publication ordering was correct, but its active regression section
still carried a heading reading "the active identity is exactly v03" and a
test method named `test_the_active_transcript_identity_is_v03`. The test
**body** checked the right value, so nothing failed functionally — but the
name and heading asserted that a superseded candidate was current, and at
Move 85 that would be frozen into adopted handoff evidence.

**Active identifiers are now checked separately from active values**,
because a name can lie while the body tells the truth. The heading is
version-neutral, and these names were corrected:

- `test_the_active_transcript_identity_is_v03` →
  `test_the_active_transcript_identity_matches_current_candidate`;
- `test_the_v01_and_v02_identities_are_recorded_as_rejected` →
  `test_superseded_identities_are_recorded_as_rejected`;
- `test_the_scanner_catches_the_v01_wording` →
  `test_the_scanner_catches_the_reported_stale_wording`;
- `test_the_stale_identity_scanner_catches_the_v02_defect` →
  `test_the_stale_identity_scanner_catches_a_reported_defect`.

The renamed current-identity test now also asserts that
`ACTIVE_TRANSCRIPT` is **derived from** `ACTIVE_CANDIDATE`, so the two
cannot drift apart.

A complete stale-active-identity audit ran over all ten additions. Two
matches were left alone as legitimate:
`test_real_move84_is_documented_as_move84_v07` and
`test_the_baseline_hash_pin_is_move84_v07` — that `v07` is **Move 84's**
adopted version, not this move's candidate number.

Four tests added: no active identifier in any addition names a superseded
candidate; the scanner is proven to catch the exact v07 wording; it is
proven to leave `move84_v07` and historically-labelled names alone; and
the active constants are internally consistent and agree with the
changelog's `Status: CANDIDATE` line.

Everything else from v07 is preserved: publication ordering, fail-closed
rollback, post-publication `SHA256SUMS` verification, the staged-versus-
published tree comparison, `pack_1` publication with `pack_2` private,
Move 84 v07 as sole baseline, `REAL_MOVE83` as external dependency, the
exact divergence IDs, no Rust change, zero inherited modifications, and no
new platform claims.

Because five tests were added, the discovered count genuinely changed and
`EXPECTED_TEST_COUNT.txt` is updated from 127 to 132. The renames alone
did not change it.

Suite (active): 132 tests.

## v07 structure (retained)

## v07 changes (terminal-marker ordering)

The rejected candidate v06
(14b4b71ec0a6612d7c00522dfee2020b0a6599aa375ec919c852ed291585160f) is
preserved unchanged as audit history.

**v06 had no possible successful execution path.** The guard

```
if [ "${AUDIT_PACK_PUBLISHED:-}" != "PASS" ]; then ... die
```

sat in the final-marker block, which ran **before** Stage P — and Stage P
held the only assignment of that variable. The gate therefore had to die
before publication could ever run. The terminal
`MOVE_85_AUDIT_PACK_ADOPTION_GATE: PASS` marker was also emitted before
publication, which would have violated the accepted contract even without
the variable bug.

The v06 publication implementation itself was correct; only its position
was wrong. **Stage P has been moved to sit before the final-marker
block**, giving the required sequence:

1. all substantive verification stages;
2. package hygiene;
3. supporting binary and provenance published;
4. the already-verified `pack_1/audit_pack_v1` published to
   `$MOVE85_OUTPUT_DIR/audit_pack_v1/`;
5. published `SHA256SUMS` verified from the published bytes;
6. published tree compared against verified `pack_1`;
7. `AUDIT_PACK_PUBLISHED=PASS`;
8. the final Move 85 markers;
9. `MOVE_85_AUDIT_PACK_ADOPTION_GATE: PASS` and `exit_code: 0`;
10. `exit 0`.

Verified in the packaged bytes by line number: Stage P at 1651, the
assignment at 1722, the guard at 1745, the terminal marker at 1749, and
`exit 0` at 1752.

Ten tests added that read the gate as an ordered sequence of statements,
so an unreachable or out-of-order success path fails off device: every
ordering anchor exists; the guard cannot precede the assignment — the
exact v06 defect; the assignment follows Stage P and both
post-publication verifications; the terminal marker follows publication,
the assignment and the guard; **no line announces adoption success before
Stage P**; the final-marker block follows Stage P; every `exit 0` follows
the terminal marker; each publication failure path reaches `die`; and
`die` is fail-closed.

The v06 publication implementation is otherwise untouched: verified
`pack_1` is the source, `pack_2` remains determinism-only and is never
published, a pre-existing target is rejected, published core files are
checked, `SHA256SUMS` is recomputed against published bytes, the published
tree is compared against staged `pack_1`, and the binary and provenance
remain secondary output.

For that superseded candidate the active identity was its own
`MOVE_85_V07_TERMUX_GATE.txt`, with the
stale-active-identity audit re-run across all ten additions.

No Rust change, no broadened scope, no weakened staging safety, no altered
adopted authority, no hidden divergence, no new platform claim.

Suite (historical, candidate v07): 127 tests.

## v06 structure (retained)

## v06 changes (the audit pack is actually published)

The rejected candidate v05
(516848157ad0e1a53ebc2c1a22a90b5a92a8c0f516cfcaecc665be6761bb1b19) is
preserved unchanged as audit history.

**The gate could report PASS while the Move 85 roadmap deliverable was
never published.** The pack was built and verified in private staging, the
publication stage published only the standalone binary and its provenance,
and the staged pack was discarded at cleanup. The supporting measurement
machinery was being shipped in place of the deliverable.

A publication stage now runs **after every substantive check** — candidate
identity and source binding, inherited immutability, clean builds and
tests, controlled behaviour, pack generation, representation determinism,
the focused suite, the complete adopted Move 84 regression, and package
hygiene — and publishes the **already-verified first generation** from
`$_AP_DIR/pack_1/audit_pack_v1/` to `$MOVE85_OUTPUT_DIR/audit_pack_v1/`.

It is fail-closed:

- the publication target must not already exist, checked by both the gate
  and the publisher;
- **nothing is regenerated** during publication — regenerating would ship
  an artifact no check had passed. `pack_2` exists solely for the
  determinism comparison and is never published;
- after copying, the published tree is verified against the staged source
  on every path, entry type, mode and byte;
- `SHA256SUMS` is recomputed from the **published** bytes and required to
  both cover and match them;
- a failed verification **rolls the partial publication back** and reports
  failure;
- the gate then independently re-verifies the published pack, and the
  terminal `MOVE_85_AUDIT_PACK_ADOPTION_GATE: PASS` marker is guarded so
  it is unreachable unless `AUDIT_PACK_PUBLISHED=PASS`.

The standalone binary and its provenance **remain** in the output
directory alongside `audit_pack_v1/`. The README and handoff now state
plainly that the audit pack is the Move 85 roadmap deliverable and the
binary is supporting measurement machinery — how the pack's measurements
were taken — and not the deliverable.

Fourteen tests added: the gate publishes `audit_pack_v1`; publication
follows every substantive check; `pack_2` is never published; nothing is
regenerated; PASS is guarded and unreachable with only the binary present;
the gate verifies the published tree and its `SHA256SUMS` after
publication; a pre-existing target is rejected by both gate and
publisher; publication produces a byte-identical tree; published
`SHA256SUMS` covers and verifies the pack; a corrupt source rolls back;
relative paths are refused; and the documentation names the deliverable.

The v05 staging repair is untouched. Everything else from v04 and v05 is
preserved: Move 84 v07 as sole baseline, `REAL_MOVE83` as the external
adopted Move 83 v13 child dependency, the exact divergence IDs from the
adopted authority, claim-manifest-not-authority semantics, the
source-level versus empirical no-PASS distinction, the audit-pack-only
determinism claim, zero inherited modifications, no Rust changes, no new
platform claims, and the complete Move 84 regression.

Suite (historical, candidate v06): 117 tests.

## v05 structure (retained)

## v05 changes (staging-directory ownership)

The rejected candidate v04
(3e4724a5f42a2a93b2363d23d473fc6425bebaae4b1f120e62b5730e7aad42d5)
reached a GENUINE first-run Termux gate and is preserved unchanged as
audit history, together with its transcript
`MOVE_85_V04_TERMUX_GATE.txt`
(6466d331bf16becf7e9502876b5fcea41e8e07f122d8f590f844fde363b1eb61),
gate exit 1, run directory `$HOME/m85_v04_internal_20260810_090922`.

That run established a great deal before failing: source binding, output
directory, the inherited check with 907/907 Move 84 v07 files
byte-identical and exactly ten additions, clean release and debug builds,
the Rust unit suite at 133/133, binary inspection, standalone execution,
the full corpus at 79/79, Move 81 adapter equivalence at 79/79, hostile
edge equivalence, the usage contract, the deterministic audit fixtures,
the two adopted divergence IDs read from the adopted Move 79 authority,
and `adopted_facts.json` checked against the adopted authorities.

**The gate and the builder disagreed about who owns the staging root.**
`build_audit_pack.py` requires `--staging` to be an absolute,
already-existing directory. The gate passed `$_AP_DIR/pack_1` and
`$_AP_DIR/pack_2` without creating either, so the builder refused with a
usage error.

The builder's fail-closed contract is **kept**, not weakened. The gate now
owns creation: a helper creates each staging root and requires it to be
absolute, not already present, empty after creation, and inside the
gate-owned staging area. The builder still creates only its own
`audit_pack_v1/` child beneath the supplied root and never creates an
arbitrary caller-supplied parent.

Why the off-device suite missed it: my tests created the staging directory
themselves before invoking the builder, so they exercised the builder but
never the gate's own behaviour. The producer and the consumer had not
actually met. The new tests check the gate's ordering directly, and the
whole-file rule means a third staging root cannot be added without being
created first.

Twelve tests added: a missing, relative, or absolute-but-nonexistent
`--staging` is rejected — that last one being the exact v04 failure — an
existing absolute root is accepted; the builder still fails closed; the
gate creates `pack_1` before the first invocation and `pack_2` before the
determinism run; **every** staging root the gate passes is created first;
roots are absolute, private and empty; the builder does not create the
supplied parent; the determinism comparison is still required; and
publication still follows the substantive checks.

For that superseded candidate the active identity was its own
`MOVE_85_V05_TERMUX_GATE.txt`, with the
stale-active-identity audit re-run across all ten additions.

Everything else from v04 is preserved: `REAL_MOVE84` as the sole baseline,
`REAL_MOVE83` as the externally verified Move 83 v13 dependency, the exact
predecessor child contract, zero inherited modifications, the ten-file
allowlist, no Rust change, the exact divergence IDs, the
claim-manifest-not-authority rule, the empirical/source-level no-PASS
distinction, determinism limited to the pack representation, and no new
platform claims.

Suite (historical, candidate v05): 103 tests.

## v04 structure (retained)

## v04 changes (Move 84 child input contract)

The rejected candidate v03
(a5ca84ddcdc9c5a42a13ce9fde21397f93b5d6f8104b2bf095f8f1ff5629d854) is
preserved unchanged as audit history.

**The Move 84 child was not given `REAL_MOVE83`.** The adopted Move 84
v07 gate's mandatory inputs are `MOVE84_CANDIDATE_ZIP`,
`MOVE84_CANDIDATE_SHA256`, `MOVE84_OUTPUT_DIR`, `REAL_MOVE83`,
`REAL_MOVE81`, `REAL_MOVE80`, `REAL_MOVE79`, `REAL_MOVE78` and
`REAL_705`. v03 forwarded every one except `REAL_MOVE83`, and its Stage J
comment documented the contract as if that input did not exist. A genuine
child would have terminated on its own usage contract before establishing
the regression.

Repaired:

- `REAL_MOVE83` is now a **mandatory** Move 85 input, checked before any
  child execution;
- it obeys the same absolute-path rule as the other `REAL_*` authorities;
- it is **independently verified** against the adopted Move 83 v13
  authority `aa06feb8…975a6c` before the child runs, and refused if it
  lives inside the candidate tree — so no candidate-contained copy can
  silently substitute for the external authority;
- it is passed explicitly to the child as `REAL_MOVE83="$REAL_MOVE83"`;
- it is documented as **a dependency the Move 84 child requires, not the
  Move 85 baseline** — the baseline remains `REAL_MOVE84` / adopted
  Move 84 v07;
- the Stage J contract documentation now lists the adopted Move 84 gate's
  exact mandatory inputs.

Regression coverage added, with the contract **read from the adopted
Move 84 gate rather than restated**: the adopted child genuinely requires
`REAL_MOVE83`; every input that gate requires is supplied; `REAL_MOVE83`
is mandatory, absolute-path-checked, and required before the child runs;
it is pinned to the adopted Move 83 v13 hash and verified before
invocation; a candidate-internal path is refused; the Move 85 baseline
remains `REAL_MOVE84`; `REAL_MOVE83` is documented as a dependency; and
the documented contract lists every input the adopted gate names.

For that superseded candidate the active identity was its own
`MOVE_85_V04_TERMUX_GATE.txt`, with the same
stale-active-identity audit re-run across all ten additions and the
scanner extended to reject superseded v03 identities from active code.

Nothing else changed. No Rust, no inherited file, no scope broadening, no
weakened check, no altered divergence state, no new platform claim.

Suite (historical, candidate v04): 91 tests.

## v03 structure (retained)

## v03 changes (active candidate identity)

Candidate v02
(2fba2ccec5dd616aa68fc9f52d622da25cb1210b5b17562b4e61cf5ec5a0fe64) was
REJECTED pre-Termux and is preserved unchanged as audit history.

The rejected candidate v02 gate still carried a superseded value in
`MOVE85_TRANSCRIPT_NAME`, naming the historical v01 transcript. It was
carried forward unchanged when the candidate was rebuilt, so v02 could not
be used for a genuine first run. **Bumping the single-sourced
identity is part of rebuilding a candidate, not an afterthought** — that
is now enforced rather than remembered.

A complete stale-active-identity audit was run across all ten additions
for both superseded candidate numbers, their transcript names, their
archive filenames and their extracted-directory forms. Exactly two
active occurrences existed, both in the gate: the assignment itself and
its explanatory comment. Both are corrected; the comment now reads as an
explicitly historical note. Every other match is in this changelog and is
classified historical.

The active identity is now `MOVE_85_V03_TERMUX_GATE.txt`, defined once and
referenced by variable, appearing exactly once in active gate code.

Regression coverage added, in the four areas required:

1. the then-active transcript identity, for that superseded candidate,
   was exactly its own `MOVE_85_V03_TERMUX_GATE.txt`,
   appears once in active code, and provenance references the variable;
2. no superseded transcript identity survives in active gate code, and a
   scanner over **every** Move 85 addition rejects any stale candidate
   identity on a line that does not classify it as historical — proven to
   catch the exact v02 defect;
3. the identity cannot drift: the candidate version is parsed from the
   changelog's `Status: CANDIDATE vNN` line and the gate's transcript name
   must be derived from it, so a rebuild that forgets to bump one fails;
4. historical references remain permitted where classified, and both
   superseded candidate hashes are recorded as rejected.

Nothing else changed. No Rust, no inherited file, no scope broadening, no
weakened check, no altered divergence state, no new platform claim.

Suite (historical, candidate v03): 80 tests.

## v02 structure (retained)

## v02 changes (gate purpose and predecessor statements)

Candidate v01
(5dd00c805333ee151099406c5b4cce61ea41e207d67a512892e0bed129d15bc2) was
REJECTED pre-Termux and is preserved unchanged as audit history.

The substantive Phase 1 corrections were accepted, but the gate — derived
from the adopted Move 84 gate — still described itself as the
tamper-and-detect demo gate, described its deliverable as a standalone
executable, and named Move 83 v13 as both the Move 85 baseline and the
child gate. The hashes bound correctly; the statements did not.

A complete stale-language audit was run over all ten additions. Only the
gate carried stale statements. The two matches elsewhere are legitimate
and were left alone: the handoff describing the Move 84 tamper-and-detect
demonstration, and the inherited checker's note about Move 83's single
additive `main.rs` modification.

Corrected in the gate:

- the header, now `MOVE 85 RUST AUDIT-PACK ADOPTION GATE`;
- the purpose, which now states that **the deliverable is the generated
  audit pack** and that a standalone executable is built as supporting
  machinery — how the measurements are taken — and is **not** the Move 85
  roadmap deliverable;
- the `REAL_MOVE84` documentation, now naming the adopted Move 84 v07 zip
  as the sole Move 85 baseline;
- Stage B and its failure text; the byte-authority comments;
- Stage J throughout — its banner, run directory, staging, output
  directory, helper checks, retained-transcript headings and diagnostics
  now all name the Move 84 child;
- the `MOVE_84_REGRESSION_GATE` documentation, now describing the
  complete adopted Move 84 v07 child gate.

**The child marker set was wrong in the same way, and is now derived
mechanically.** v01 demanded nine `MOVE_83_*` stage markers of the Move 84
child. The adopted Move 84 gate emits `MOVE_84_*` stage markers and, from
its own child, `MOVE_83_REGRESSION_GATE`. The required set is now built by
enumerating that gate's real emission sites — `echo "<NAME>: PASS"` or
`echo "<NAME>: $VAR"` with `VAR` assigned `PASS` — yielding ten
`MOVE_84_*` markers plus the inherited `MOVE_83_REGRESSION_GATE`, with
none impossible. This is the Move 84 v06 failure, caught here before any
device run.

Fourteen tests added: the header, deliverable, `REAL_MOVE84`, hash pin,
Stage B and Stage J statements; a whole-file scanner for stale subject and
purpose statements, itself proven to catch the reported v01 wording and to
leave legitimate Move 83 dependency and Move 84 demonstration references
alone; and marker checks requiring every demanded marker to be emittable
by the adopted Move 84 gate, the terminal marker to be that gate's own,
only the inherited regression marker to be required, and no `MOVE_83_*`
stage marker to be demanded.

Mutation-tested: reinstating the v01 header and baseline wording fails
three of these.

Nothing else changed. No Rust, schema, fixture or inherited-file change;
no scope broadening; no weakened check; no new platform claim; no change
to the accepted truth semantics.

Suite (historical, candidate v02): 71 tests.

## v01 structure (retained)

## Roadmap objective

> **85 — Rust audit pack v1** — Package clean, tampered, and corrupted
> bundles with Python expected outputs, Rust outputs, instructions, and
> known limits.

## Adopted baseline

- `project-witness-MOVE_84_candidate_v07.zip`
- SHA-256:
  `0c06017a871adc23b50bdfda272a30fb6843dbb50fbb4632284b037090e7e880`
- Moves 71–84 adopted. Move 85 is **additive only**: 907/907 inherited
  files byte-identical, `modified_paths` empty, ten additions.

## Binding corrections implemented

**1 — finite testing is not reachability.** Two separate claims replace
the earlier overclaim. The *source-level contract* is that the adopted
Rust source declares exactly two verdict constants, `VERDICT_FAIL` and
`VERDICT_INCONCLUSIVE`, with no PASS constant — machine-checked by
enumerating `const VERDICT_*` from the adopted `main.rs`. The *empirical*
claim is only that no Rust PASS was observed on the measured surfaces.
Each carries an explicit `does_not_establish` note, and a test scans the
manifest, README and handoff for any global-reachability phrasing.

**2 — `adopted_facts.json` is never an authority.** It declares itself a
claim manifest, every entry names the external authority and the checking
method, and the gate compares it *against* those authorities: the
externally supplied adopted archive with its externally pinned hash, the
adopted Move 79 gate bytes, the adopted `main.rs` bytes, and fresh
execution. No value is established because the file contains it.

**3 — the exact divergence IDs are preserved and machine-checked.** The
gate reads `EXPECT_DIV_IDS` out of the adopted Move 79 gate at run time
and requires the manifest to name both `stage_manifest_json_invalid` and
`stage_report_field_missing_repaired`. The generic
`SYSTEM_AGREEMENT_RESULT: FAIL` markers remain required in the child
transcript.

**4 — the publication contract is defined.** The pack is a
gate-generated artifact in `MOVE85_OUTPUT_DIR/audit_pack_v1/`, not a
source file, with `MANIFEST.json`, `INSTRUCTIONS.md`, `KNOWN_LIMITS.md`,
`SHA256SUMS`, `bundles/<case_id>/` and `observed/<case_id>/` holding each
lane's captured stdout and its exit code and stderr byte count. The
manifest labels `observed/` as authoritative measurement and the two
documents as explanatory text. It is assembled in private staging and
copied into place only after every check passes; a failing check publishes
nothing, and an existing target is refused.

**5 — the determinism boundary is explicit.** `MANIFEST.json`,
`INSTRUCTIONS.md`, `KNOWN_LIMITS.md` and `SHA256SUMS` regenerate
byte-for-byte. The manifest carries no timestamp, duration, temporary
path, random name or run-directory identity; paths are relative and lists
sorted. The manifest states in its own `determinism_scope` field that this
is about the pack representation and is **not** a reproducible-build
claim.

**6 — status vocabulary distinguishes provenance.** Seven statuses:
`historically_established`, `freshly_reproduced_by_move_85`,
`established_android_termux_aarch64_only`, `source_level_contract`,
`known_limitation`, `unestablished`, `not_claimed`. A flat `established`
label is forbidden and a test enforces its absence.

**7 — historical values are verified, not asserted.** The baseline hash is
recomputed from the externally supplied artifact and compared with the
externally pinned value; the inherited file count is counted from that
archive rather than quoted; the gate takes the expected hash as an input.

**8 — the handoff states its scope up front.** Its opening names itself
supplemental to Moves 71–85, names the four Part One documents, and says
they were deliberately not rewritten and are not retroactively altered.

## Files added (10)

- `HANDOFF_MOVES_71_TO_85.md`
- `CHANGELOG_MOVE_85.md`
- `tools/check_move85_audit_pack_adoption.sh`
- `verify/audit_pack_v01/README.md`
- `verify/audit_pack_v01/adopted_facts.json`
- `verify/audit_pack_v01/build_audit_pack.py`
- `verify/audit_pack_v01/check_move85_inherited.py`
- `verify/audit_pack_v01/allowlist_move85.json`
- `verify/audit_pack_v01/audit_pack_tests.py`
- `verify/audit_pack_v01/EXPECTED_TEST_COUNT.txt`

No inherited file is modified. No Rust, schema, fixture, adopted gate or
adopted document changes. No GitHub release. No new platform support.
The two adopted divergences are preserved and visible.

## What is NOT established off device

This environment has no Rust toolchain, so the adopted verifier is neither
built nor executed here. The Python lane IS genuinely executed. The Rust
lane is exercised end-to-end through the real pack builder using a
stand-in verifier, which proves the builder's logic and establishes
nothing about the adopted binary. Only the on-device gate establishes
that.

Suite (historical, candidate v01): 57 tests.

## Not adopted

- **v01** — `5dd00c805333ee151099406c5b4cce61ea41e207d67a512892e0bed129d15bc2`
  — REJECTED pre-Termux: stale gate purpose and predecessor statements.
  Never run on Termux. Preserved unchanged as audit history.
- **v02** — `2fba2ccec5dd616aa68fc9f52d622da25cb1210b5b17562b4e61cf5ec5a0fe64`
  — REJECTED pre-Termux: stale active transcript identity. Never run on
  Termux. Preserved unchanged as audit history.
- **v03** — `a5ca84ddcdc9c5a42a13ce9fde21397f93b5d6f8104b2bf095f8f1ff5629d854`
  — REJECTED pre-Termux: the Move 84 child was not given REAL_MOVE83.
  Never run on Termux. Preserved unchanged as audit history.
- **v04** — `3e4724a5f42a2a93b2363d23d473fc6425bebaae4b1f120e62b5730e7aad42d5`
  — REJECTED after a genuine first-run Termux gate (exit 1): the gate
  passed staging roots it had not created. Transcript
  `MOVE_85_V04_TERMUX_GATE.txt`, SHA-256
  `6466d331bf16becf7e9502876b5fcea41e8e07f122d8f590f844fde363b1eb61`.
  Preserved unchanged as audit history.
- **v05** — `516848157ad0e1a53ebc2c1a22a90b5a92a8c0f516cfcaecc665be6761bb1b19`
  — REJECTED pre-Termux: the audit pack was never published. Never run on
  Termux. Preserved unchanged as audit history.
- **v06** — `14b4b71ec0a6612d7c00522dfee2020b0a6599aa375ec919c852ed291585160f`
  — REJECTED pre-Termux: the terminal PASS guard ran before the
  assignment, leaving no successful path. Never run on Termux. Preserved
  unchanged as audit history.
- **v07** — `443c66e9b79b7958779ae6eed631b41cd920f15d96b307e2c6003e36dbbb0af2`
  — REJECTED pre-Termux: an active test name and heading falsely
  identified a superseded candidate as current. Never run on Termux.
  Preserved unchanged as audit history.
- **v08** — this candidate, packaged for independent hostile
  packaged-byte review. It has **not** been run on a real Termux device
  and is **not** adopted.
