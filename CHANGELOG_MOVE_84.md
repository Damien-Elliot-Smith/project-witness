# CHANGELOG — Move 84: Tamper-and-detect demo

Status: CANDIDATE v07. Not adopted. Not run on Termux.

## v07 changes (child markers derived from the adopted gate)

Candidate v06
(a3c23067920addecc643bb767c6b455d77d24e13d8815a4911bc7ee4d023e782)
FAILED its genuine first-run Termux adoption gate and is preserved
unchanged as rejected audit history, together with its transcript
`MOVE_84_V06_TERMUX_GATE.txt`
(ab56b88259a375ec708d2efad8da89125b34c9e14c5b53ba6938d8b42415fa4a),
genuine gate exit code 1, run directory
`$HOME/m84_v06_internal_20260809_143927`.

Everything Move 84 exists to establish worked. The complete adopted
Move 83 v13 child gate itself **succeeded**, emitting
`MOVE_83_REPORT_ADOPTION_GATE: PASS` with exit 0. The Move 84 parent then
rejected that genuinely successful run because it required
`MOVE_83_REPORT_OUTPUT: PASS`, which the adopted gate never emits.

**The defect was in my own regression test.** v06 checked that each
required marker's NAME appeared somewhere in the adopted gate. It does —
but only on FAIL paths. The adopted gate assigns `REPORT_OUTPUT=PASS` and
`DIGEST_BINDING=PASS` internally and never echoes either in its terminal
summary. Checking that a name is mentioned is not checking that the gate
can emit `<NAME>: PASS`.

The required set is now **derived mechanically from the adopted gate's own
bytes**: a marker is requirable only if that gate contains
`echo "<NAME>: PASS"` or `echo "<NAME>: $VAR"` where `VAR` is assigned
`PASS`. That derivation yields exactly eleven markers, matching the
genuine v06 transcript:

- `MOVE_83_REPORT_ADOPTION_GATE`, `MOVE_83_CANDIDATE_IDENTITY`,
  `MOVE_83_BASELINE_IMMUTABILITY`, `MOVE_83_TARGET_DETECTION`,
  `MOVE_83_CLEAN_RELEASE_BUILD`, `MOVE_83_BINARY_INSPECTION`,
  `MOVE_83_STANDALONE_EXECUTION`, `MOVE_83_CONTROLLED_BEHAVIOUR`,
  `MOVE_83_DEBUG_RELEASE_EQUIVALENCE`, `MOVE_83_PROVENANCE`;
- the inherited `MOVE_82_REGRESSION_GATE`.

`MOVE_83_REPORT_OUTPUT` and `MOVE_83_DIGEST_BINDING` are removed. Child
exit 0 is still required, and child stdout, stderr and exit status are
still checked separately. The child's retained output is printed verbatim
and no marker inside it is relabelled.

Stale `_m82_*` variable names left by the derivation were also renamed to
`_m83_*`, so the child-invocation variables say what they hold.

Eleven tests added or rewritten: every required marker is emittable by the
adopted gate; the two never-emitted markers are absent from both the
emittable set and the required set; a name appearing only on FAIL paths is
proven not emittable; the terminal and nine stage markers are required;
only the inherited Move 82 regression marker is required; genuine adopted
child output is accepted; a missing genuine marker is rejected; **adding
`MOVE_83_REPORT_OUTPUT: PASS` cannot rescue output missing a genuine
marker**; exit 0 is required; stdout, stderr and status are checked
separately; and both divergences are still required.

Nothing else changed. No inherited Move 83 v13 file, no Rust, no demo
behaviour.

Suite (active): 94 tests.

## v06 structure (retained)

## v06 changes (every active suite-count claim validated)

Candidate v05
(faeb7ad084ee5a33486b6f8bcb76ad746e9a094bef122b18524668355dbd9140) was
REJECTED pre-Termux and is preserved unchanged as audit history.

v05's regression check extracted every `Suite: X -> Y tests.` claim but
validated only the first. That establishes nothing about the rest: a
second, contradictory active claim would have passed silently. The check
selected a claim rather than covering them all.

**Every suite-count claim is now explicitly classified**, so active and
historical claims are distinguished deterministically rather than by
position. An active claim is written `Suite (active): N tests.` and a
retained one `Suite (historical, candidate vNN): ... tests.`, naming the
superseded candidate it describes. Each such line appears exactly once, at
the end of the section it belongs to; no illustrative copies exist
anywhere in this file, so a line-based scanner cannot mistake an example
for a claim.

