# Release Blocker Register - Move 59 carried into Move 60

Roadmap: Step 59 = Repair Release Blockers. Step 60 = Freeze Local v1 Release.
Status: Roadmap One (Steps 1-70) complete as a local review/demo stack. Not production-ready. Part Two has started.

Move 59 repaired internal release blockers found before the Local v1 release
freeze. Move 60 freezes the release after those blocker checks pass.

## Important honesty boundary

No external reviewer feedback is recorded. Therefore there are no external
reviewer blockers claimed, no external reviewer approvals claimed, and no external
reviewer blocker repairs claimed.

Feedback state: `NO_EXTERNAL_FEEDBACK_RECORDED`.

## Accepted blockers repaired in Move 59

| ID | Type | Status | Repair summary |
|---|---|---|---|
| RB-59-001 | Documentation/status drift | REPAIRED | Current top-level docs were brought to a single roadmap status marker. |
| RB-59-002 | Mislabelled current roadmap status | REPAIRED | Move 57/58 numbering was corrected against the roadmap. |
| RB-59-003 | Stale package names in active reviewer instructions | REPAIRED | Active reviewer/demo instructions now point at the current package name. |
| RB-59-004 | Stack status stale bottom line | REPAIRED | `STACK_STATUS.md` bottom status was corrected. |
| RB-59-005 | Move index status duplication | REPAIRED | `MOVE_INDEX.md` status section was cleaned and now includes current moves. |
| RB-59-006 | Missing release-blocker checker | REPAIRED | `tools/check_release_blockers.sh` was added and must pass. |

## Move 60 release gate

Move 60 is accepted only if `tools/check_local_v1_release.sh`,
`tools/check_release_blockers.sh`, and the existing validation commands pass.

## Blockers found by external review (2026-07-03), repairs in candidate state

These repairs are packaged as candidates (Move 70.6 reconciliation and the
RT-004 repair candidate) and are not adopted until the owner verifies them.

| ID | Type | Status | Repair summary |
|---|---|---|---|
| RB-EXT-001 | Live src/ diverged from declared final release package (18 files; no checker compared them) | REPAIR CANDIDATE | Move 70.6: live `src/` reconciled to the declared v20 package; `tools/check_src_matches_release.sh` added (path + SHA-256, fails on missing/extra/changed; negative-tested in all three directions). |
| RB-EXT-002 | RT-004: `companion verify` accepted tampered runs — nested evidence bytes changed, deleted, added unexpectedly, or checksum/manifest fix-up all returned verify_ok=true (blind spot recorded in `rt_004_repair/before_repair_verdicts.json`) | REPAIR CANDIDATE | Companion v0.3.2 deep verification: nested checksum recursion, Aletheia manifest binding, Sentinel source-run binding, evidence-directory completeness; 28 new tests; all four tamper classes now rejected with distinct reasons (`rt_004_repair/after_repair_verdicts.json`). |

Status exact marker: Project Witness Roadmap One, Steps 1-70, is complete as a local review/demo stack. Post-completion repairs Move 70.6 and RT-004 are adopted. The Move 71 Python behaviour freeze is adopted. Rust Moves 72-78 are adopted, including ZipGuard archive safety. Part Two has started. Move 79 (verification-only Python/Rust agreement harness) is the current candidate; no full bundle verification capability exists or is claimed.
