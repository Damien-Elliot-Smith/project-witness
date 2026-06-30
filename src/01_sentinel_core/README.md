# Sentinel Core v0.2.2

A deterministic action-gating prototype for exactly one real filesystem action:
**`CREATE_DIRECTORY`**.

Sentinel takes a structured action request, decides `ALLOW` / `BLOCK` /
`DRY_RUN` / `ERROR` using pure, read-only path logic, performs the directory
creation (when allowed) with no shell, records a hash-chained receipt for every
request, seals the run when it closes, and can actively re-derive the whole run
through a fresh kernel.

**The boundary is run-configured, not caller-selected.** The `allowed_root` is
fixed once in the run manifest when the run is created; every request is judged
against that root and that root only. Requests carry no `allowed_root` field
(removed in request schema v1.1.0 — a request that still includes one is
rejected as schema-invalid). This was the v0.1.1 repair: in v0.1.0 a request
could self-declare a different root and act there.

**Appending requires a valid, genuinely open run.** Opening an existing run for
append (v0.1.2) verifies the manifest, every receipt hash, and the full chain
structure, and refuses any run containing a close receipt — even if the
`run_seal` was deleted — before a kernel exists. Tampered or closed runs cannot
receive new actions; the refusal happens before any filesystem side effect.

**Only a real close receipt can close a run.** The session may transition
`OPEN -> CLOSED_BY_OPERATOR` only via an `ALLOW_SESSION_CLOSE` receipt
(v0.1.3). A normal CREATE/BLOCK/DRY_RUN/ERROR receipt forged to a closed state
— even with a recomputed hash and a freshly built seal — is rejected at receipt
construction, chain verification, seal validation, and replay.

**Two-stage INTENT/RESULT receipts (v0.2).** Every approved `CREATE_DIRECTORY`
records an **INTENT** receipt — persisted and committed *before* any `mkdir` —
then executes, then records a **RESULT** receipt that references the INTENT.
This fixes the v0.1.x "mkdir-before-persist" limitation: the intent is durable
before the side effect. If the RESULT is never persisted (e.g. a crash between
mkdir and the RESULT write), the run is left in an explicit
`RESULT_MISSING_AFTER_INTENT` state that append, close, and replay all detect
and refuse — it is never silently treated as complete. `BLOCK` and `DRY_RUN`
never execute, so they remain single self-contained RESULT receipts.

**Replay verdicts are honest about reproduction (v0.2.2).** Replay reports one of
four verdicts: `PASS_STRICT` (every receipt was strictly re-derived),
`PASS_WITH_ENVIRONMENTAL_EXCEPTIONS` (accepted, but one or more environmental
ERROR receipts — `ERROR_EXECUTION_FAILED` / `ERROR_POSTCONDITION_FAILED` — were
**structurally verified, not strictly reproduced**), `FAIL` (re-derivation
diverged), and `REPLAY_INCOMPATIBLE` (version-vector mismatch). Both PASS
verdicts exit 0, but the text distinguishes them: a run that leans on an
environmental ERROR never reports the same verdict as a strictly re-derived run.
This matters because, under unkeyed hashes (see KNOWN_LIMITATIONS L4), a forged
ERROR receipt is indistinguishable from a genuine one — so replay refuses to
overclaim and surfaces the exception in the verdict rather than hiding it inside
a plain PASS.

It is inspired by the **Embodied Witness Phase 1A v0.5.2** architecture
(receipts → manifest hash → run seal → active replay), but it is a **separate
project** that touches the real filesystem rather than a simulated world.

## What this is — and is not

Sentinel v0.2.2:

- Supports **only** `CREATE_DIRECTORY`. Nothing else.
- Is a **prototype**, not production security software.
- Does **not** prove user identity.
- Does **not** stop a local actor who can rewrite the whole run file from
  producing a *different* internally-valid run. The run seal is an unkeyed
  SHA-256 digest: tamper-**evident** within a file, not tamper-**proof**.
  Preventing that needs signing or external anchoring, which is out of scope
  for v0.2.2.
- Does **not** use shell execution anywhere.
- Does **not** accept natural language in the deterministic core. Requests are
  structured JSON-like objects only.
- Is intentionally narrow: no delete, move, overwrite, network, email, browser,
  or app-control actions; no GUI; no Android; no integration with Aletheia,
  ODIN, Histor, Companion, or any coordinator.

## Layout

```
sentinel_core_v022/
  README.md            this file
  selfcheck.py         fixed battery of gates; exits non-zero on any failure
  sentinel.py          operator CLI (create / close / replay / inspect)
  REPAIR_LEDGER.md     issues found and fixed during the build
  sentinel_core/       the deterministic core package
  tests/               unit tests (also runnable under python -O)
  docs/                invariants, threat model, run format, commands, limits
```

## Quick start

```bash
# Create a directory under an allowed root, recording a run file.
python3 sentinel.py create --run run.json --run-id demo \
    --request-id REQ-001 --target-path demo/output --allowed-root ./workspace

# Close (seal) the run.
python3 sentinel.py close --run run.json

# Re-derive the whole run through a fresh kernel.
python3 sentinel.py replay --run run.json

# Summarise a run file.
python3 sentinel.py inspect --run run.json
```

## Self-check

```bash
python3 selfcheck.py        # all gates
python3 -O selfcheck.py     # same, with assertions stripped (must still pass)
```

See `docs/COMMANDS.md` for the full command reference, `docs/INVARIANTS.md` for
the properties the core is built to hold, `docs/THREAT_MODEL.md` for what is and
is not defended, and `docs/KNOWN_LIMITATIONS.md` for the honest edges.