No historical number changed. Only the classification prefix was added,
which is what makes the distinction machine-checkable instead of
positional.

The strengthened check now:

- requires at least one active claim;
- validates **every** active claim, not the first — each must equal both
  the pinned `EXPECTED_TEST_COUNT.txt` and the count discovered by
  loading the suite;
- requires every historical claim to name the superseded candidate it
  describes, and refuses any historical claim naming the active
  candidate;
- **rejects any unclassified `Suite:` line anywhere in the changelog**, so
  a future claim cannot be added without being classified and therefore
  cannot escape validation.

That last rule is what closes the hole: under v05 an unlabelled second
claim was simply not looked at, whereas now its mere presence fails the
suite.

The check remains folded into the existing changelog-consistency test
rather than added as a new one, so the suite stays at 85 and the check
does not perturb the quantity it validates.

Nothing else changed. The genuine Move 84 v02 transcript SHA-256, the
Stage J helper path `verify/report_v01/check_move83_inherited.py`, the six
historical-evidence tests, the demonstration and `rust/` are all
untouched.

Suite (historical, candidate v06): 85 tests, unchanged.

## v05 structure (retained)

## v05 changes (corrected focused-suite count)

Candidate v04
(4874a898fbf376ce77d071380e5384c1dc0005e8fe83deef771daa4d71554de5) was
REJECTED pre-Termux and is preserved unchanged as audit history.

**The v04 changelog claimed the focused suite had gone 79 -> 83 tests.**
The pinned `EXPECTED_TEST_COUNT.txt` correctly held 85 and the suite
genuinely contained 85, so the changelog understated the count by two. I
wrote the sentence before finishing the sixth historical-evidence test and
did not revise it. The active claim now reads 79 -> 85.

Every focused-suite count claim in the candidate was audited. The two
older claims are genuine history and are unchanged: v02 went 55 -> 70 and
v03 went 70 -> 79. `EXPECTED_TEST_COUNT.txt` remains 85, which is the
discovered suite size.

**A regression check now makes this class of error impossible to ship.**
Rather than adding a new test — which would itself change the count to 86
and contradict the instruction to preserve 85 — the check is folded into
the existing changelog-consistency test. It parses the topmost, and
therefore active, `Suite: X -> Y tests.` claim in the changelog and
requires Y to equal both the pinned `EXPECTED_TEST_COUNT.txt` value and
the count discovered by loading the suite. A changelog that disagrees with
either now fails off device.

Nothing else changed. The genuine Move 84 v02 transcript SHA-256, the
Stage J helper path `verify/report_v01/check_move83_inherited.py`, the six
historical-evidence tests, the demonstration and `rust/` are all
untouched.

Suite (historical, candidate v05): 85 tests, unchanged.

## v04 structure (retained)

## v04 changes (corrected audit history)

Candidate v03
(41f5ccdb2c5bce5bc759a3764bf4f2f108208105a0f29929c289315786518071) was
REJECTED pre-Termux and is preserved unchanged as audit history.

**I recorded a false SHA-256 for candidate v02's genuine Termux
transcript.** The v03 changelog attributed a hash to
`MOVE_84_V02_TERMUX_GATE.txt` that was not the transcript's hash and was
not supplied by anyone; I wrote it into the audit record. The false value
is deliberately not reproduced here, so that no reader can mistake it for
evidence and no scanner can match it. The genuine hash, reported with the
v02 rejection, is:

```
0d8678555d7775addb8496618d23e4e943616982fb2cf510b030fd4c27814493
```

Both occurrences are corrected. This was a fabricated piece of evidence in
a project whose entire purpose is tamper-evident evidence, and it is the
most serious error I have made in this block. A false hash in an audit
record is indistinguishable from a forged one.

Every historical identity in the Move 84 files was then audited against
what was actually reported:

| Fact | Value | Status |
|---|---|---|
| Adopted Move 83 v13 baseline | `aa06feb8…975a6c` | verified against the archive |
| Move 84 v01 candidate | `27d18656…1986c` | rejected pre-Termux, never run |
| Move 84 v02 candidate | `dfd5ba01…1f36` | failed a genuine Termux gate |
| Move 84 v02 transcript | `0d867855…4493` | **corrected** |
| Move 84 v03 candidate | `41f5ccdb…8071` | rejected pre-Termux, never run |

