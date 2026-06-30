# Test results — Sentinel Core v0.2.2

> Note: this build additionally applies a **documentation / version-string
> cleanup** (ledger R16) — stale "v0.1" identity/scope strings, the README
> layout directory name, and the `release_check.py` checksum hint were corrected
> to v0.2.2. No code, protocol, or test changes; the test count (144) and
> selfcheck (15/15) are unchanged. Historical version references (when a feature
> or repair was introduced) were deliberately preserved.

v0.2.2 is a narrow **replay-honesty / reporting** repair of v0.2.1. The
INTENT/RESULT protocol is unchanged; the deterministic core is byte-for-byte the
v0.2.0 core. No new actions, no signing, no GUI, no integrations. All commands
below were run from a **clean extraction** of `sentinel_core_v022.zip`.
Environment: Python 3 standard library only.

## The issue and its fix

**Issue 1 — environmental ERROR replay reported too strongly.** Taking a clean
successful run, mutating its success RESULT into `ERROR_EXECUTION_FAILED`,
recomputing the receipt hash, the next `prior_hash`, the close-receipt hash, and
the run seal, then replaying — returned plain **PASS** and marked the forged
receipt `MATCH*`. The structural acceptance is expected (unkeyed hashes, L4; and
environmental errors are non-reproducible, L10), but the verdict was too strong:
a run leaning on a `MATCH*` exception read identically to a strictly re-derived
run.

**Fix.** Replay now reports one of four verdicts:

- `PASS_STRICT` — every receipt strictly re-derived.
- `PASS_WITH_ENVIRONMENTAL_EXCEPTIONS` — accepted, but one or more environmental
  ERROR receipts (`ERROR_EXECUTION_FAILED` / `ERROR_POSTCONDITION_FAILED`) were
  structurally verified, NOT strictly reproduced (`MATCH*`).
- `FAIL` — re-derivation diverged or a structural/hash/seal/completeness check
  failed.
- `REPLAY_INCOMPATIBLE` — version-vector mismatch.

Both PASS verdicts exit 0, but the report text distinguishes them; any use of a
`MATCH*` exception forces `PASS_WITH_ENVIRONMENTAL_EXCEPTIONS`. The programmatic
API returns a `ReplayResult` (`.ok`, `.verdict`, `.report`) that still unpacks as
the historical `(ok, report)` tuple, so existing callers are unaffected.

**Issue 2 — stale comment.** The top-of-file comment in
`sentinel_core/kernel.py` still described the old single-receipt design; it now
describes the two-stage INTENT/RESULT flow.

## Acceptance — all pass from a clean extraction

| Command | Result |
|---------|--------|
| `python3 -m compileall -q .` | PASS |
| `python3 -m unittest discover -s tests -v` | PASS — 144 tests |
| `python3 -O -m unittest discover -s tests -v` | PASS — 144 tests |
| `python3 selfcheck.py` | PASS — 15/15 gates |
| `python3 -O selfcheck.py` | PASS — 15/15 gates |
| `python3 -W error::ResourceWarning -m unittest discover -s tests` | PASS |
| `python3 release_check.py` | PASS — 7/7 steps |
| `sha256sum -c sentinel_core_v022.sha256` | OK |

## The reported attack, before and after

Clean run → `REPLAY VERDICT: PASS_STRICT` (exit 0).
Forged-ERROR run (success RESULT mutated to `ERROR_EXECUTION_FAILED`, all hashes
and the seal recomputed) → `REPLAY VERDICT: PASS_WITH_ENVIRONMENTAL_EXCEPTIONS`
(exit 0). The forged receipt is still structurally accepted under L4, but the
verdict no longer claims strict re-derivation.

## New tests (144 total, was 138)

### tests/test_two_stage.py (+6)
- `test_clean_run_is_pass_strict` — clean run → PASS_STRICT, no `MATCH*`.
- `test_genuine_execution_error_run_is_pass_with_env_exceptions` — a real
  injected mkdir failure → PASS_WITH_ENVIRONMENTAL_EXCEPTIONS, accepted (exit 0).
- `test_genuine_postcondition_error_run_is_pass_with_env_exceptions`.
- `test_forged_error_run_reports_env_exceptions_not_strict` — the reported
  attack (recomputed hashes + seal) → PASS_WITH_ENVIRONMENTAL_EXCEPTIONS, asserts
  it is NOT PASS_STRICT.
- `test_incompatible_version_is_replay_incompatible_verdict`.
- `test_structural_failure_is_fail_verdict`.

### Selfcheck (+1 gate, now 15)
- `replay_verdict_categories` — asserts a clean run is PASS_STRICT and an
  environmental-ERROR run is PASS_WITH_ENVIRONMENTAL_EXCEPTIONS (and still ok).

### Versioning
- `PACKAGE_VERSION` → 0.2.2; `IMPL_VERSION` stays 0.2.0 (protocol unchanged), so
  the manifest version vector and v0.2.0 run-file replay compatibility are
  preserved.

## Preserved guarantees (all still tested)

Two-stage INTENT/RESULT receipts and RESULT_MISSING_AFTER_INTENT detection;
CREATE_DIRECTORY only; manifest-authoritative `allowed_root`; append-time
integrity loader; session-closure grammar; run sealing; hostile-JSON handling;
no bare runtime asserts; standard library only; `release_check.py` with
independent timed subprocess gates; `selfcheck.py` does not launch the unit
suite; the unit suite spawns no subprocesses.

## Honest edges (unchanged in substance)

L1a (RESULT_MISSING_AFTER_INTENT detected/refused, orphan not auto-reconciled);
L10 (execution-error outcomes structurally verified, not strictly reproduced —
now reflected in the PASS_WITH_ENVIRONMENTAL_EXCEPTIONS verdict); L4 (unkeyed
hashes — a forged ERROR is indistinguishable from a genuine one; detecting it
needs signing or external anchoring, out of scope).
