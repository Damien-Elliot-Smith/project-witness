# CHANGELOG — Move 81: Full PASS/FAIL/INCONCLUSIVE verifier output

Status: CANDIDATE v08. Not adopted. Not run on Termux.

Move 81 adds a deterministic, machine-readable structured-verdict output
boundary around the adopted Project Witness verification lanes. It is
additive and honesty-preserving: it modifies no adopted verifier, no
default command output, and no verdict behaviour, and it adds no
verification capability. `rust/` and the frozen Python source are
unchanged.

## v08 changes (Stage F gate-composition defect)

Candidate v07
(1d46b6d8f74cecebb2b63f696ddc92cee62c0b099ad1fa68ef2fa5f89caaf36b) reached
its FIRST GENUINE TERMUX ADOPTION RUN and was REJECTED there. Its
first-run transcript is `MOVE_81_V07_TERMUX_GATE.txt`, SHA-256
`8849762e9e255dd57c48b3f8bbcf6d5eb2b7ac047063a766421d0075e3772cdc`. v07 is
preserved unchanged as audit history. Every v07 production and portability
repair is retained; v08 is built directly from the exact v07 tree.

On that run the genuine Termux environment was correct and v07 passed
trusted bootstrap, the nested-execution probe, REAL_MOVE80 hash
verification, baseline ZIP safety, 866/866 inherited files byte-identical,
exactly ten declared Move 81 additions, a fresh Rust build at version
0.0.8-step79-diagnostics, fresh cargo tests, the focused suite 165/165
with no skips and empty stderr, deterministic Python PASS/0, healthy Rust
INCONCLUSIVE/3 with no synthetic PASS, clean-control AGREEMENT, and legacy
default-output preservation.

It failed only at Stage F, on a deterministic gate-composition defect of
my own making.

**The defect.** The Move 81 gate invoked the unchanged Move 80 adoption
gate FROM THE MOVE 81 CANDIDATE ROOT. The Move 80 gate compares its
current tree against the real Move 79 v27 ZIP and permits only the Move 80
addition set. Run from the Move 81 candidate root it therefore necessarily
saw the ten legitimate Move 81 additions as undeclared relative to Move
79, and failed its inherited-tree comparison. This was not a Termux
failure, artifact corruption, user-command error, Rust failure or
focused-test failure — the composition itself was wrong.

**The repair.** The complete, UNCHANGED Move 80 child adoption gate is now
run from a private, safely extracted copy of the exact adopted REAL_MOVE80
ZIP, never from the Move 81 candidate root. Stage F now:

1. requires `REAL_MOVE80` as an explicit absolute regular-file path;
2. verifies it with the trusted `sha256sum` against
   `8c08342efae3b17458e33c6ae54ff42bf79d6759170b46cfbf32ef218d0dd2ad`;
3. independently validates the ZIP BEFORE extraction — no duplicate
   members, no traversal, no absolute paths, no backslash ambiguity, no
   symlinks or special files, no encrypted entries, exactly one canonical
   `project-witness-main/` root, and CRC integrity of every member;
4. extracts only into a gate-owned private temporary directory created
   after trusted bootstrap, with every member re-checked against the
   destination boundary as it is written;
5. locates the extracted Move 80 root deterministically and confirms it is
   a complete Move 80 tree;
6. invokes the unchanged Move 80 adoption gate from THAT root;
7. supplies the same adopted dependencies the Move 80 gate requires
   (`REAL_MOVE78`, `REAL_705`, `REAL_MOVE79`, and `REAL_V20` when set);
8. retains the child's complete stdout and stderr between explicit
   retained-output markers, alongside separate retained extraction
   evidence;
9. requires child exit 0 and the exact adopted Move 80 markers, including
   the expected inner `SYSTEM_AGREEMENT_RESULT: FAIL`;
10. cleans the temporary extraction directory through the existing trusted
    trap/cleanup mechanism (`gate_track_tmp`, removed under the EXIT and
    HUP/INT/TERM traps) on every exit path, plus a prompt explicit removal
    on the success path.

No Move 81 file is copied or overlaid into the extracted Move 80 tree, and
the Move 80 gate is not weakened, patched, bypassed or replaced. The
extraction and hashing run through `$TRUSTED_PYTHON3`, `$TRUSTED_MKTEMP`
and `$TRUSTED_SHA256SUM`, and the child through `$TRUSTED_SH`; the
bootstrap additionally replaces `PATH` with the trusted Termux path before
any stage runs, so a hostile PATH cannot substitute the extraction,
hashing, shell or cleanup tools.

The defect and its repair were demonstrated directly off-device: comparing
the Move 81 candidate root against the Move 80 baseline while permitting
only the Move 80 addition set reproduces exactly the observed failure —
the same ten legitimate Move 81 files reported as undeclared additions —
while the same comparison run against the extracted Move 80 root reports
866 byte-identical inherited files and zero additions.

One incidental correctness fix was required by the new tests: the
special-file check added in v07 examined the whole mode word, so a member
carrying permission bits but no file-type bits (the normal shape for
archive members written from strings) was misreported as a special file.
It now inspects the `S_IFMT` type field and treats absent type bits as an
ordinary member, exactly as `zipfile` itself does. The adopted baseline
was unaffected either way, because its members carry full type bits.

