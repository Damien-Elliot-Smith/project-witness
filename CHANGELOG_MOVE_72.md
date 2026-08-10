# Changelog - Move 72 (CANDIDATE, rebuilt)

Move: 72
Name: Rust workspace setup + Part Two state-model update
Date: 2026-07-09
Status: CANDIDATE pending owner review and adoption. ADOPTION IS BLOCKED
until a real cargo build + cargo test PASS transcript exists (see below).
Base: adopted Move 71 freeze v2
(zip sha256 d20234ca59d3e25f899f24f9704b7b2c7e72494f1468d539cff9b32f45d79197).
Supersedes the first Move 72 candidate, rejected by external review for a
current-state/status regression (stale "Part Two has not started" claims
plus a checker enforcing them - a false-green checker).

## Added (Rust, unchanged from first candidate, externally reviewed narrow)

- rust/ workspace, outside src/, zero external crates, fail-closed
  skeleton binary (exit 2), two unit tests, boundary README naming the
  adopted Move 71 freeze as the behavioural reference.
- tools/check_rust_workspace.sh: PASS / FAIL /
  INCONCLUSIVE_TOOLCHAIN_UNAVAILABLE (exit 0/1/3). INCONCLUSIVE is not
  green. Negative-tested (dependency injection -> FAIL).

## Changed (state model, new in this rebuild)

- CURRENT_RELEASE_STATE.md updated to the post-adoption reality:
  Roadmap One complete; Move 70.6 adopted; RT-004 adopted; Move 71
  Python behaviour freeze adopted; Part Two has started; Move 72 is a
  Rust workspace skeleton candidate, not a verifier; Rust workspace
  exists, but no Rust verification capability exists yet; no production
  Rust verifier is claimed; Steps 73-130 not started.
- Status exact marker updated in all 19 current-status docs. Historical
  records (MOVE_70_5_COMPLETION_REPORT.md, CHANGELOG_RT_004_REPAIR.md,
  freeze records) preserved unedited.
- tools/check_current_release_state.sh rules updated and negative-tested
  in all four directions: fails on stale Part-Two-not-started claims, on
  stale Move-71-not-started claims, on no-Rust-work claims while rust/
  exists, and on missing skeleton-only/no-capability statements; also
  requires the three adoption lines and forbids working-Rust-verifier
  claims; still forbids Rust artifacts inside src/ and verify/.

## Honest build status (unchanged)

The builder sandbox has no Rust toolchain and no network. cargo build and
cargo test have NOT been executed anywhere. Required before adoption:
on a machine with cargo (Termux: pkg install rust),
sh tools/check_rust_workspace.sh must print RUST_WORKSPACE_CHECK: PASS
with exit 0, showing cargo build and cargo test.

## Not changed

Python src/ untouched (source-match checker passes). No Step 73 content.
No runtime behaviour change. Move 71 freeze record untouched.
