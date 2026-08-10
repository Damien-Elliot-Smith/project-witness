# Changelog - Move 70.6 (Reconciliation Candidate)

Move: 70.6
Name: Live source reconciliation to the declared final release
Date: 2026-07-03
Status: CANDIDATE pending owner review and adoption.
Base: project-witness-main-move-70-5.zip
(sha256 72e38ffd8338a978bf5d59d2fc9f0f06847092eab5f6a828077adef709c0f348)

## Why

External review found the live top-level src/ had silently diverged from
the src/ inside the declared final Roadmap One package (18 file
differences: missing Move 62 test coverage, missing Move 63 evidence-type
module, missing atlas release-gate registry, nine Sentinel core files with
differing content; 1234 vs 1273 tests). Every existing checker passed
because none compared the live tree to the declared package. Owner ruling:
the declared v20 release zip is the authoritative Roadmap One source line;
the live src/ divergence is a release-wrapper failure, not a new truth line.

## Changed

- src/ replaced wholesale with the src/ from the declared package
  releases/roadmap_one_complete/move_70_final/
  Project_Witness_WORKING_STACK_v20_MOVE_70.zip
  (sha256 1248bc46fa555cc50ed7b63c9284baffd1e95a6972cdfbc4a40a0201fea81aba),
  bytecode excluded per packaging rules. 625 files, verified 0 differences.

## Added

- tools/check_src_matches_release.sh: compares live src/ against the src/
  inside the release zip declared by CURRENT_RELEASE_STATE.md, by path and
  SHA-256; fails on missing, extra, or changed files. Negative-tested in
  all three failure directions.

## Not changed

No runtime behaviour beyond restoring src/ to the declared release source.
CURRENT_RELEASE_STATE.md untouched. No Move 71 content. No RT-004 repair
(that is a separate candidate). No Rust.