Regression coverage added: valid baseline extracts and reports its root;
hash mismatch fails with nothing written and no safety inspection reached;
an unsafe ZIP (traversal) and a second-root ZIP are each rejected before
extraction with nothing written and nothing escaping; the declared Move 81
additions are provably absent from the extracted tree and the extraction
destination is disjoint from the candidate root; paths containing spaces
are supported for both the archive and the destination; extraction runs
under an empty PATH; the trap-and-remove cleanup contract removes a
populated tracked directory; and gate-structure assertions that the child
is launched from inside the extracted tree, exactly once, after
extraction, with its directory tracked for trap cleanup, with child
nonzero exit failing Stage F, with child stdout/stderr retained, with the
adopted dependencies forwarded, with only trusted tools used, and with
nothing copied or overlaid into the extracted tree.

Suite: 165 -> 182 tests. The exact one-process suite was run with the
supplied absolute `MOVE81_TEST_SH` and again with `PATH` empty: both
report `Ran 182 tests` / final `OK` / exit 0 / stderr 0 bytes / 0 skips.

## v07 changes (three fail-closed robustness blockers)

Candidate v06
(242729fbfbc63a93e881ffc105f066b9c047518aafe0e55d616a3b03e3d3f54f) was
REJECTED at hostile review before any Termux run and is preserved
unchanged as audit history. Every v06 portability repair and all existing
structured-verdict behaviour is retained. v07 is built directly from the
exact v06 tree and fixes three cases where an unexpected input produced a
traceback instead of a clean fail-closed record. No new schema version and
no new measurement-error code is introduced.

1. **Generic executable launch failure is now a clean record.**
   `adapter._run()` caught only `FileNotFoundError` and `PermissionError`.
   An absolute, regular, chmod-executable file with an INVALID EXECUTABLE
   FORMAT passes every path validation the adapter performs, and then
   `subprocess.run` raises `OSError: [Errno 8] Exec format error` — which
   escaped as a traceback on stderr with no record emitted, leaking the
   raw path. `_run()` now converts EVERY launch-time `OSError` into the
   existing `ADAPTER_INVOCATION_ERROR` semantics (both previously caught
   exceptions are `OSError` subclasses, so they are subsumed). The result
   is exactly one canonical `record_type="measurement_error"` object with
   `measurement_error_code="ADAPTER_INVOCATION_ERROR"`, adapter exit 1,
   NO `exit_code` field (the process never completed normally, so no exit
   status is honestly established), completely empty stderr, no traceback
   and no path leakage.
2. **Malformed reason-map entries now fail deterministically.**
   `load_reason_map` verified only that each lane existed and was a list,
   so a syntactically valid map such as
   `{"python_bundle":[1],"rust_bundle":[],"archive":[]}` reached
   `entry.get(...)` and raised an uncaught `AttributeError`; missing or
   wrongly typed fields could similarly raise `KeyError`, `TypeError` or
   `re.error`. A malformed regex was worse than a crash: because exact
   matches take precedence, a bad pattern could sit unnoticed until some
   later input happened to reach it. Every entry is now validated
   COMPLETELY at load time — object shape, present and known `match_type`,
   present non-empty string `value`, compilable `regex` values, present
   non-empty string `class`, and present non-empty string `stage` — before
   any verifier is invoked. The semantics are the EXISTING ones an absent
   lane already had: an unusable `--reason-map` is adapter CLI misuse, so
   the adapter exits 2, emits NO record, writes deterministic usage text
   to stderr, and never launches a verifier. `ADAPTER_UNKNOWN_REASON` and
   `ADAPTER_MISSING_STAGE_MAPPING` remain as defensive guards inside the
   resolver and are covered by direct tests.
3. **Both determinism runs now prove they were warning-clean.** Stage D
   performed its SECOND Python adapter run with `2>/dev/null`, which could
   not prove both runs were warning-clean. The second run now writes to a
   separate tracked temporary and is held to exactly the same strict
   emptiness policy as the first.

Regression coverage added: invalid-format `--rust-bin` under
`rust_bundle`; invalid-format `--rust-bin` under `archive`;
invalid-format `--python-bin` under `python_bundle`; a `compare` with one
invalid-format attempted lane proving
`comparison_status="MEASUREMENT_ERROR"`, the failed lane carrying its
complete measurement_error record, the unaffected completed lane still
present, neither attempted lane replaced with null, and empty stderr;
eleven malformed reason-map structures (non-object entry, missing/unknown
`match_type`, missing/non-string `value`, malformed regex, missing/
non-string `class`, missing/non-string `stage`, non-object map), each
additionally proving via a canary that NO verifier was launched; and gate
tests proving no adapter invocation discards stderr and that both
determinism runs capture and check it.

Suite: 144 -> 165 tests. The exact one-process suite was run with the
supplied absolute `MOVE81_TEST_SH` and again with `PATH` empty: both
report `Ran 165 tests` / final `OK` / exit 0 / stderr 0 bytes / 0 skips.

## v06 changes (target-portable test executables)

Candidate v05
(93634ed78b89c02604f5465ea4eb207b282ed1d77c8442082c00b8d586e96459) was
REJECTED at hostile review before any Termux run and is preserved
unchanged as audit history. v05's production repairs were correct and are
retained in full; v06 is a TEST-HARNESS PORTABILITY repair only. The
structured-verdict schema, the adapter's behaviour and every adopted
verifier behaviour are unchanged.

