# Run format

A run file is a single JSON object with three top-level keys: `manifest`,
`receipts`, and `run_seal`.

```json
{
  "manifest": { ... },
  "receipts": [ ... ],
  "run_seal": null
}
```

## manifest

Pins the version vector and the run's identity. Its `manifest_hash` is a
SHA-256 over the canonical JSON of every manifest field except `manifest_hash`
itself.

```json
{
  "impl_version": "0.2.0",
  "receipt_schema_version": "0.2.0",
  "action_schema_version": "1.1.0",
  "policy_version": "0.1.1",
  "reason_registry_version": "0.1.0",
  "session_version": "0.1.0",
  "manifest_version": "0.1.0",
  "run_id": "demo",
  "allowed_root": "/abs/path/to/workspace",
  "initial_session_state": "OPEN",
  "manifest_hash": "<64-hex>"
}
```

The manifest's `allowed_root` is the **authoritative boundary for the whole
run**: every request is judged against it, and requests carry no root of their
own. Any change to a bound field without recomputing `manifest_hash` is
rejected at load. Replay also requires the version vector to match the current
implementation exactly; otherwise it returns `REPLAY_INCOMPATIBLE` rather than
guessing.

## receipts

An ordered array. Each receipt records one decision and is individually hashed.

```json
{
  "receipt_id": 0,
  "prior_hash": "GENESIS",
  "run_id": "demo",
  "manifest_hash": "<64-hex>",
  "receipt_schema_version": "0.2.0",
  "impl_version": "0.1.0",
  "action_schema_version": "1.0.0",
  "policy_version": "0.1.0",
  "reason_registry_version": "0.1.0",
  "session_version": "0.1.0",
  "pre_session_state": "OPEN",
  "post_session_state": "OPEN",
  "stage": "RESULT",
  "intent_receipt_id": 0,
  "intent_hash": "<64-hex of the INTENT this RESULT resolves, or null>",
  "request": { ...the normalised action request... },
  "decision": "ALLOW",
  "reason_code": "ALLOW_CREATE_DIRECTORY",
  "detail": { ...diagnostic fields, e.g. resolved paths... },
  "executed": true,
  "canonical_hash": "<64-hex>"
}
```

- `prior_hash` is `"GENESIS"` for receipt 0, otherwise the previous receipt's
  `canonical_hash`. This forms the chain.
- `canonical_hash` is a SHA-256 over the canonical JSON of every field except
  `canonical_hash`. It is recomputed on load; a mismatch means tampering.
- `executed` is `true` only for an `ALLOW` that actually created the directory.
- The final receipt of a closed run is an `ALLOW_SESSION_CLOSE` receipt with
  `post_session_state` = `CLOSED_BY_OPERATOR` and `executed` = `false`.

**Closure grammar (v0.1.3).** Only an `ALLOW_SESSION_CLOSE` receipt may carry
`post_session_state = CLOSED_BY_OPERATOR`, and it must have exactly
`decision=ALLOW`, `reason_code=ALLOW_SESSION_CLOSE`,
`request={"action_type": "CLOSE_SESSION"}`, `executed=false`,
`pre_session_state=OPEN`. Every other receipt (CREATE/BLOCK/DRY_RUN/ERROR) must
be `OPEN -> OPEN`. This is validated at receipt construction, chain
verification, seal build/validation, and replay, so a non-close receipt forged
to a closed state — even rehashed and resealed — is rejected.

### The action request

The `request` stored in a CREATE_DIRECTORY receipt is the normalised form:

```json
{
  "request_id": "REQ-001",
  "action_type": "CREATE_DIRECTORY",
  "target_path": "demo/output",
  "dry_run": false,
  "preconditions": ["inside_allowed_root", "parent_exists", "target_absent"],
  "postconditions": ["target_exists", "target_is_directory"],
  "schema_version": "1.1.0"
}
```

There is **no `allowed_root` field** in a request (removed in v1.1.0). The
boundary is the manifest's `allowed_root`; a request including the field is
rejected as schema-invalid.

(`preconditions` / `postconditions` are stored sorted for a canonical hash.)

## run_seal

`null` while the run is open. On close it becomes:

```json
{
  "seal_version": "0.1.0",
  "run_id": "demo",
  "manifest_hash": "<64-hex>",
  "receipt_count": 4,
  "final_receipt_id": 3,
  "final_receipt_hash": "<64-hex>",
  "final_session_state": "CLOSED_BY_OPERATOR",
  "seal_hash": "<64-hex>"
}
```

`seal_hash` is a SHA-256 over the seal's other fields. Because it binds the
receipt count and the final receipt hash, deleting the final receipt (a clean
suffix truncation) makes the seal inconsistent and closed/audit replay rejects
the file.

## Receipt stages (v0.2)

Every receipt has a `stage`:

- `INTENT` — the action was approved for execution but has NOT yet executed.
  `executed` is `false`; `intent_receipt_id`/`intent_hash` are `null`. Persisted
  and committed before any `mkdir`.
- `RESULT` — the outcome was recorded. A RESULT that resolves an INTENT sets
  `intent_receipt_id` to that INTENT's id (always `receipt_id - 1`) and
  `intent_hash` to its `canonical_hash`. `BLOCK` and `DRY_RUN` are self-contained
  RESULT receipts with `intent_receipt_id = null` (nothing was ever approved for
  execution).
- `SESSION_CLOSE` — the terminal close receipt.

A successful create is therefore the pair INTENT(N) then RESULT(N+1). A run whose
final receipt is an unresolved INTENT (no following RESULT) is **incomplete**
(`RESULT_MISSING_AFTER_INTENT`) and is refused by append, close, and replay.

The pairing invariants enforced on load and replay: every resolving RESULT
immediately follows its INTENT and hash-matches it; no RESULT references a
non-INTENT; no INTENT is resolved by two RESULTs; receipt ids stay contiguous;
and a session cannot close while any INTENT is unresolved.

## Replay and the sandbox (important)

Replay re-derives decisions against a **fresh temporary directory**, not the
original `allowed_root`. A successful `CREATE_DIRECTORY` is not idempotent, and
the original absolute root plus any pre-existing external directories are not
reconstructable from the manifest. Consequently:

- Re-executed receipt **hashes legitimately differ** from the saved ones
  (different absolute root), so replay compares the
  `(decision, reason_code, executed)` projection, not raw hashes, for the
  re-derivation step.
- Tamper-evidence (the strong guarantee) comes from recomputing the **saved**
  receipt hashes and verifying the seal, which happens before any re-execution.
- To reproduce decisions that depended on directories existing on the original
  machine, replay reconstructs minimal context from each recorded decision
  (e.g. it creates a parent directory in the sandbox when the saved decision
  implies the parent existed). See KNOWN_LIMITATIONS L2 for the precise
  contract and its trust caveat.

## Replay verdict (v0.2.2)

Replay reports one of four verdicts on its final two lines
(`REPLAY VERDICT: <verdict>` followed by a one-line summary):

- `PASS_STRICT` — every receipt was strictly re-derived; no exceptions.
- `PASS_WITH_ENVIRONMENTAL_EXCEPTIONS` — the run is accepted, but one or more
  environmental ERROR receipts (`ERROR_EXECUTION_FAILED` /
  `ERROR_POSTCONDITION_FAILED`) were **structurally verified, not strictly
  reproduced** (shown as `MATCH*` lines). Replay in a clean sandbox cannot
  reproduce an environmental failure, so it verifies the receipt's structure and
  INTENT/RESULT pairing instead. See KNOWN_LIMITATIONS L10 (and L4 on why a
  forged ERROR is indistinguishable from a genuine one under unkeyed hashes).
- `FAIL` — re-derivation diverged, a structural/hash/seal check failed, the run
  was incomplete (`RESULT_MISSING_AFTER_INTENT`), or the chain was broken.
- `REPLAY_INCOMPATIBLE` — the run's version vector does not match this build
  (exact-version policy; no migration).

The process exit code is 0 for both PASS verdicts (the run is accepted) and
non-zero for `FAIL` and `REPLAY_INCOMPATIBLE`. The two PASS verdicts are reported
distinctly on purpose: a run that leans on an environmental exception must never
read as a strictly re-derived run.

The programmatic API returns a `ReplayResult` with `.ok` (bool), `.verdict` (one
of the four strings above), and `.report` (the full text). It still unpacks as
the historical `(ok, report)` tuple for backward compatibility.
