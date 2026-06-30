# Repair ledger

Issues found and fixed during the build of Sentinel Core (v0.1.0 through
v0.2.2), in the
project's "make claims, attack claims, repair claims, narrow claims" spirit.
Each entry is a thing that was wrong at some point and what was done about it.
Newest first.

## R16 — DOCUMENTATION (v0.2.2): stale version strings corrected
**Found (review):** several user-facing strings still named old versions or an
old layout: the CLI header and `argparse` description said "Sentinel Core v0.1";
the package and selfcheck headers said "v0.1"; the README layout block named
`sentinel_core_v01/`; README and KNOWN_LIMITATIONS described the *current* scope
as "v0.1" ("v0.1 supports only CREATE_DIRECTORY", "out of scope for v0.1"); the
INVARIANTS and THREAT_MODEL intros said "Sentinel Core v0.1"; and
`release_check.py`'s skipped-checksum hint named `sentinel_core_v014.sha256`.
**Fix (documentation / version-string only — no code, protocol, or test change):**
updated every *current-identity / current-scope* reference to v0.2.2, fixed the
layout directory name and the checksum-hint filename, and corrected the ledger
header to span v0.1.0–v0.2.2. Deliberately left unchanged: all *historical*
references that record WHEN something was introduced or repaired (e.g. "the
v0.1.1 repair", "(v0.1.3)", "Since v0.1.2", "v0.1.0 attack shape", the
versions.py changelog, and the earlier ledger entries) — those are accurate
history and rewriting them would be wrong. The `--version` flag and CLI
description are driven by `PACKAGE_VERSION` and now report `Sentinel Core
v0.2.2`.
**Verified:** all release gates pass from a clean extraction; the test count is
unchanged (144) and selfcheck is unchanged (15/15), confirming no behavioural
change.

## R15 — REPLAY HONESTY (v0.2.1 → v0.2.2): environmental ERROR reported too strongly
**Found (external):** take a clean successful run, mutate its success RESULT into
`ERROR_EXECUTION_FAILED` (executed=false), recompute that receipt's hash, the
next receipt's `prior_hash`, the close receipt's hash, and the run seal, then
replay. Replay returned plain **PASS** and marked the forged receipt `MATCH*`.
The structural acceptance is expected under the unkeyed-hash limitation (L4) and
the non-reproducibility of environmental errors (L10) — but the *verdict* was too
strong: a run that leans on a `MATCH*` exception read identically to a strictly
re-derived run.
**Fix (reporting/honesty only — no protocol change):**
- `replay` now reports one of four verdicts: `PASS_STRICT`,
  `PASS_WITH_ENVIRONMENTAL_EXCEPTIONS`, `FAIL`, `REPLAY_INCOMPATIBLE`.
- Any run that uses one or more `MATCH*` environmental exceptions reports
  `PASS_WITH_ENVIRONMENTAL_EXCEPTIONS`, never `PASS_STRICT`. The final report
  lines are `REPLAY VERDICT: <verdict>` plus a one-line summary naming how many
  environmental ERROR receipts were structurally verified rather than reproduced.
- Process exit code stays 0 for BOTH pass verdicts (the run is accepted); the
  text distinguishes them. `FAIL`/`REPLAY_INCOMPATIBLE` stay non-zero.
- `replay_from_path()` now returns a `ReplayResult` (`.ok`, `.verdict`,
  `.report`) that still unpacks as the historical `(ok, report)` tuple, so every
  existing caller keeps working.
- Issue 2: the stale single-receipt comment at the top of
  `sentinel_core/kernel.py` was replaced with the correct two-stage
  INTENT/RESULT description.
- Docs updated: README (verdict categories), KNOWN_LIMITATIONS L10 (structurally
  verified, not strictly reproduced; interaction with L4), RUN_FORMAT (verdict
  section + `ReplayResult`).