The focused suite assumed desktop filesystem paths that are not part of
the adopted Termux environment: `/bin/sh` and `/usr/bin/env`. On the
target those paths may not exist, so a fixture could be selected and then
fail before doing its job -- which, in the hostile-PATH test, would have
produced FALSE evidence of safety (an absent marker read as "no tool ran"
when the tool actually ran and died).

1. **Every hard-coded `/bin/sh` gate invocation removed.** All five
   `subprocess.run(["/bin/sh", GATE], ...)` calls now use a resolved
   `TEST_SH`. The suite resolves it ONCE at module import -- strictly
   before any test can install a hostile PATH -- and validates it as an
   absolute, canonical, regular, executable file. Under the adoption gate
   the exact trusted shell is required and supplied via
   `MOVE81_TEST_SH="$TRUSTED_SH"`; for off-device hostile review only, a
   single explicit fallback resolves `sh` once via `shutil.which` at
   import time and then canonicalizes and validates it. The shell is never
   resolved after a hostile PATH has been installed.
2. **Every `#!/usr/bin/env python3` fixture removed.** `PYTHON_BIN` is now
   `os.path.realpath(sys.executable)`, validated as an absolute regular
   executable, and every executable Python fixture is created through one
   shared helper that writes `#!<PYTHON_BIN>`. A directly executed fixture
   therefore never searches PATH and never needs `/usr/bin/env`.
3. **Hostile-PATH marker tools made reliably executable on the target.**
   They previously used a `#!/bin/sh` shebang; they now use the exact
   validated interpreter shebang and each writes its OWN tool name to the
   marker file before exiting. The hostile-PATH test now names exactly
   which fake executable ran if the boundary ever fails, instead of
   reporting a bare failure. The fake `sh` was added to the hostile set.
4. **Target-path assertions added**, proving: no `subprocess.run` gate
   invocation contains a literal `/bin/sh`; no executable fixture carries
   an env-based shebang; no hostile marker executable carries a
   `/bin/sh` shebang; `TEST_SH` and `PYTHON_BIN` are each absolute,
   canonical, regular and executable; the path validator rejects empty,
   relative, missing, non-executable and directory paths; installing a
   hostile PATH does not change the already-resolved `TEST_SH`; every fake
   Rust fixture executes directly by absolute path with an EMPTY `PATH`;
   the shell-fixture helper carries the shell shebang and runs; and the
   gate hands the trusted shell down rather than a desktop path.
   Crucially, a POSITIVE CONTROL now invokes every hostile marker tool
   through its absolute path and requires each to record its own name --
   so the absence of a marker is only used as security evidence after the
   marker mechanism itself is proven to work.
   (These scanners build their forbidden tokens from fragments, so the
   scan honestly covers the whole file including the scanner itself
   rather than flagging its own assertions.)
5. **The adoption gate trust boundary is unchanged.** The gate remains
   responsible for supplying the exact trusted shell, trusted Python,
   freshly built Rust binary, inherited Python entry, reason map and
   comparison contract. No production code searches PATH.
6. **All v05 correct work retained** -- complete adopted bootstrap
   protocol with return classification, cleanup traps and the
   nested-execution probe; exit-2 precedence; agreement-case class/stage
   equality; the genuine known-divergence requirement; rejected-only known
   divergences; corrected hash-evidence wording; strict output framing;
   all-lane stderr rejection; Python error-form normalization; Rust
   verifier identity validation; frozen reason-map authority; no Rust PASS
   path; the additive adapter-only architecture; one complete Move 80
   child gate; exact one-object canonical output; and inherited baseline
   immutability.

Portability evidence: the exact one-process suite
(`python3 -B -W error::ResourceWarning structured_tests.py`) reports
`Ran 144 tests` / final `OK` / exit 0 / stderr 0 bytes / 0 skips. It was
additionally run with `MOVE81_TEST_SH` supplied as the gate supplies it,
and with an EMPTY `PATH` plus a supplied `MOVE81_TEST_SH` -- green in
both, proving no PATH lookup is required anywhere. With neither
`MOVE81_TEST_SH` nor any `sh` on PATH the suite fails immediately with a
clear, deterministic error naming `MOVE81_TEST_SH`.

## v05 changes (six hostile-review repairs)

Candidate v04
(021fd6c43cf8aeb21e35557ec487536f8f5e6fdca23f481fadae660b805f6f68) was
REJECTED at hostile review before any Termux run and is preserved
unchanged as audit history. v05 fixes six further gaps:

1. **The adopted bootstrap protocol is now complete.** The gate previously
   called `gate_bootstrap` without capturing or classifying its result, and
   never installed the cleanup traps or ran the nested-execution probe. It
   now runs `gate_bootstrap`, captures `BOOT_RC`, classifies exit 3 as
   `MOVE_81_STRUCTURED_VERDICT_ADOPTION_GATE:
   INCONCLUSIVE_RUST_UNAVAILABLE`, classifies any other nonzero honestly as
   a controlled gate FAIL (distinguishing missing preload, invalid preload,
   and untrusted environment), and exits immediately on any unsuccessful
   bootstrap. `gate_install_traps` is called immediately after a successful
   bootstrap and BEFORE any temporary file is created or tracked, restoring
   EXIT cleanup, HUP/INT/TERM cleanup and termination, temporary
   `CARGO_HOME` cleanup, and tracked `mktemp` cleanup. `gate_lib.sh` is
   then sourced, and `gate_nested_exec_probe` runs before Stage A,
   requiring `TERMUX_NESTED_EXEC_CHECK: PASS` and stopping the gate with a
   Move 81 FAIL marker otherwise — proving trusted nested execution works
   before the subprocess-heavy focused suite.
