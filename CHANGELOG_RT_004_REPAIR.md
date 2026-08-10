# Changelog - RT-004 Repair Candidate

Name: Companion verification-depth repair (RT-004 / RB-EXT-002)
Date: 2026-07-03
Status: CANDIDATE pending owner review and adoption.
Base: Move 70.6 reconciliation candidate (itself a candidate).

## Evidence trail

- rt_004_repair/before_repair_verdicts.json: the UNREPAIRED base accepted
  all four tamper classes (bytes changed, file deleted, file added
  unexpectedly, checksum/manifest fix-up) with verify_ok=true.
- rt_004_repair/after_repair_verdicts.json: the REPAIRED stack rejects all
  four with distinct reasons; the clean control still passes.

## Changed

- src/12_companion_cli_v031: new companion_lib/deep_checksums.py (nested
  checksum recursion, Aletheia manifest binding, Sentinel source-run
  binding, evidence-directory completeness), verifier hook, 28 new tests
  (companion suite 79 -> 107), KNOWN_LIMITATIONS updated honestly.
- RELEASE_BLOCKER_REGISTER.md: RB-EXT-001 / RB-EXT-002 recorded as
  REPAIR CANDIDATE, not silently marked repaired.
- CURRENT_RELEASE_STATE.md: added "Current source release package"
  declaration (v21 RT-004 candidate source zip under releases/), forced by
  tools/check_src_matches_release.sh, which would otherwise correctly fail
  once src/ diverges from the historical v20 package. The Roadmap One
  final-package declaration is unchanged and historical.

## Not changed

No output schema change (0.3.0). No new action surface. No Move 71 freeze.
No Rust. Part Two has not started. Whole-folder fabrication remains
possible without signing (unchanged, documented).