- Core unchanged: `IMPL_VERSION` stays 0.2.0; v0.2.0 runs remain replayable.
**Verified:** the exact attack now yields `PASS_WITH_ENVIRONMENTAL_EXCEPTIONS`
(exit 0) instead of plain PASS, while a clean run yields `PASS_STRICT`. New tests
prove: clean run -> PASS_STRICT; genuine execution-error and postcondition-error
runs -> PASS_WITH_ENVIRONMENTAL_EXCEPTIONS; the forged-ERROR-with-recomputed-seal
attack -> PASS_WITH_ENVIRONMENTAL_EXCEPTIONS (not PASS_STRICT); structural tamper
-> FAIL; old version vector -> REPLAY_INCOMPATIBLE. A new selfcheck gate
(`replay_verdict_categories`) asserts the two PASS categories. 144 tests pass
under normal and -O; selfcheck 15/15 both modes.

## R14 — RELEASE BLOCKER (v0.2.0 → v0.2.1): CLI subprocess tests blocked clean exit
**Found (external):** in a clean extraction `python3 -m unittest discover -s
tests -v` reached `test_valid_cli_append_still_works` and then did not exit; even
`python3 -m unittest tests.test_append_integrity.TestAppendIntegrityCLI -v`
printed OK but the process did not terminate cleanly. Because release_check.py
runs the unit suite, it hung too.
**Cause:** `TestAppendIntegrityCLI` exercised the CLI by spawning
`python sentinel.py` via `subprocess.run(..., capture_output=True)`. A spawned
child under captured pipes can leave an inherited pipe write-end or a lingering
process that holds the interpreter open at interpreter shutdown — an
intermittent, environment-dependent hang (it completed in some environments and
not others).
**Fix (per the spec's preference — avoid CLI subprocess tests where direct
tests suffice):** the CLI tests now invoke `sentinel.main()` IN-PROCESS via a
small `run_cli()` helper that captures stdout/stderr with
`contextlib.redirect_*` and normalises both returned codes and `SystemExit` to
an exit code. The suite now spawns NO subprocesses at all: no child processes,
no inherited pipes, nothing to block shutdown. The class name
`TestAppendIntegrityCLI` is preserved so the exact acceptance command still
resolves, and all three end-to-end attack reproductions still run (now ~10x
faster).
- A new guard test `tests/test_no_subprocess_in_tests.py` parses every test
  module and fails if any imports or uses `subprocess`, preventing regression.
- The only component that runs subprocesses remains `release_check.py` (by
  design), each with an explicit timeout.
- Core unchanged: `IMPL_VERSION` stays 0.2.0 (v0.2.0 runs remain replayable);
  only `PACKAGE_VERSION` advanced to 0.2.1.
**Verified:** from a clean extraction, the full discover, the `-O` discover, the
specific `TestAppendIntegrityCLI` command, the ResourceWarning sweep, and
`release_check.py` all terminate on their own (measured via `communicate()`,
not killed) in ~1.3s / ~1.6s / ~0.1s / ~1.4s / ~4.3s respectively, with no
lingering `unittest`/`sentinel` processes afterwards. 138 tests pass under
normal and `-O`; selfcheck 14/14 both modes.

## R13 — ARCHITECTURAL (v0.1.4 → v0.2.0): two-stage INTENT/RESULT receipts
**Motivation (carried limitation L1):** through v0.1.x a single receipt was
written AFTER mkdir, so the filesystem side effect could occur before the final
receipt was durably persisted. A persistence failure after mkdir left an
unrecorded orphan directory.
**Change:** replaced the single-receipt model with two stages.
- Every receipt now carries `stage` in {INTENT, RESULT, SESSION_CLOSE} plus
  `intent_receipt_id`/`intent_hash`. A new reason code `INTENT_CREATE_DIRECTORY`
  marks the approved-but-not-executed stage.
- For an approved CREATE: build + persist + commit an INTENT BEFORE mkdir; then
  mkdir; verify; then build + persist a RESULT that references the INTENT.
  BLOCK/DRY_RUN stay single self-contained RESULTs (they never execute).