2. **The hostile-PATH test is now platform-honest.** It previously
   hardcoded exit 3 and `INCONCLUSIVE_RUST_UNAVAILABLE`, which is only
   correct off Termux; on a real Termux host the literal trusted readlink
   exists, the gate proceeds, and it refuses the deliberately nonexistent
   baseline with exit 1. The test now accepts a refusal exit of 1 or 3,
   requires exit 3 to carry the INCONCLUSIVE marker and exit 1 to carry a
   controlled failure marker, requires the Move 81 PASS marker never to
   appear, and — the decisive, platform-independent property — requires
   that no fake `dirname`, `readlink`, `python3`, `sha256sum`, `pwd`,
   `cargo` or `rustc` on `PATH` ever executed. The focused suite no longer
   depends on being off Termux.
3. **Underlying exit 2 now takes precedence over output framing.** For the
   Python, Rust bundle and archive lanes the adapter checks for a normal
   completion with exit 2 FIRST and immediately emits
   `ADAPTER_INVOCATION_ERROR` with `exit_code=2` preserved, exiting 1. It
   no longer parses or reinterprets usage stdout/stderr as a verifier
   result, so normal usage text on stderr can no longer surface as
   `ADAPTER_UNEXPECTED_STDERR`, and an empty stdout can no longer surface
   as `ADAPTER_INCOMPLETE_RESULT`. Exit 2 accompanied by valid-looking
   stdout also remains an invocation failure and never becomes a verdict.
4. **Adopted comparison category semantics are enforced.** An
   `AGREEMENT_CASE` must now have matching normalized outcomes AND an
   identical expected reason class AND an identical expected stage across
   both lanes; differing class or stage invalidates the contract. A
   `KNOWN_DIVERGENCE_CASE` must still carry exact `expected_divergence`,
   must have at least one of reason class or stage differing between the
   lanes (identical class and stage is agreement, not divergence, however
   self-consistent the metadata), and must remain a REJECTED outcome —
   an "accepted divergence" is not something Move 81 may invent. Every
   violation produces `record_type=measurement_error`,
   `measurement_error_code=ADAPTER_COMPARISON_CONTRACT_INVALID`,
   `operation=compare`, `input_type=bundle_dir` and adapter exit 1 before
   either lane executes. Both rules were verified against all four adopted
   agreement cases and both adopted divergence cases before implementation,
   so the genuine frozen contract remains accepted.
5. **Hash-evidence wording corrected.** The shell gate keeps
   `REAL_MOVE80 verified by trusted sha256sum:` because that check
   genuinely uses `$TRUSTED_SHA256SUM`. The Python checker's independent
   `hashlib` verification now prints
   `REAL_MOVE80 independently matched --expect-sha256 in the baseline
   checker:` instead of claiming the trusted tool. Neither hash check was
   weakened or removed; both still run, independently.
6. **v04's correct work is retained** — complete field/type/verdict-exit
   validation, safe case IDs and per-case lane validation,
   normalized-outcome validation, `expected_divergence` consistency,
   signal termination with no negative `exit_code`, comparison-authority
   errors carrying `input_type=bundle_dir`, executable negative
   baseline-hash tests, strict stdout framing, all-lane stderr rejection,
   Python error-form normalization, Rust verifier identity checking,
   `reason_map` as the only reason/stage authority, no Rust PASS path, the
   additive adapter-only architecture, one complete Move 80 child gate
   only, bounded subprocess tests, the exact one-process focused-suite
   discipline, and inherited Move 80 immutability.

## v04 changes (seven hostile-review repairs)

Candidate v03
(cc8acafa579940ef05381cd58e3854d14b723b39aae653dbaf9b75e4331a8992) was
REJECTED at hostile review before any Termux run and is preserved
unchanged as audit history. v04 fixes seven further gaps:

1. **Comparison-contract validation is now complete, structurally AND
   semantically.** Beyond v03's structural checks it now requires: a
   nonempty, non-whitespace, safe-token `case_id`; a per-case `lane`
   matching the corpus; an adopted `(verdict, exit_code)` pairing for every
   in-scope expected record; rejection of usage exit 2 as a verdict
   expectation; only lane-reachable verdicts (a Python `INCONCLUSIVE` or a
   Rust `PASS` expectation is rejected); a present and valid
   `normalized_outcome` consistent with every in-scope lane's verdict under
   the adopted agreement semantics; for `KNOWN_DIVERGENCE_CASE` a present
   `expected_divergence` whose `python_class`/`python_stage`/`rust_class`/
   `rust_stage` exactly match the expected lane records, with inconsistent
   or missing divergence metadata invalidating the whole contract; a
   rejection of divergence metadata on non-divergence cases; and a
   well-formed out-of-scope observed record when present. The adopted
   agreement semantics were derived from and verified against all fifteen
   frozen cases before implementation, so the validator accepts the genuine
   authority and rejects mutations of it.
