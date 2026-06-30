# Known limitations

Sentinel Core v0.2.2 is a narrow prototype. These are the honest edges. None of
them are hidden; each is something a reviewer should weigh.

## L1 — RESOLVED in v0.2 (two-stage INTENT/RESULT)
The v0.1.x single-receipt limitation (mkdir could happen before the final
receipt was persisted) is fixed. v0.2 persists and commits an INTENT receipt
*before* any mkdir, then records a RESULT. The remaining honest edge is the
RESULT-persistence-failure window, handled explicitly below (L1a) rather than
hidden.

## L1a — RESULT_MISSING_AFTER_INTENT window (explicit, not hidden)
If mkdir succeeds but the RESULT write then fails (e.g. a crash in between), the
directory exists, the INTENT is committed, but no RESULT is. The run is left in
a `RESULT_MISSING_AFTER_INTENT` state. This is NOT silently treated as complete:
the append loader, `close`, and replay all detect a trailing unresolved INTENT
and fail closed with that reason. What v0.2 does NOT do is automatically
reconcile the orphan directory or write a recovery RESULT — recovery is left to
the operator (the state is explicit and detectable). Proven in
`tests/test_two_stage.py::test_result_persistence_failure_leaves_incomplete_run`.

## L2 — Replay reconstructs context from recorded decisions
Replay's tamper-evidence step recomputes the **saved** receipt hashes and
verifies the seal without trusting stored decisions — that part is strong.

The re-derivation step is weaker by necessity. Real `mkdir` side effects and the
original machine's pre-existing directories cannot be reconstructed from the
manifest. To reproduce decisions that depended on external structure, replay
creates minimal context in its sandbox **based on each recorded decision** (for
example, it makes a parent directory exist when the saved decision implies it
existed). This means the re-derivation step *trusts the recorded decisions to
set up context*. It is therefore a reproducibility check ("these decisions are
consistent and re-derivable"), not an independent re-execution of original
state. The independent integrity guarantee is the hash/seal verification, not
the re-derivation.

## L3 — Re-derivation compares a projection, not raw hashes
Because replay runs against a different absolute `allowed_root` (a temp
sandbox), recomputed receipt hashes differ from the saved ones by design. The
re-derivation step compares the `(decision, reason_code, executed)` projection
per receipt. Exact hash-identity replay is not achievable for a real-filesystem
action and is not claimed.

## L4 — Unkeyed hashes: tamper-evident, not tamper-proof
All hashes are plain SHA-256 with no key or signature. Editing an existing run
is detectable, but a local actor who can run this code can fabricate a brand-new
run that is internally valid and passes replay. There is no identity,
non-repudiation, or external anchoring. Adding those (signing, a timestamp
authority, an append-only log) is future work, not present capability.

## L5 — TOCTOU window
Policy evaluation and execution are distinct steps with no filesystem lock held
between them. `os.mkdir` provides a final fail-closed guard (it errors if the
target appeared in the interim), but a privileged concurrent actor reshaping the
tree during evaluation is out of scope.

## L6 — Symlink handling is conservative
Containment is computed against realpath-resolved parents. A symlink whose
resolved parent escapes the root is blocked as `BLOCK_SYMLINK_RISK`; a symlink
sitting at the exact target name is treated as "already exists" and blocked. If
`allowed_root` itself is a symlink, containment is computed against its real
target. These are intentionally cautious and may block some benign symlink
layouts.

## L7 — Single-level creation only
`CREATE_DIRECTORY` creates exactly one level (`os.mkdir`). It does not create
missing intermediate parents (`mkdir -p` behaviour). A missing parent is a
block, not an auto-create. This is a deliberate safety choice.

## L8 — Scope
v0.2.2 supports only `CREATE_DIRECTORY`. No delete, move, overwrite, copy,
network, email, browser, or app-control actions. No GUI, no Android, no
integration with Aletheia, ODIN, Histor, Companion, or any coordinator. Those
are explicitly out of scope.

## L9 — Older run files are not replayable or appendable (intentional)
The version vector requires an exact match. v0.1.1 changed the request schema
(1.0.0 → 1.1.0, removing `allowed_root`); v0.1.2 bumped `impl_version` for the
load-time integrity repair; v0.1.3 bumped `impl_version` and
`receipt_schema_version` for the closure-grammar repair. v0.1.4 was a release-harness-only repair. v0.2.0 changed the core (two-stage
INTENT/RESULT) and advanced `impl_version` and `receipt_schema_version`: v0.1.x
run files are `REPLAY_INCOMPATIBLE` and refused for append (exact-version
rejection, no migration). v0.2.1 (CLI tests in-process) and v0.2.2
(replay-verdict honesty) are non-core repairs; the deterministic protocol is
byte-for-byte the v0.2.0 protocol, so the version vector is UNCHANGED and v0.2.0
run files remain replayable under v0.2.1 and v0.2.2. Run files produced by earlier versions are refused
as `REPLAY_INCOMPATIBLE` (and equally refused for append) rather than
re-interpreted under newer rules. This is a deliberate hard break, consistent
with the documented exact-vector policy: silently accepting old runs would
reintroduce the semantics each release repaired.

## L10 — Execution-error outcomes are not reproducible by replay
A RESULT recording `ERROR_EXECUTION_FAILED` or `ERROR_POSTCONDITION_FAILED`
captures an environmental failure (a race, `EACCES`, a postcondition that did not
hold). Replay runs in a clean sandbox and will usually NOT reproduce that
failure — the fresh kernel succeeds. Replay therefore verifies such a receipt
**structurally** (it must be a RESULT resolving the correct INTENT, and its
self-hash and pairing must check out) but does not require the non-reproducible
outcome to recur; the replay report marks these `MATCH*`. Tamper-evidence for
these receipts comes from the per-receipt hash and the INTENT/RESULT pairing, not
from re-derivation — consistent with the documented split between tamper-evidence
(hashes) and reproducibility (projection).