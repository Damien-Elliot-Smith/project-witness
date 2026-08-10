# Project Witness - Working Stack

A local, deterministic, standard-library-only integrity-verification stack.

Project Witness preserves and verifies structured provenance relationships between files, hashes, manifests, receipts, statuses, and declared workflow outputs under tested local conditions.

This repository is the runnable Project Witness working stack.

## Roadmap One status

Project Witness Roadmap One, Steps 1-70, is complete as a local review/demo stack. Part Two has started.

Single authoritative current-state document: CURRENT_RELEASE_STATE.md
Authoritative current-state checker: tools/check_current_release_state.sh

Final Roadmap One package:

releases/roadmap_one_complete/move_70_final/Project_Witness_WORKING_STACK_v20_MOVE_70.zip

SHA-256:

1248bc46fa555cc50ed7b63c9284baffd1e95a6972cdfbc4a40a0201fea81aba

Main completion documents:

- ROADMAP_ONE_COMPLETE.md
- ROADMAP_ONE_COMPLETION_MATRIX.md
- releases/roadmap_one_complete/move_70_final/VERIFICATION_TRANSCRIPT_MOVE_70.md
- releases/roadmap_one_complete/move_70_final/CHANGELOG_MOVE_70.md

## What it is

- Pure standard-library Python.
- No third-party packages.
- No network requirement for the checked local stack.
- No build step.
- A completed local review/demo stack for Roadmap One.
- A pipeline of small components including Sentinel, Histor-lite, Aletheia, ODIN, Atlas, Coordinator, Companion, verifiers, and self-checks.
- Reproducible through the included scripts and verification transcripts.
- Packaged with final Move 70 completion material.

## What it is not

- It does not prove external truth or that evidence is factually correct.
- It does not authenticate real-world identity or source trust.
- It is not production-ready.
- It does not claim external reviewer approval.
- Move 65 signing is test-only and not production-valid.
- Move 66 anchoring is local simulation only, not real external anchoring.
- Move 67 web UI is read-only and does not execute actions.
- Moves 68 and 69 are planning packs only.
- No Android app has been built.
- No Windows app has been built.
- It has no cloud operation claim.
- It has no autonomy claim.

## Read these first

1. ROADMAP_ONE_COMPLETE.md - final Roadmap One completion note.
2. ROADMAP_ONE_COMPLETION_MATRIX.md - Steps 1-70 completion matrix.
3. releases/roadmap_one_complete/move_70_final/VERIFICATION_TRANSCRIPT_MOVE_70.md - final Move 70 verification transcript.
4. LOCAL_V1_RELEASE.md - Local v1 release boundary, validation commands, and limits.
5. START_HERE.md - orientation and layout.
6. FIVE_MINUTE_DEMO_SCRIPT.md - short demo script and safe spoken wording.
7. RELEASE_BLOCKER_REGISTER.md - release-blocker register and repair outcome.
8. REVIEWER_FEEDBACK_ROUND.md - feedback-round instructions and honesty boundary.
9. REVIEWER_QUICKSTART.md - checksum, extraction, exact commands, expected markers.
10. PUBLIC_EXPLANATION.md - plain-language public explanation and safe wording.
11. REPOSITORY_STRUCTURE.md - top-level directory and file map.
12. PRIVATE_REVIEWER_PACKAGE.md - private reviewer inspection instructions.
13. LINUX_DESKTOP_RUN_INSTRUCTIONS.md and WINDOWS_NOTES.md - platform notes.

## Quick run

From the repository root, with python3 and a POSIX shell:

sh tools/check_local_v1_release.sh

sh tools/validate_handoff.sh

Expected historical Local v1 marker:

LOCAL_V1_RELEASE_CHECK: PASS

For final Roadmap One completion, see:

releases/roadmap_one_complete/move_70_final/VERIFICATION_TRANSCRIPT_MOVE_70.md

## Layout

- src/ - latest version of each component, in pipeline order.
- verify/ - independent verifier and frozen full-stack component freeze.
- freeze_record/ - candidate and release freeze records.
- tools/ - runnable shell wrappers for tests, verifiers, demo, review checks, and release checks.
- releases/roadmap_one_complete/move_70_final/ - final Roadmap One package, checksum, changelog, and verification transcript.

See REPOSITORY_STRUCTURE.md for the full breakdown.

## Licence

Apache License 2.0 - see LICENSE.

## Status

Roadmap One complete: Steps 1-70.

Status exact marker: Project Witness Roadmap One, Steps 1-70, is complete as a local review/demo stack. Post-completion repairs Move 70.6 and RT-004 are adopted. The Move 71 Python behaviour freeze is adopted. Rust Moves 72-78 are adopted, including ZipGuard archive safety. Part Two has started. Move 79 (verification-only Python/Rust agreement harness) is the current candidate; no full bundle verification capability exists or is claimed.