2. **Signal termination no longer reports a negative exit code.** A
   negative subprocess return value is signal metadata, not a process exit
   code: the adapter emits `ADAPTER_SIGNAL_TERMINATION`, exits 1, and omits
   `exit_code` entirely. `exit_code` is retained only when the underlying
   process completed normally.
3. **Comparison-authority errors preserve the known input type.**
   `ADAPTER_COMPARISON_CONTRACT_INVALID` and `ADAPTER_UNKNOWN_CASE_ID`
   records now carry `operation` = `compare` AND `input_type` =
   `bundle_dir`, because the input directory is validated before authority
   lookup. No fabricated lane verdicts are included.
4. **Gate-authority proof is now executable, not only static.** The hash
   authority is factored into the baseline checker via `--expect-sha256`,
   which verifies the baseline FIRST and refuses to open, safety-inspect or
   compare it on mismatch; the gate passes the adopted hash down so the
   authority is enforced independently twice. Executable tests prove an
   exact hash is accepted, and that a different ZIP, a byte-modified ZIP,
   and an arbitrary ZIP merely renamed as the baseline are each rejected
   with the comparison never reached. A genuine hostile-PATH test places
   fake `dirname`/`readlink`/`python3`/`sha256sum`/`pwd`/`cargo`/`rustc`
   binaries first on `PATH`, each recording a marker when executed, runs
   the REAL gate, and asserts that no marker was ever written — executing
   the pre-bootstrap logic rather than only reading it. Two further
   executed tests prove the gate refuses a renamed copy of itself and
   exits 2 on missing inputs. The Termux-only gate was NOT weakened to
   make testing easier.
5. **README comparison semantics corrected.** The contradictory claim that
   malformed contracts and unknown case IDs produce
   `comparison_status=MEASUREMENT_ERROR` is removed and replaced with the
   two exact shapes: (A) pre-lane authority failure = top-level
   `measurement_error`, no `comparison_status`, `operation=compare`,
   `input_type=bundle_dir`; (B) a valid case whose attempted lane cannot be
   measured = `record_type=comparison`,
   `comparison_status=MEASUREMENT_ERROR`, the affected lane carrying its
   complete measurement_error record, the unaffected lane still present,
   and null allowed only for a genuine `LANE_NOT_APPLICABLE`.
6. **The exact one-process focused-suite run is bounded and verified.**
   Every test subprocess now carries an explicit timeout, so no hung child
   can stall the suite; the slow timeout fixture was shortened. The
   complete stdout-bound suite was run exactly as the gate runs it
   (`python3 -B -W error::ResourceWarning structured_tests.py`) in one
   process: exact pinned count, final `OK`, no skips, empty stderr,
   deterministic completion, with the runtime recorded below. There is no
   cumulative test interference and no unbounded subprocess.
   `EXPECTED_TEST_COUNT.txt` is updated to the true v04 count.

   Recorded evidence of the exact one-process run at v04
   (`python3 -B -W error::ResourceWarning structured_tests.py`):
   `Ran 113 tests` / final `OK` / exit 0 / stderr 0 bytes / 0 skips /
   wall time ~6.7 seconds. Every `subprocess.run` in the suite carries an
   explicit timeout, so the worst case is bounded rather than open-ended.
   At v05 the same exact one-process invocation reports `Ran 132 tests` /
   final `OK` / exit 0 / stderr 0 bytes / 0 skips / ~7.7-7.9 s wall.
7. **Baseline immutability retained.** Every inherited Move 80 v07 file
   remains byte-identical; `rust/`, `src/`, `freeze_record/`,
   `reason_map.json`, the agreement corpus, the Move 79 and Move 80 gates,
   the Move 80 fixtures and expected results, and the inherited status
   documents are all untouched.

## v03 changes (seven hostile-review repairs)

Candidate v02
(9adf8e341328c3453573cf28198d8504ccf07197f8b64a8e9e0071e814922bd9) was
REJECTED at hostile review before any Termux run and is preserved
unchanged as audit history. v03 fixes seven further gaps:

1. **The adopted pre-bootstrap trust order is restored exactly.** The gate
   no longer runs any PATH-resolved external command before trust exists.
   It captures the inherited `LD_PRELOAD` by shell assignment, sanitizes
   and validates with built-ins, rejects a missing Termux preload with
   built-ins, then canonicalizes `$0` using the LITERAL
   `/data/data/com.termux/files/usr/bin/readlink`, requires the canonical
   path to end exactly in
   `/tools/check_move81_structured_verdict_adoption.sh` and to be a regular
   file, derives `_SCRIPT_DIR` and `ROOT` by shell parameter expansion, and
   only then sources `gate_bootstrap.sh`. The prohibited
   `dirname`/`pwd` construction is gone.