- If INTENT persistence fails: no mkdir, no side effect, nothing committed.
- If mkdir/postcondition fails after INTENT: a RESULT/ERROR is recorded
  (session stays open, run stays replayable). These environmental errors are not
  reproducible by replay, which verifies them structurally (`MATCH*`) — see
  KNOWN_LIMITATIONS L10.
- If the RESULT write fails after mkdir: the run is left in an explicit
  `RESULT_MISSING_AFTER_INTENT` state. A new `ReceiptChain.unresolved_intent()`
  detector makes append, close, and replay fail closed on a trailing unresolved
  INTENT rather than treat it as complete (KNOWN_LIMITATIONS L1a).
- `verify_chain` enforces the pairing invariants (every resolving RESULT
  immediately follows and hash-matches its INTENT; no orphan RESULT; no double
  RESULT for one INTENT; contiguous ids; no close over an unresolved INTENT).
- Replay drives the fresh kernel once per logical action (an INTENT consumes its
  following RESULT) and compares stage + intent linkage + session states in
  addition to decision/reason/executed.
- Version vector advanced (`impl_version` 0.2.0, `receipt_schema_version` 0.2.0);
  v0.1.x runs are `REPLAY_INCOMPATIBLE` and refused for append (exact-version
  rejection, no migration).
**Preserved unchanged:** CREATE_DIRECTORY-only; manifest-authoritative
allowed_root; append-time integrity loader; session-closure grammar; run
sealing; hostile-JSON handling; no bare asserts; stdlib only; release_check.py
with independent subprocess gates; selfcheck.py not launching unit tests.
**Verified:** new `tests/test_two_stage.py` (19 tests) covers INTENT-before-mkdir,
all three failure rules, the incomplete-run detection, the replay pairing
invariants (missing/duplicate/mutated INTENT and RESULT), and the preserved
guarantees; a new `two_stage_intent_result` selfcheck gate is added. Full suite
137 tests pass under normal and `-O`; selfcheck 14/14 both modes.

## R12 — RELEASE BLOCKER (v0.1.3 → v0.1.4): full selfcheck could deadlock
**Found (external):** `python3 -u selfcheck.py` printed `imports`, `compileall`,
`unit_tests`, then hung before completing `unit_tests_-O`. The v0.1.3 mitigation
(an env-flag "lightweight" mode) reduced but did not remove the cause: full
selfcheck still ran the unit suite as a subprocess, that subprocess ran
`test_selfcheck`, which spawned ANOTHER selfcheck subprocess. With
`capture_output=True`, a surviving grandchild holding the inherited stdout/stderr
pipe write-end could make the parent's `communicate()` block on an EOF that never
arrived — an intermittent, timing-dependent pipe-inheritance deadlock that
typically struck on the second (-O) nested pass. Running `-O` directly never
nested, so it always passed — exactly the reported asymmetry.
**Fix (architectural):** no release gate spawns another release gate.
- `selfcheck.py` no longer has `unit_tests` / `unit_tests_-O` gates and imports
  no `subprocess`; it runs only internal, in-process invariant gates (13).
- `tests/test_selfcheck.py` runs `selfcheck.main([])` IN-PROCESS, so the unit
  suite never spawns selfcheck as a subprocess. It also adds a structural guard
  asserting selfcheck imports no `subprocess` and defines no `unit_tests` gate,
  to prevent regression.
- New `release_check.py` orchestrates the full sequence (compileall → unit →
  unit -O → selfcheck → selfcheck -O → ResourceWarning sweep → checksum) as
  INDEPENDENT subprocesses, each with an explicit timeout (timeout = failure).
  It is never invoked by a gate.
- `--skip-unit-gates` is kept as an accepted no-op for compatibility.
- The deterministic core is unchanged, so the manifest version vector is NOT
  bumped (v0.1.3 runs stay replayable); only `PACKAGE_VERSION` advanced to
  0.1.4.