v01 and v03 have no Termux transcript, because neither was run there, and
none is claimed for them.

A regression test now pins the genuine v02 transcript hash exactly,
asserts the fabricated value appears nowhere in the candidate, and
requires that any file naming a historical transcript names it with its
real hash. Two further tests assert that no candidate that was never run
on Termux is credited with a transcript, and that the active provenance
identity is `MOVE_84_V04_TERMUX_GATE.txt`.

Nothing else changed. The Stage J helper path remains
`verify/report_v01/check_move83_inherited.py`, the demo is untouched, no
inherited Move 83 v13 file changed, and `rust/` is byte-identical.

The active provenance transcript identity is
`MOVE_84_V07_TERMUX_GATE.txt`.

Suite (historical, candidate v04): 79 -> 85 tests.

## v03 structure (retained)

## v03 changes (child-tree helper path; transcript identity)

Candidate v02
(dfd5ba010291e4659d2481be9115069781ce5a7b62c4eb98e84ea07a91d61f36)
FAILED its genuine first-run Termux adoption gate and is preserved
unchanged as rejected audit history, together with its transcript
`MOVE_84_V02_TERMUX_GATE.txt`
(0d8678555d7775addb8496618d23e4e943616982fb2cf510b030fd4c27814493).

**The demonstration itself worked.** On device, all three cases behaved
exactly as designed and the Rust reason code was established by execution
rather than prediction:

| Case | Python | Rust |
|---|---|---|
| clean | `PASS`, exit 0 | `INCONCLUSIVE`, exit 3, `RECEIPT_CHAIN_HASHES_RECOMPUTED` |
| toplevel_tamper | exit 1 | `FAIL`, exit 1, **`FILE_HASH_MISMATCH`** |
| nested_evidence_tamper | exit 1, nested checksum mismatch | `INCONCLUSIVE`, exit 3 — undetected, as documented |

Both transcripts were byte-identical, the debug profile reproduced the
demonstration, and the focused suite passed 70/70. The run failed at Stage
J for a path defect.

1. **The child-tree helper path is corrected.** Stage J invoked
   `verify/portable_build_v01/check_move83_inherited.py` inside the
   extracted Move 83 child tree. That file does not exist: the Move 83
   checker lives in `verify/report_v01/`, and `portable_build_v01` holds
   the **Move 82** checker. The derivation had renamed the file and left
   the directory. The gate now uses
   `verify/report_v01/check_move83_inherited.py`, which is the exact path
   the adopted Move 83 gate itself uses for its own output-directory
   check, and verifies the helper is present and not a symlink **before**
   invoking it — so a wrong path fails with a clear message instead of an
   opaque `exit 2` from `python3`.

2. **The transcript identity is current.** v02's provenance recorded
   `MOVE_84_V01_TERMUX_GATE.txt`: the single-sourced value was carried
   forward unchanged when the candidate was rebuilt. It is now
   `MOVE_84_V03_TERMUX_GATE.txt` for that candidate, still defined once and referenced by
   variable, and the inherited explanatory comment — which described Move
   83's own drift — is rewritten to describe this one.

Nine tests added. Every `$_M83_ROOT/...` path the gate reaches for is
resolved against the **real adopted Move 83 v13 archive**, so a
nonexistent child-tree path fails off device. Further tests assert the
Move 83 checker is sought in `report_v01` and never in
`portable_build_v01`, confirm from the archive that
`portable_build_v01` holds only the Move 82 checker, require the presence
check before use, and verify from the adopted Move 83 gate's own source
that `$P` there is `verify/report_v01`. Four more pin the transcript
identity: defined once, referenced by variable, no superseded identity in
active code, and matching the changelog.

No inherited Move 83 v13 file changed. No Rust change. Nothing else in the
demonstration was altered.

Suite (historical, candidate v03): 70 -> 79 tests.

## v02 structure (retained)

## v02 changes (gate identity language corrected)

Candidate v01
(27d18656a61e5c135b7ba1bbf0a093c986377a64ee6947861dd7cc52b9d1986c) was
REJECTED pre-Termux and is preserved unchanged as audit history.

The archive was clean and the implementation was accepted, but the Move 84
adoption gate — derived from the adopted Move 83 gate — carried Move 82
identity language throughout. The `_M83_EXPECT` hash bound to the correct
adopted Move 83 v13 bytes, but the comments, stage names, failure messages
and success messages repeatedly called that artifact "Move 82 v07".