2. **The real Move 80 baseline is hash-verified with the trusted
   sha256sum.** After bootstrap and canonical path resolution the gate
   computes the supplied `REAL_MOVE80` hash with `$TRUSTED_SHA256SUM`,
   requires exactly
   `8c08342efae3b17458e33c6ae54ff42bf79d6759170b46cfbf32ef218d0dd2ad`, and
   fails before any baseline comparison on mismatch. The transcript prints
   `REAL_MOVE80 verified by trusted sha256sum:` followed by that hash. A
   different, byte-modified, or merely renamed ZIP cannot become the
   authority.
3. **The baseline ZIP is genuinely safety-inspected before member bytes
   are read**, reusing the adopted Move 80 safety design: no duplicate
   member names, no traversal, no absolute paths, no backslash ambiguity,
   no symlinks, no encrypted entries, and exactly one
   `project-witness-main/` root. The evidence is printed, not merely
   claimed.
4. **The frozen comparison contract is completely validated** before
   either lane is invoked: top-level object; the corpus lane identifier
   (so a bundle comparison cannot silently use the archive corpus); `cases`
   is a list; every case is an object with a unique nonempty string
   `case_id`; `category` is one of the three adopted values;
   `python_scope`/`rust_scope` are `in_scope`/`out_of_scope`; `expected` is
   an object; every in-scope lane has a well-formed expected object with
   `verdict`, `reason_class`, `stage`, `exit_code` of correct type and
   allowed value; agreement and known-divergence cases have both lanes in
   scope; single-implementation cases have exactly one. Every failure is
   deterministic and fails closed — no traceback, no raw exception, no
   contaminated stderr.
5. **Comparison-authority error shapes are corrected.** An invalid
   contract or an unknown case id now emits one top-level
   `record_type=measurement_error` with `operation=compare` and the
   dedicated codes `ADAPTER_COMPARISON_CONTRACT_INVALID` /
   `ADAPTER_UNKNOWN_CASE_ID`. v02 wrongly emitted a comparison record with
   both lanes null under `MEASUREMENT_ERROR`; that shape is gone. After a
   valid case is established, a completed attempted lane is a full verdict
   record, a failed attempted lane is a full measurement_error record, an
   unaffected completed lane remains present, and only an adopted
   out-of-scope lane may be null.
6. **The claimed test matrix is now actually implemented**: per-lane
   underlying-stderr rejection (Python, Rust, archive); the full strict
   framing set (leading space/newline/blank line, trailing space, extra
   trailing newline, prefix, suffix, multiple objects, and the accepted
   single-object form); verifier identity absent/empty/wrong/non-string;
   real inherited-verifier integration against a genuinely prepared bundle
   missing `companion_report.json` and against an honestly prepared
   noncanonical report, plus reason-form, error-form, error-precedence,
   empty and non-string failures; the complete comparison-authority matrix
   including both adopted divergence IDs, agreement, a genuine
   LANE_NOT_APPLICABLE, unexpected divergence, an attempted-lane
   measurement error with the unaffected lane preserved, unknown case id,
   invalid JSON, missing expected object, invalid category, invalid scope,
   duplicate case IDs, wrong corpus lane, and malformed expected shape; and
   gate-authority tests proving a hostile PATH cannot substitute
   pre-bootstrap tools, that the baseline is hash-verified against the
   exact adopted hash before comparison, that unsafe baseline ZIPs
   (traversal, duplicate names, wrong root) are rejected, and that exactly
   one Move 80 child gate is invoked with no independent Move 79 run.
   `EXPECTED_TEST_COUNT.txt` is updated to the actual count.
7. **The changelog candidate identity is corrected** and now distinguishes
   rejected v01, rejected v02, and current v03.

## v02 changes (eight hostile-review repairs)

Candidate v01
(377b9be80e1ccd39e27e7bc6fc503b5672d7f6df4348be05259ef18899d61e35) was
REJECTED at hostile review before any Termux run and is preserved
unchanged as audit history. v02 fixes eight substantive gaps:

1. **Python reason normalization matches the adopted harness.** The
   adapter now reads a Python FAIL's cause with the adopted rule
   `out.get("error", out.get("reason", ""))` — the `error` key first, then
   `reason`. A PASS still uses `reason`. An empty or non-string
   reason/error fails closed. v01 read only `reason`, so a genuine Python
   FAIL that reported its cause under `error` would have been misclassified
   or unmapped.
2. **Underlying stderr is rejected for every lane.** Any non-empty stderr
   from any underlying verifier is `ADAPTER_UNEXPECTED_STDERR`. v01 only
   enforced this on the Python lane.
3. **Comparison status is decided by the frozen authority — and all five
   statuses are now actually reachable.** v01 could only ever emit
   AGREEMENT / UNEXPECTED_DIVERGENCE / MEASUREMENT_ERROR; its README
   claimed DECLARED_DIVERGENCE and LANE_NOT_APPLICABLE were produced, but
   no code path emitted them (a false claim). v02 loads the frozen
   `verify/agreement_harness_v01/corpus/bundle_cases.json` contract,
   requires an explicit `--case-id` and `--comparison-contract`, runs each
   in-scope lane, and compares the actual lane records against that case's
   adopted expected outcomes: AGREEMENT (agreement case, both lanes match),
   DECLARED_DIVERGENCE (known-divergence case, both match),
   LANE_NOT_APPLICABLE (a single-implementation case's out-of-scope lane is
   null and the in-scope lane matches), UNEXPECTED_DIVERGENCE (an in-scope
   lane does not match its adopted outcome), and MEASUREMENT_ERROR (an
   attempted lane fails, an unknown case id, or a malformed contract). An
   out-of-scope lane is legitimately null; an attempted lane that fails is
   preserved as its full measurement_error record, never null.