**Verified:** from a clean extraction, all acceptance commands pass without
hanging — `compileall`, `unittest -v`, `-O unittest -v`, `selfcheck`,
`-O selfcheck`, `selfcheck --skip-unit-gates`, the ResourceWarning sweep, and
`release_check.py`. Full `selfcheck.py` ran 5× consecutively and the unit suite
3× back-to-back with no hang.

## R11 — RELEASE BLOCKER (v0.1.2 → v0.1.3): unit/selfcheck recursion could hang
**Found (external):** the required command `python3 -m unittest discover -s
tests` could hang through `test_selfcheck_runs_clean -> selfcheck.py ->
unit_tests -> unit_tests_-O`. The unit suite launched full selfcheck, and full
selfcheck launches the unit suite. v0.1.2 guarded this with an env-flag skip,
but that left the in-suite selfcheck test either skipped (under the flag) or
recursive (without it) — fragile.
**Fix:** added a lightweight selfcheck mode `python3 selfcheck.py
--skip-unit-gates` that omits the two gates which launch the unit suite.
`test_selfcheck_runs_clean_lightweight` now always calls that mode, so plain
`unittest discover` can never trigger a nested full selfcheck — the recursion is
broken structurally, not by an env flag. The full `python3 selfcheck.py`
remains a separate release gate, run directly. Every `subprocess.run` in tests
and selfcheck now has an explicit `timeout=` (120s in tests, 300s in
selfcheck), so a hang fails closed instead of blocking forever.
**Verified:** the four release gates each complete independently
(`unittest -v`, `-O unittest -v`, `selfcheck`, `-O selfcheck`); the bare
`unittest discover` finishes in ~1s under a 180s watchdog. `test_selfcheck.py`
asserts the lightweight run prints the "unit-test gates skipped" banner.

## R10 — RELEASE BLOCKER (v0.1.2 → v0.1.3): semantic closure validation gap
**Found (external attack on v0.1.2):** a run was forged whose final receipt was
still `ALLOW_CREATE_DIRECTORY` but with `post_session_state` edited to
`CLOSED_BY_OPERATOR`; the receipt hash was recomputed and a valid run seal
built over it. Replay accepted it as PASS. The closure transition was only
*implied* by how the kernel emits receipts, never *validated* on load — so a
recomputed hash over a forged transition passed every check.
**Fix:** made the session-transition grammar an explicit, single-sourced
invariant. `reason_codes.is_session_close_shape` defines the one legal close
shape (decision=ALLOW, reason=ALLOW_SESSION_CLOSE,
request={'action_type':'CLOSE_SESSION'}, executed=False). It is enforced at
four layers: (1) receipt construction — every receipt must be OPEN->OPEN unless
it is exactly a close receipt, which must be OPEN->CLOSED_BY_OPERATOR; this runs
on load too, since loading reconstructs each receipt; (2) chain verification —
defence in depth for already-constructed chains; (3) `build_run_seal` and
`validate_run_seal` — a sealed run's final receipt must be a real close receipt;
(4) replay — now compares `pre_session_state` and `post_session_state`, not just
(decision, reason_code, executed). `receipt_schema_version` bumped to 0.1.1.
**Verified:** `tests/test_closure_grammar.py` forges CREATE, BLOCK, DRY_RUN, and
ERROR final receipts to closed (recomputed hash + valid seal) and asserts replay
fails for each; asserts a wrong-request or executed=True close receipt fails
construction; asserts seal build/validate reject a non-close final receipt; and
asserts a genuine create->close->replay still passes. The v0.1.2 forge was
confirmed to reproduce (replay PASS) before the fix. A 15th selfcheck gate
(`forged_closure_fails`) covers it.