v02 restarts from the exact adopted Move 83 v13 baseline, reapplies the
same authorised additive implementation, and corrects the identity
language throughout rather than only at the reported examples. The whole
gate was audited, not spot-fixed.

Corrected:

- the header, from `MOVE 82 PORTABLE BUILD ADOPTION GATE` to
  `MOVE 84 TAMPER-AND-DETECT DEMO ADOPTION GATE`;
- the `REAL_MOVE83` documentation, which now names the adopted Move 83
  v13 zip as the sole Move 84 development baseline and the complete
  adoption/regression child gate rerun here;
- Stage B, now "baseline immutability (candidate vs real adopted Move 83
  v13 zip)", with matching failure text;
- the byte-authority comments and success message, now naming the adopted
  Move 83 v13 verifier;
- Stage J, now "complete adopted Move 83 v13 adoption/regression child
  gate", together with every child run-directory, staging, output-dir and
  marker message;
- the stale `MOVE 83 REPORT STAGES` headers left by the derivation;
- the terminal child evidence marker, now `MOVE_83_REGRESSION_GATE`.

**The child's marker vocabulary was read from the child, not guessed.**
The adopted Move 83 gate emits its own `MOVE_83_*` stage markers and,
because it in turn reruns its inherited Move 82 gate, its retained
transcript also carries genuine `MOVE_82_*` markers. v01 demanded
`MOVE_82_CANDIDATE_IDENTITY` and eight other Move 82 stage markers of the
Move 83 child — the wrong family. v02 requires the child's own twelve
`MOVE_83_*` markers plus the single inherited `MOVE_82_REGRESSION_GATE:
PASS`, and both adopted divergences. The child's retained output is
printed verbatim and no marker inside it is relabelled.

The evidence chain is now unambiguous:

```
Move 84 candidate
  -> adopted Move 83 v13 baseline
  -> complete adopted Move 83 v13 adoption/regression child gate
     -> which itself exercises its inherited Move 82 regression gate
```

Eleven tests added to catch this class mechanically rather than by
inspection: a scanner for phrases assigning a baseline or child-gate role
to an older move, itself proven to flag the exact v01 wording and to leave
genuine Move 80 fixture, Move 81 adapter and dependency references alone;
checks that the baseline is named Move 83 v13 wherever it is named, that
the header names this move, that Stage B and Stage J name the Move 83
baseline and child; and marker checks requiring the child's own family,
permitting only the inherited regression marker, and verifying that
**every marker demanded of the child is one the adopted Move 83 gate can
actually emit** — read from that gate's own source.

Mutation-tested: reinstating the v01 Stage B wording and header fails four
of these tests.

No inherited Move 83 v13 file changed. No Rust change. Move 84 was not
broadened.

Suite (historical, candidate v02): 55 -> 70 tests.

## v01 structure (retained)

## Roadmap objective

> **84 — Tamper-and-detect demo** — Show a clean bundle passing, then
> modify one evidence file and show the verifier failing with the exact
> reason.

## Adopted baseline

- `project-witness-MOVE_83_candidate_v13.zip`
- SHA-256:
  `aa06feb870ec3d72ff7c942fe8c0752efff313cbbdab6e280302dba288975a6c`
- Moves 71–83 adopted. Move 84 is **additive only**: no inherited file
  changes, and `rust/` is byte-identical in its entirety.

## Binding rulings implemented

**A1 — clean bundle.** Both lanes are shown honestly. Python: `PASS`,
exit 0. Rust: `INCONCLUSIVE`, exit 3, `RECEIPT_CHAIN_HASHES_RECOMPUTED`.
The Rust result is never described as a pass; the transcript states that
`INCONCLUSIVE`/3 is the adopted verifier's honest clean-bundle ceiling,
and a test asserts the word PASS never appears on a Rust verdict line.

**A2 — tamper and detection.** Two tampers are demonstrated.
`toplevel_tamper` flips one byte in the top-level declared file
`companion_steps.json`, which the adopted Rust hash stage covers, so the
Rust verifier genuinely detects it. **Its exact reason code, stage, stdout
and exit are established by executing the adopted verifier** — nothing in
this candidate declares them, and a test scans the driver and the fixture
builder to keep it that way. `nested_evidence_tamper` flips one byte in
`coordinator_output/aletheia_bundle/evidence/evidence_001.bin`; the Python
lane detects it and the adopted Rust verifier does not, its output being
byte-identical to the clean bundle. That limitation is stated plainly and
a test rejects any run in which it is not observed.