4. **Strict single-object stdout framing.** The adapter no longer
   `strip()`s underlying stdout. The canonical object must begin at byte 0
   and be followed by at most a single trailing newline; leading
   whitespace/blank lines/prefix, trailing spaces/blank lines/suffix, a
   second object, or surrounding noise each fail closed as
   STDOUT_CONTAMINATION or MULTIPLE_OBJECTS.
5. **Verifier identity is validated, not assumed.** The Rust/archive lanes
   require the underlying object to self-identify as `witness-verify`; an
   absent, empty, or different `verifier` field is
   `ADAPTER_VERIFIER_IDENTITY_MISMATCH`. The lane's `verifier` field is
   never inferred purely from which lane was selected.
6. **Input type is validated honestly.** Bundle lanes
   (`python_bundle`, `rust_bundle`) require the input to be an existing
   directory; the archive lane requires an existing readable regular file.
   A mismatched input type is an adapter usage error (exit 2, no record).
7. **The gate resolves and validates every adapter path through the
   trusted readlink after bootstrap.** The Python entry, frozen reason
   map, comparison contract, trusted interpreter, and adapter are each
   canonicalized to a validated absolute regular-file path before being
   handed to the adapter, and the adapter is invoked with the trusted
   interpreter. The gate also adds a live comparison check on the
   `clean_control` case against the freshly built binary (AGREEMENT, exit
   0, status never verdict-labelled).
8. **The focused suite exercises the repairs.** New/expanded tests cover
   the error-first Python normalization, stderr rejection on every lane,
   all five comparison statuses against the frozen contract (including a
   real LANE_NOT_APPLICABLE with a null out-of-scope lane and a
   DECLARED_DIVERGENCE), strict stdout framing (contamination vs multiple
   objects), verifier-identity mismatch/absence, and input-type
   validation. The suite count is pinned in `EXPECTED_TEST_COUNT.txt`.

No fixture, hash, expected result, reason code, corpus, or Rust/Python
behaviour changed. Every inherited Move 80 v07 file remains byte-identical.

## Roadmap objective and owner clarification

Roadmap Two (Project_Witness_Part_Two_Roadmap_Steps_71_to_130.pdf, Page 2,
Phase One / Block A), Step 81: "Full verifier verdict output — Upgrade the
Rust verifier to produce PASS, FAIL, and INCONCLUSIVE with structured
reason codes aligned to Witness language."

Per the owner's operational clarification, Move 81 upgrades the
verification output CONTRACT to represent the complete PASS / FAIL /
INCONCLUSIVE vocabulary with deterministic structured reason codes; it
does not authorise a lane to emit a verdict its present capability cannot
honestly establish. No Rust PASS path is created; a healthy Rust bundle
remains INCONCLUSIVE (exit 3), and archive-safety success remains
INCONCLUSIVE (exit 3). The full clarification and the preserved original
wording are recorded in `ROADMAP_TWO_MOVE_81_CLARIFICATION.md`.

## What Move 81 adds (new files only)

- `verify/structured_verdict_v01/adapter.py` — the structured-verdict
  adapter. Invokes the adopted commands via explicit absolute paths
  (never searching PATH, never defaulting), captures their output
  internally, validates it fail-closed, and emits exactly one canonical
  record.
- `verify/structured_verdict_v01/schema.py` — fixed structural constants
  and allowed-value enums only. No reason-code or stage mappings live
  here; those come from the inherited frozen reason map at run time.
- `verify/structured_verdict_v01/structured_tests.py` — focused suite
  (stdout-bound runner, pinned count, warning-clean stderr).
- `verify/structured_verdict_v01/EXPECTED_TEST_COUNT.txt` — pinned focused
  test count.
- `verify/structured_verdict_v01/README.md` — scope, honesty boundary, and
  exact capability_scope definitions.
- `verify/structured_verdict_v01/allowlist_move81.json` — the Move 81
  permitted-change allowlist.
- `verify/structured_verdict_v01/check_move81_inherited.py` — baseline
  checker: candidate vs the real Move 80 v07 ZIP member bytes + allowlist.
- `tools/check_move81_structured_verdict_adoption.sh` — the Move 81
  adoption gate.
- `ROADMAP_TWO_MOVE_81_CLARIFICATION.md` — additive documentation-truth
  file (Option A).
- `CHANGELOG_MOVE_81.md` — this file.

No inherited Move 80 v07 file is modified. `MOVE_INDEX.md` and
`CURRENT_RELEASE_STATE.md` are deliberately left byte-identical (see the
clarification file for why).

## Record contract

Three record types under a mandatory `record_type` (verdict / comparison /
measurement_error), each carrying the mandatory envelope: `schema_version`
= `witness-verdict/1`, `producer` = `witness-structured-verdict-adapter`,
`producer_version` = `0.0.1-step81-structured-verdict`.

- Adapter identity (`producer` / `producer_version`) is separate from
  verifier identity (`verifier` / `verifier_version`).
- Adapter-layer failures use a separate `measurement_error_code`
  vocabulary and are never stored in `reason_code`.
