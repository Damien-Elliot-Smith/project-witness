# Invariants

These are the properties Sentinel Core v0.2.2 is built to hold. Each is enforced
in code with an explicit raise or the `require()` helper (never a bare
`assert`, so the property survives `python -O`), and exercised by tests.

## I1 — Single action type
The only action that can ever be allowed or executed is `CREATE_DIRECTORY`.
Any other `action_type` is blocked with `BLOCK_UNKNOWN_ACTION` and never
touches the filesystem.
Enforced in: `action_schema.py`, `decision.py`. Tested in:
`test_kernel_create_directory.py`, `test_security_boundaries.py`.

## I2 — Structured requests only
The deterministic core accepts only a dict with the exact CREATE_DIRECTORY
field set and the exact declared pre/postconditions. Strings (natural
language), lists, numbers, missing fields, and extra fields are all rejected
with `BLOCK_SCHEMA_INVALID`.
Enforced in: `action_schema.py`. Tested in: `test_action_schema.py`.

## I3 — No action outside allowed_root
A directory is created only when its fully resolved path lies inside the
realpath-resolved `allowed_root`. Lexical `..` escape, absolute targets outside
the root, and symlink escape are each blocked with a distinct reason code.
Enforced in: `path_policy.py`. Tested in: `test_path_policy.py`,
`test_security_boundaries.py`.

## I3a — The boundary is run-configured, never caller-selected (v0.1.1)
`allowed_root` lives in the run manifest only. The kernel passes
`manifest["allowed_root"]` into path policy for every request. Requests carry
no `allowed_root` field (request schema v1.1.0); a request that includes one is
rejected as `BLOCK_SCHEMA_INVALID`, so a v1.0.0-style self-declared root fails
closed rather than being honoured. A run created with root A can never act
under a request-named root B.
Enforced in: `action_schema.py`, `kernel.py`, `decision.py`. Tested in:
`test_boundary_authority.py`.

## I4 — No shell, ever
Directory creation uses `os.mkdir` (a single level) only. No `subprocess`, no
`os.system`, no shell string is constructed or executed anywhere in the core.
A target containing shell metacharacters is treated as a literal directory
name.
Enforced in: `persistence.py`. Tested in: `test_security_boundaries.py`.

## I5 — No overwrite
If the target already exists (including as a symlink, checked with `lexists`),
the request is blocked with `BLOCK_TARGET_ALREADY_EXISTS`. `os.mkdir` provides
a second fail-closed guard against a check-to-execute race.
Enforced in: `path_policy.py`, `persistence.py`. Tested in:
`test_path_policy.py`, `test_persistence.py`.

## I6 — A receipt for every request
Every request processed while the session is open produces exactly one receipt
(ALLOW, BLOCK, DRY_RUN, or ERROR). Closing the session produces one final
`ALLOW_SESSION_CLOSE` receipt.
Enforced in: `kernel.py`. Tested in: `test_kernel_create_directory.py`.

## I7 — Persistence before commit, per stage (v0.2)
In-memory state (the receipt chain and session state) is advanced only **after**
the run file containing the new receipt has been durably written. This holds for
EACH of the two stages: the INTENT is persisted-and-committed before any mkdir,
and the RESULT is persisted before the action is considered complete. If
persistence fails, no further state is committed and the failure is raised.
Enforced in: `journal.py`, `kernel.py`. Tested in: `test_persistence.py`,
`test_two_stage.py`.

## I8 — Hash-chained receipts
Each receipt carries a canonical SHA-256 hash over its full payload and the
prior receipt's hash. Recomputation on load detects any field mutation; broken
linkage detects insertion, deletion, or reordering.
Enforced in: `receipts.py`. Tested in: `test_replay.py`.

## I9 — Closed runs are sealed
When a run closes, a `run_seal` binds the manifest hash, receipt count, and the
final receipt's id/hash/state. Closed/audit replay requires a valid seal, so a
cleanly truncated suffix (e.g. a deleted final receipt) is rejected.
Enforced in: `run_seal.py`, `journal.py`. Tested in: `test_run_seal.py`,
`test_replay.py`.

## I10 — Active replay
Replay does not merely compare stored final states. It verifies the saved chain
(hashes, linkage, versions, seal) and then re-derives every request through a
fresh kernel against a reconstructed sandbox, comparing the
`(decision, reason_code, executed)` projection for each receipt.
Enforced in: `replay.py`. Tested in: `test_replay.py`.

