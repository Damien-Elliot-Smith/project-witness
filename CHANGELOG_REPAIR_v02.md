# Changelog — Repair v02 (handoff hardening)

Date: 2026-06-29
Scope: cleanup and reviewer-readiness only. No new features. No architecture or
schema changes. No component behaviour changes. No roadmap advancement.

## Fixed

- **`tools/run_all_tests.sh` rewritten for reliability.**
  - Pass/fail is now decided by the Python `unittest` **exit code**, not by
    grepping output text.
  - Removed the `tail -3` dependency that could hide the `Ran N tests` / `OK`
    line when a component prints extra output after the test summary.
  - Removed `set -e`; a non-zero result from one component (or a failed count
    parse) no longer aborts the whole wrapper early.
  - Test counts are best-effort: a missing/unparseable `Ran N` line no longer
    crashes the script (the total is reported as partial instead).
  - Clean final summary: components checked / passed / failed, total tests
    detected, and a final `RESULT: PASS|FAIL` line.
  - Exits `0` only when every component suite passes; non-zero otherwise. On
    failure the failing component's full output is printed, not suppressed.

## Added

- `REVIEWER_QUICKSTART.md` — one-page reviewer guide (what it is / is not,
  checksum verification, safe extraction, commands, expected PASS markers).
- `HANDOFF_NOTES.md` — scope, archive relationship, component-local doc meaning,
  roadmap status, honesty boundary.
- `LICENSE_DECISION_NEEDED.md` — explains that public release needs a licence
  decision; outlines MIT vs Apache 2.0 without inventing legal certainty. No
  `LICENSE` file was added because permissive-release intent is unconfirmed.
- `tools/run_independent_verify.sh` — wraps the Move 45/46 independent verifier.
- `tools/run_local_v1_verify.sh` — wraps the Move 50 Local v1 Candidate verifier.
- `tools/run_termux_verify.sh` — wraps the Move 51 Termux instructions verifier.
- `tools/run_demo.sh` — stable alias for the live end-to-end demo.
- `tools/validate_handoff.sh` — top-level validator; runs all of the above and
  the live demo, prints a summary, and **fails closed** (non-zero) if any stage
  fails. Failure output is not hidden.

## Updated

- `START_HERE.md` — first command is now the reliable `validate_handoff.sh`;
  points reviewers to `REVIEWER_QUICKSTART.md`; claims unchanged and still honest.
- `STACK_STATUS.md` — added a v02 note; results re-confirmed after the repair.

## Unchanged (intentionally)

- All component code, schemas, and behaviour.
- The frozen verification artifacts (independent verifier, Move 45 freeze, Move 50
  candidate, Move 51 termux) — byte-for-byte identical.
- Roadmap status: complete through Move 51; Moves 52–70 remain future work. This
  is a Local v1 Candidate, not a final Local v1 Release.

## Re-verification after repair

All commands below were run from a fresh extraction of the v02 zip and passed:

```
sh tools/run_all_tests.sh           -> RESULT: PASS — ALL_COMPONENT_TESTS_PASSED (18/18, 1234 tests)
sh tools/run_independent_verify.sh  -> PROJECT_WITNESS_INDEPENDENT_VERIFICATION_PASSED / verify_ok = true
sh tools/run_local_v1_verify.sh     -> LOCAL_V1_CANDIDATE_VERIFIED / verify_ok = true
sh tools/run_termux_verify.sh       -> TERMUX_RUN_INSTRUCTIONS_VERIFIED / verify_ok = true
sh tools/run_demo.sh                -> COMPANION_COMPLETED / verify_ok: true
sh tools/validate_handoff.sh        -> HANDOFF_VALIDATION: PASS
```

The wrapper's fail-closed behaviour was also tested against a deliberately broken
component: it reported the failure, printed the full failure output, and exited
non-zero.
