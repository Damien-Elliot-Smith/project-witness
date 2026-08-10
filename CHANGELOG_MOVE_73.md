# Changelog - Move 73 (CANDIDATE)

Move: 73
Name: witness-verify CLI skeleton
Date: 2026-07-10
Status: CANDIDATE. ADOPTION BLOCKED until a real cargo build + cargo test
PASS transcript exists on a machine with a Rust toolchain
(sh tools/check_rust_workspace.sh must print PASS, exit 0). The builder
sandbox has no Rust toolchain: the Rust code in this candidate has NOT
been compiled. If cargo build or cargo test fails on your machine, paste
the error text back; the fix becomes part of this move's record.
Base: adopted Move 72 v2
(zip sha256 1de1bcab94598fe038982d14a2ac3d320dd5b82ef2877e7b3eaa4bfd224bf46e).

## Added

- witness-verify CLI (v0.0.2): usage `witness-verify verify <bundle-dir>`.
  Read-only; opens nothing, modifies nothing. Controlled single-line JSON
  output: verifier, version, verdict, reason_code, detail. Verdicts FAIL
  and INCONCLUSIVE only - NO CODE PATH CAN EMIT PASS, and exit 0 is
  unreachable (reserved for a real PASS in later steps). Exit codes:
  1 FAIL, 2 usage error, 3 INCONCLUSIVE, matching the checker convention.
  Reason codes in the frozen UPPER_SNAKE vocabulary style:
  USAGE_ERROR, BUNDLE_PATH_MISSING, BUNDLE_PATH_NOT_A_DIRECTORY,
  NO_CHECKS_IMPLEMENTED. Six unit tests, including the PASS-unreachable
  property test and JSON-escaping safety.
- rust/README.md: Step 73 output contract documented, plus the Termux
  storage note from the Move 72 adoption run (build from internal
  storage; Android blocks executing binaries from shared storage).

## Changed

- State model updated proactively in the same move (the drift class
  caught three times by external review is now handled at authoring
  time): CURRENT_RELEASE_STATE.md and all 19 live markers record Move 72
  adopted and Move 73 as candidate; Steps 74-130 not started;
  tools/check_current_release_state.sh required strings updated
  (Move 72 adoption recorded; Move 73 skeleton-only; CLI fails closed).
- tools/check_rust_workspace.sh fail-closed rule updated from the Move 72
  literal to the Move 73 contract (named exit constants, no-checks reason
  code, PASS-unreachable property test present); negative-tested.

## Not changed

Python src/ untouched. Move 71 freeze record untouched. No Step 74
content: no manifest reading, no hashing, no verification logic. The
CLI does not open any file inside the bundle.