- Underlying exit 2, timeout, signal termination, and launch failure all
  produce a measurement_error record, never a verdict.
- `detail` is optional and included only when a deterministic safety check
  proves it free of paths, temp names, host values, timestamps, random
  values, and input-derived disclosure.
- Comparison records hold both complete lane records plus a separate
  `comparison_status` (AGREEMENT / DECLARED_DIVERGENCE /
  UNEXPECTED_DIVERGENCE / LANE_NOT_APPLICABLE / MEASUREMENT_ERROR), never a
  merged verdict and never labelled PASS/FAIL/INCONCLUSIVE. An attempted
  lane that fails is preserved as its measurement_error record, never
  null.
- `stage` and `reason_code` are resolved only from the inherited frozen
  `verify/agreement_harness_v01/reason_map.json`, supplied via
  `--reason-map`; an unknown reason or missing stage mapping fails closed.
- `input_identity` is omitted from schema v1 (no adopted deterministic
  directory tree-hash exists).

## Python verifier version finding (binding clarification 5)

The adopted Python implementation DOES expose an authoritative
implementation version constant: `COMPANION_CLI_VERSION = "0.3.0"` in
`src/12_companion_cli_v031/companion_lib/versions.py`. The adapter reads
this constant from the implementation's own source tree (the sibling of
the supplied `--python-entry`), never from the input bundle. Python
verdict records therefore carry `verifier_version` = `"0.3.0"`. If a
Python implementation without such a constant were supplied,
`verifier_version` would be omitted for that lane (never `"unknown"`,
never a reason to fail an otherwise valid verdict).

## Exit contract

Verdict: PASS→0, FAIL→1, INCONCLUSIVE→3. Underlying measurement failure→1
(one measurement_error record). Adapter CLI usage error→2 (no record).
Comparison: AGREEMENT / DECLARED_DIVERGENCE / LANE_NOT_APPLICABLE→0;
UNEXPECTED_DIVERGENCE / MEASUREMENT_ERROR→1.

## Adoption gate

`tools/check_move81_structured_verdict_adoption.sh` establishes the
adopted trusted Termux bootstrap, verifies the candidate against the real
Move 80 v07 ZIP (byte-identical inherited files; additions exactly the
Move 81 allowlist), removes `rust/target`, performs a fresh trusted Cargo
build, runs all Cargo tests, verifies the exact Rust binary version, runs
the focused structured-verdict suite (pinned count, no skips, empty
stderr), proves live determinism and the Rust honesty property against the
freshly built binary, proves legacy default-output preservation, and
invokes exactly one complete Move 80 adoption/regression child gate (which
already includes the full Move 79 regression). The inner
SYSTEM_AGREEMENT_RESULT: FAIL remains expected and is required as
evidence.

Build evidence policy: source identity plus a fresh trusted build are
authoritative; cross-run binary-byte identity is not required (reproducible
builds are not yet adopted).

## Candidate history and adoption state

- **v01** — `377b9be80e1ccd39e27e7bc6fc503b5672d7f6df4348be05259ef18899d61e35`
  — REJECTED at hostile packaged-byte review. Preserved unchanged as audit
  history. Never run on Termux; never adopted.
- **v02** — `9adf8e341328c3453573cf28198d8504ccf07197f8b64a8e9e0071e814922bd9`
  — REJECTED at hostile packaged-byte review. Preserved unchanged as audit
  history. Never run on Termux; never adopted.
- **v03** — `cc8acafa579940ef05381cd58e3854d14b723b39aae653dbaf9b75e4331a8992`
  — REJECTED at hostile packaged-byte review. Preserved unchanged as audit
  history. Never run on Termux; never adopted.
- **v04** — `021fd6c43cf8aeb21e35557ec487536f8f5e6fdca23f481fadae660b805f6f68`
  — REJECTED at hostile packaged-byte review. Preserved unchanged as audit
  history. Never run on Termux; never adopted.
- **v05** — `93634ed78b89c02604f5465ea4eb207b282ed1d77c8442082c00b8d586e96459`
  — REJECTED at hostile packaged-byte review. Preserved unchanged as audit
  history. Never run on Termux; never adopted.
- **v06** — `242729fbfbc63a93e881ffc105f066b9c047518aafe0e55d616a3b03e3d3f54f`
  — REJECTED at hostile packaged-byte review. Preserved unchanged as audit
  history. Never run on Termux; never adopted.
- **v07** — `1d46b6d8f74cecebb2b63f696ddc92cee62c0b099ad1fa68ef2fa5f89caaf36b`
  — REJECTED after its FIRST GENUINE TERMUX ADOPTION RUN, at Stage F, for
  the gate-composition defect described above. First-run transcript
  `MOVE_81_V07_TERMUX_GATE.txt`, SHA-256
  `8849762e9e255dd57c48b3f8bbcf6d5eb2b7ac047063a766421d0075e3772cdc`.
  Preserved unchanged as audit history; never adopted.
- **v08** — this candidate. Packaged for independent hostile packaged-byte
  review. It has **not** been run on a real Termux device and is **not
  adopted**.

No fixture, hash, expected result, reason code, corpus, or Rust/Python
behaviour changed in any of these candidates. Every inherited Move 80 v07
file remains byte-identical.
