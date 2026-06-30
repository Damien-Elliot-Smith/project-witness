# Threat model

This document states plainly what Sentinel Core v0.2.2 defends against and what it
does not. The goal is honesty, not reassurance.

## Assets

- The **run file**: the manifest, the receipt chain, and the run seal.
- The **filesystem under `allowed_root`**: directories Sentinel may create.

## What Sentinel defends against

### T1 — Path escape from allowed_root
`..` traversal, absolute targets pointing outside the root, and symlink-based
escape are each detected and blocked with a specific reason code. Containment is
computed against realpath-resolved paths, so a symlink in the parent chain that
points outside the root fails closed.

The root itself is **run-configured and authoritative** (v0.1.1): it is fixed
in the manifest, the kernel passes it into path policy for every request, and a
request cannot name a root of its own — that field no longer exists in the
schema, and supplying it is schema-invalid. This closes the v0.1.0 flaw where a
request could self-declare a different root and act there.

### T2 — Overwrite / clobber
Sentinel never overwrites. An existing target (file, directory, or symlink)
blocks the request. `os.mkdir` gives a final guard against a check-to-execute
race.

### T3 — Shell / command injection
There is no shell anywhere. Targets with metacharacters become literal directory
names. There is no code path that builds or runs a shell command.

### T4 — In-file tampering of a saved run (tamper-evidence)
Mutating a receipt's `target_path`, `allowed_root`, `decision`, or any other
hashed field breaks that receipt's recomputed hash and is rejected on load.
Deleting or reordering receipts breaks chain linkage. Deleting the final
receipt or editing the seal is rejected by seal validation in closed/audit
replay. All of this is detected **without** trusting the stored decisions,
because the hashes are recomputed.

Since v0.1.2 this verification is enforced at **load time for append**, not
just at replay. A closed run whose seal was deleted, or an open run whose chain
was broken (deleted/duplicated/tampered receipts), is refused before any kernel
is constructed — so the tamper is caught *before* a filesystem side effect can
occur, not merely detected afterwards by replay.

Since v0.1.3 the **session-closure grammar** is enforced semantically, not just
by hash. Marking a normal CREATE/BLOCK/DRY_RUN/ERROR receipt as
`CLOSED_BY_OPERATOR`, recomputing its hash, and building a fresh valid seal
(all of which an in-file editor can do) no longer produces an accepted run:
only a real `ALLOW_SESSION_CLOSE` receipt may declare closure, checked at
construction, chain verification, seal validation, and replay. This narrows the
forgery surface within a file further — though N2 still stands: a local actor
can fabricate a wholly new run that obeys the grammar.

### T5 — Hostile run files at replay
A malformed, mis-encoded, or maliciously deep JSON file does not crash replay;
it fails closed with a controlled error.

### T6 — Crash between execution and record
Persistence is atomic (temp file → fsync → `os.replace` → best-effort directory
fsync). A crash leaves either the old run file or the fully written new one,
never a half-written file. Under the v0.2 two-stage model a crash is further
constrained: before mkdir there is at most a committed INTENT (no side effect);
after mkdir but before the RESULT is written the run is left in an explicit
`RESULT_MISSING_AFTER_INTENT` state that append, close, and replay all detect and
refuse, rather than silently accepting an action whose outcome was never
recorded.

## What Sentinel does NOT defend against

### N1 — Identity
Sentinel does not authenticate anyone. It records *what* was requested and
decided, not *who* requested it.

### N2 — A local actor forging a fresh, internally-valid run
The receipt and seal hashes are **unkeyed** SHA-256. Anyone who can run this
code can construct a brand-new run that is internally consistent and passes
replay. Tamper-evidence catches edits to an *existing* run; it cannot prove a
run was produced by a particular party at a particular time. Closing that gap
requires cryptographic signing and/or external anchoring (e.g. a timestamp
authority or append-only log), which is deliberately **out of scope** for v0.2.2.

### N3 — The operating system and Python runtime
Sentinel trusts the OS, filesystem, and interpreter. It does not defend against
a compromised kernel, a malicious `os`/`pathlib`, or a hostile filesystem
driver.

### N4 — TOCTOU beyond the single mkdir guard
Policy evaluation and execution are separate steps. Sentinel re-guards with
`os.mkdir` (which fails if the target appeared in between), but it does not hold
filesystem locks. A sufficiently privileged concurrent actor manipulating the
tree during evaluation is not in scope.

### N5 — Pre-existing external structure during replay
Replay reconstructs only what the recorded decisions imply (see RUN_FORMAT and
KNOWN_LIMITATIONS). It is a reproducibility check of decisions, not a perfect
re-execution of the original machine state.

## Trust boundary summary

Sentinel is a deterministic *gate and recorder*. Within a single run file it
gives strong tamper-evidence and faithful decision re-derivation. It does not,
on its own, provide authenticity, non-repudiation, or protection against a local
actor who rewrites the whole file. Treat its output as an honest internal audit
trail, not as cryptographic proof of who did what.