**A3 — medium.** An executable deterministic driver is the authority, with
a README explaining how to run it and what each case means. No canned
transcript exists. The transcript carries no timestamps, hostnames,
absolute paths or durations, and the gate requires two runs to be
byte-identical.

**A4 — fixtures.** One new fixture family, derived deterministically from
the frozen reference bundle using the frozen Move 71 byte-flip (offset 5,
XOR 0xFF). Each case is independently re-hashed after mutation and must
show an unchanged file set with exactly the declared file differing. No
expected Rust verdict is authored anywhere in the fixture layer.

**A5 — Rust scope.** No Rust modification. `modified_paths` is empty and
the inherited checker fails if it is not.

**A6 — Move 85 boundary.** This is a demonstration, not a distributable
audit pack. Nothing is packaged for distribution.

## Files added (9)

- `verify/demo_v01/build_demo_fixtures.py`
- `verify/demo_v01/demo.py`
- `verify/demo_v01/demo_tests.py`
- `verify/demo_v01/check_move84_inherited.py`
- `verify/demo_v01/allowlist_move84.json`
- `verify/demo_v01/EXPECTED_TEST_COUNT.txt`
- `verify/demo_v01/README.md`
- `tools/check_move84_demo_adoption.sh`
- `CHANGELOG_MOVE_84.md`

No inherited file is modified.

## What exit 0 from the demonstration means

Only that every expected observation was genuinely reproduced. It does
**not** mean the tested bundle is universally valid, that the Rust
verifier detects every tamper, or that it produced a pass — it cannot.

## What is NOT established off device

This environment has no Rust toolchain, so the adopted binary is neither
built nor executed here. The Python lane IS genuinely executed. The Rust
lane is exercised end-to-end through the real driver with a stand-in
verifier, which proves the driver's logic and establishes nothing about
the adopted binary. Only the on-device adoption gate establishes that.

## Not adopted

- **v01** — `27d18656a61e5c135b7ba1bbf0a093c986377a64ee6947861dd7cc52b9d1986c`
  — REJECTED pre-Termux: the gate misidentified the adopted Move 83 v13
  baseline as Move 82 v07. Preserved unchanged as audit history.
- **v02** — `dfd5ba010291e4659d2481be9115069781ce5a7b62c4eb98e84ea07a91d61f36`
  — FAILED its genuine first-run Termux gate at Stage J on a child-tree
  helper path. The demonstration itself succeeded. Transcript
  `MOVE_84_V02_TERMUX_GATE.txt`, SHA-256
  `0d8678555d7775addb8496618d23e4e943616982fb2cf510b030fd4c27814493`.
  Preserved unchanged as audit history.
- **v03** — `41f5ccdb2c5bce5bc759a3764bf4f2f108208105a0f29929c289315786518071`
  — REJECTED pre-Termux: its changelog recorded a false SHA-256 for the
  v02 Termux transcript. Never run on Termux. Preserved unchanged as audit
  history.
- **v04** — `4874a898fbf376ce77d071380e5384c1dc0005e8fe83deef771daa4d71554de5`
  — REJECTED pre-Termux: its changelog understated the focused-suite
  count. Never run on Termux. Preserved unchanged as audit history.
- **v05** — `faeb7ad084ee5a33486b6f8bcb76ad746e9a094bef122b18524668355dbd9140`
  — REJECTED pre-Termux: its suite-count regression check validated only
  the first claim. Never run on Termux. Preserved unchanged as audit
  history.
- **v06** — `a3c23067920addecc643bb767c6b455d77d24e13d8815a4911bc7ee4d023e782`
  — FAILED its genuine first-run Termux gate: it required a child marker
  the adopted Move 83 v13 gate never emits. Transcript
  `MOVE_84_V06_TERMUX_GATE.txt`, SHA-256
  `ab56b88259a375ec708d2efad8da89125b34c9e14c5b53ba6938d8b42415fa4a`.
  Preserved unchanged as audit history.
- **v07** — this candidate, packaged for independent hostile
  packaged-byte review. It has **not** been run on a real Termux device
  and is **not** adopted.