## R9 — RELEASE BLOCKER (v0.1.1 → v0.1.2): append trusted "no seal" as "open and valid"
**Found (external attack on v0.1.1):** the CLI loader treated an existing run
as appendable if `run_seal` was missing, and hardcoded the journal session
state to `OPEN`. Two attacks followed. Attack 1: create → close → manually
delete `run_seal` → `create` again: the new action was accepted and the
directory created despite the `CLOSED_BY_OPERATOR` receipt in the chain.
Attack 2: delete the first receipt of an open two-receipt run → `create`
again: the action executed onto a structurally invalid chain, producing
duplicate receipt IDs and broken linkage. Replay failed later in both cases —
but the real filesystem side effect had already happened. Detection-after-the-
fact is not prevention.
**Fix:** added `sentinel_core/run_loader.py::open_run_for_append`, which all
CLI append AND close paths now use. Before any kernel exists it: loads the run
(hostile-JSON-safe), validates the manifest, reloads every receipt with
self-hash recomputation, runs full `chain.verify_chain(manifest)` (contiguous
IDs from 0, prior-hash linkage, versions, session continuity, closure
placement), refuses any run containing a receipt with a non-OPEN
`post_session_state` — regardless of `run_seal` presence, because the seal is
corroborating evidence of closure, never its sole witness — refuses a present
seal, and derives the journal session state from the chain head instead of
hardcoding `OPEN`. Rejections raise before a Kernel is constructed, so no
action and no filesystem side effect is possible against an invalid or closed
run. `cmd_close` going through the same loader also prevents a second close
receipt being appended to a deseal-tampered run.
**Verified:** `tests/test_append_integrity.py` (15 tests): both attacks
reproduced end-to-end through the CLI as reported and refused with
directory-listing proof of zero filesystem change and hash proof the run file
itself is untouched by a refused load; deleted-first/middle receipt, broken
prior_hash (with recomputed self-hash so only linkage is broken), duplicate
IDs, and tampered fields all refuse; valid open runs still append with
contiguous IDs; sealed runs still refuse; replay behaviour unchanged. Attack 1
was confirmed to reproduce against v0.1.1 before the fix (the test has teeth).
A 14th selfcheck gate (`append_integrity`) covers both attack shapes.

## R5 — RELEASE BLOCKER (v0.1.0 → v0.1.1): the root boundary was caller-selected
**Found (external attack on v0.1.0):** the manifest stored an `allowed_root`,
but the kernel evaluated path policy against the `allowed_root` supplied inside
each individual request. A run created with manifest root A could process a
request self-declaring root B and create a directory under B. Replay still
passed, because the run was internally consistent — the configured boundary was
recorded but never authoritative.
**Fix:** removed `allowed_root` from the request schema entirely (action schema
1.0.0 → 1.1.0). The kernel now passes `journal.manifest["allowed_root"]` into
`decision.evaluate()`, which forwards it to path policy. A request that still
carries `allowed_root` is rejected as an extra field (`BLOCK_SCHEMA_INVALID`),
so v1.0.0-style requests fail closed instead of being honoured. The CLI's
`--allowed-root` now configures the run manifest only: required when creating a
new run, and refused on append unless it canonicalises to the manifest root.
The version vector bump means v0.1.0 run files are `REPLAY_INCOMPATIBLE` by
design rather than re-interpreted.
**Verified:** `tests/test_boundary_authority.py` proves manifest root A +
attempted root B is blocked with neither root modified (both the v1.0.0-style
field-injection shape and the absolute-target-under-B shape), that recorded
requests carry no root, and that replay of such a run passes while touching
nothing outside its sandbox. `tests/test_replay.py` proves an injected
`allowed_root` in a saved request breaks the receipt hash, a mutated manifest
root fails manifest validation, and an old version vector is refused.

## R6 — Postcondition-failure branch was not fault-injected (v0.1.1)
**Found:** v0.1.0's TEST_RESULTS honestly flagged `ERROR_POSTCONDITION_FAILED`
as covered-by-construction only.
**Fix:** added `tests/test_kernel_faults.py` with a surgical fault injection:
`os.path.isdir` lies only about the target (so the path policy's earlier
root/parent checks still see the truth and the request reaches execution),
forcing the postcondition branch. Also added an injected-`mkdir`-failure test
for `ERROR_EXECUTION_FAILED`. Both produce controlled, persisted ERROR receipts
with the session left open.