## I11 — Fail closed on hostile input
The run-file loader maps every decoder failure — malformed JSON, bad encoding,
and deeply nested input that raises `RecursionError` — to a controlled
`ManifestError`, so replay never crashes on a hostile file. Likewise,
`Kernel.process()` accepts arbitrary Python objects without crashing: a request
that fails schema validation and contains non-JSON-native values (sets, custom
objects, NaN, non-string keys) is recorded as a sanitised, tagged JSON-native
copy in its BLOCK receipt.
Enforced in: `manifest.py`, `replay.py`, `kernel.py`. Tested in:
`test_replay.py`, `test_kernel_faults.py`.

## I12 — No bare asserts; `-O` safe
No runtime or selfcheck code uses a bare `assert`. All invariants use explicit
raises or `require()`. The test suite and selfcheck pass identically under
`python -O`.
Enforced throughout. Tested in: `test_selfcheck.py` (AST scan) and by running
everything under `-O`.

## I13 — Append requires a fully valid, genuinely open run (v0.1.2)
Opening an existing run for append performs the same integrity verification as
replay BEFORE any kernel exists: manifest validation, per-receipt hash
recomputation, full chain structure (contiguous IDs, prior-hash linkage,
versions, session continuity, closure placement), and closure checks. A run
containing a session-closing receipt refuses append even if its run_seal has
been deleted — the seal corroborates closure but is never its sole witness. A
structurally broken chain (deleted, duplicated, reordered, or tampered
receipts) refuses append before any action can execute, so no filesystem side
effect is possible against an invalid or closed run. The journal session state
is derived from the chain head, never hardcoded.
Enforced in: `run_loader.py` (used by all CLI append/close paths). Tested in:
`test_append_integrity.py` (including end-to-end CLI reproductions of both
v0.1.1 attacks).

## I14 — Session-closure grammar is enforced, not assumed (v0.1.3)
The session may transition `OPEN -> CLOSED_BY_OPERATOR` **only** via a real
`ALLOW_SESSION_CLOSE` receipt: `decision=ALLOW`,
`reason_code=ALLOW_SESSION_CLOSE`, `request={'action_type': 'CLOSE_SESSION'}`,
`executed=False`. Every non-close receipt must be `OPEN -> OPEN`. This grammar
is enforced at four independent layers: receipt construction (so it holds on
load, since loading reconstructs each receipt), chain verification, run-seal
build/validation (a sealed run's final receipt must be a real close receipt),
and replay (which now compares `pre_session_state` and `post_session_state`,
not only decision/reason/executed). A CREATE/BLOCK/DRY_RUN/ERROR receipt edited
to `CLOSED_BY_OPERATOR` and rehashed — even with a freshly built valid seal —
is rejected.
Enforced in: `reason_codes.py` (single source of truth `is_session_close_shape`),
`receipts.py`, `run_seal.py`, `replay.py`. Tested in: `test_closure_grammar.py`.

## I15 — Release gates do not spawn each other (v0.1.4)
This is a harness-reliability property rather than a protocol invariant, but it
is load-bearing for release. `selfcheck.py` runs only internal, in-process
invariant gates and launches no subprocess. The unit-test suite runs
`selfcheck.main()` in-process and never spawns the suite or selfcheck as a
subprocess. The full external sequence lives in `release_check.py`, which runs
each step as an independent, explicitly timed subprocess and is itself never
invoked by a gate. Because no gate spawns another gate, the intermittent
pipe-inheritance deadlock that affected full `selfcheck.py` through v0.1.3
cannot occur.
Enforced in: `selfcheck.py`, `tests/test_selfcheck.py` (structural guard:
asserts selfcheck imports no `subprocess` and has no `unit_tests` gate),
`release_check.py`. Tested in: `test_selfcheck.py`.

## I16 — Two-stage INTENT before side effect (v0.2)
Every approved CREATE_DIRECTORY records an INTENT receipt that is durably
persisted AND committed before `mkdir` runs. The execution outcome is then
recorded in a RESULT receipt that references the INTENT by id and hash. The
ordering is load-bearing: a crash before mkdir leaves a committed INTENT with no
side effect; a crash after mkdir but before the RESULT is persisted leaves a
detectable RESULT_MISSING_AFTER_INTENT run. The pairing invariants (every INTENT
resolved by exactly one immediately-following hash-matching RESULT; no orphan
RESULT; contiguous ids; no close over an unresolved INTENT) are enforced at
receipt construction, chain verification, the append loader, and replay.
Enforced in: `kernel.py`, `journal.py`, `receipts.py`, `run_loader.py`,
`replay.py`. Tested in: `test_two_stage.py`.