## R7 — Non-JSON Python objects could crash receipt construction (v0.1.1)
**Found:** a request that failed schema validation was recorded raw in its
BLOCK receipt. If the raw input contained non-JSON-native values (a set, a
custom object, NaN, non-string dict keys), the strict canonical encoder raised
mid-receipt — an uncontrolled crash on hostile input to `Kernel.process()`.
**Fix:** schema-invalid requests are now passed through `_sanitize_for_record`,
which produces a faithful JSON-native record with tagged
`<unrepresentable: ...>` markers (depth- and length-capped). Valid requests are
unaffected (the normalised request is recorded as before). Runs containing
sanitised hostile records verify and replay.
**Verified:** `test_kernel_faults.py` (set values, arbitrary objects, NaN,
non-string keys, and replay of a hostile-record run).

## R8 — Unclosed file handles in tests and selfcheck (v0.1.1)
**Found:** several `json.load(open(...))` / `json.dump(..., open(...))` calls
in tests and selfcheck gates leaked file handles, producing `ResourceWarning`s.
**Fix:** all converted to `with open(...)` context managers.

## R1 — Confused session-close model (fixed)
**Found:** the first `Kernel.close` implementation tried to mutate the last
receipt's session state, but receipts are frozen, and an alternative path raised
`NotImplementedError`. The closure semantics were muddled and inconsistent.
**Fix:** modelled session close as a real, recorded action. Added the
`ALLOW_SESSION_CLOSE` reason code (an `ALLOW` decision with `executed=False`)
and a single `close_session()` method that emits one final receipt transitioning
`OPEN → CLOSED_BY_OPERATOR`, persisted-then-committed like any other receipt,
with the run seal bound to it.
**Verified:** `test_kernel_create_directory.py::test_close_emits_final_receipt`
and the replay tests.

## R2 — Wrong test assertion for shell-metacharacter target (fixed)
**Found:** `test_path_policy.py::test_no_shell_metacharacters_executed` asserted
that `"x; rm -rf /"` would be blocked as parent-missing. In fact it normalises
to a literal child directory name directly under the root, so the correct,
safe behaviour is `ALLOW` (created as a literal name — which is exactly the
proof that no shell splitting occurs).
**Fix:** corrected the assertion to expect `ALLOW` and to confirm the resolved
target is a literal child of the root. The security property (no shell) is
re-proven in `test_security_boundaries.py::test_no_shell_injection_executed`,
which shows a sentinel file is *not* deleted.

## R3 — Selfcheck recursion via the test suite (fixed)
**Found:** `selfcheck.py` runs the unit-test suite as a gate; the suite includes
`test_selfcheck.py`, which shells back out to `selfcheck.py` — an unbounded
recursion.
**Fix:** `test_selfcheck.py` skips its subprocess invocation when the
environment variable `SENTINEL_IN_SELFCHECK=1` is set, and `selfcheck.py` sets
that variable when it launches the test suite. The selfcheck still runs as a
genuine gate when invoked directly.

## R4 — ResourceWarning from unclosed files in the assert scanner (fixed)
**Found:** the bare-assert AST scan in `test_selfcheck.py` opened files without
closing them, raising `ResourceWarning` under the test runner.
**Fix:** wrapped the reads in `with open(...)`.

## Carried forward from the reference architecture

The following were lessons already learned in Embodied Witness v0.5.x and built
into Sentinel from the start, rather than discovered here:

- **Hostile-JSON loader:** `load_run_file` catches `RecursionError` (deeply
  nested JSON) along with the other decoder failures and maps them all to a
  controlled `ManifestError`, so replay fails closed instead of crashing. This
  mirrors the v0.5.1 → v0.5.2 fix in the reference project.
- **No dead/non-atomic save path:** there is a single atomic write path
  (`AtomicFileBackend`); there is no separate unused, non-atomic save function.
- **No bare asserts:** every invariant uses `require()` or an explicit raise, so
  behaviour is identical under `python -O`.
