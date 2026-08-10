# Project Witness - Working Stack

A local, deterministic integrity-verification stack: an inherited standard-library-only Python Roadmap One stack plus an adopted Rust-hardening block.

Project Witness preserves and verifies structured provenance relationships between files, hashes, manifests, receipts, statuses, and declared workflow outputs under tested local conditions.

This repository is the runnable Project Witness working stack.

## Roadmap One status

Current publication state (2026-08-10): Roadmap One, Steps 1–70, is complete as a local review/demo stack. Move 70.6 and RT-004 are adopted post-completion repairs. Move 71 Python behaviour freeze is adopted. Rust-hardening Moves 72–85 are adopted. Move 85 v08 is the current adopted technical authority for this publication state. Project Witness is not production-ready.

Single authoritative current-state document: CURRENT_RELEASE_STATE.md
Inherited checker: tools/check_current_release_state.sh (it contains pre-Move-85 publication assertions and is not the publication authority).

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

- The inherited Roadmap One stack is pure standard-library Python.
- The Roadmap One Python path requires no third-party Python packages and no build step.
- No network requirement for the checked local stack.
- The adopted Rust verifier is source-built from the `rust/` workspace with Cargo/Rust; the held build/runtime evidence establishes Android/Termux AArch64 only.
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

1. CURRENT_RELEASE_STATE.md - current adopted publication state and evidence boundaries.
2. START_HERE.md - orientation, prerequisites, and current review path.
3. HANDOFF_MOVES_71_TO_85.md - adopted Rust-hardening handoff, exact build/run route, known divergences, and platform evidence.
4. REVIEWER_QUICKSTART.md - Roadmap One review route plus the current Rust-hardening review route.
5. FIVE_MINUTE_DEMO_SCRIPT.md - bounded demonstration wording.
6. PUBLIC_EXPLANATION.md - plain-language public explanation and safe wording.
7. REPOSITORY_STRUCTURE.md - top-level directory and file map.
8. RELEASE_BLOCKER_REGISTER.md and REVIEWER_FEEDBACK_ROUND.md - blocker/feedback records and review process.

## Historical Roadmap One material

These remain important provenance for the completed Roadmap One stack; they are not the current Move 85 publication-state authority:

- ROADMAP_ONE_COMPLETE.md - final Roadmap One completion note.
- ROADMAP_ONE_COMPLETION_MATRIX.md - Steps 1-70 completion matrix.
- releases/roadmap_one_complete/move_70_final/VERIFICATION_TRANSCRIPT_MOVE_70.md - final Move 70 verification transcript.
- LOCAL_V1_RELEASE.md - historical Move 60 Local v1 release boundary.
- PRIVATE_REVIEWER_PACKAGE.md - reviewer instructions that retain the Roadmap One package route.
- LINUX_DESKTOP_RUN_INSTRUCTIONS.md and WINDOWS_NOTES.md - inherited platform notes, now explicitly scoped where needed.

## Quick run

For the inherited Roadmap One Python/POSIX checks, from the repository root with `python3` and a POSIX shell:

sh tools/check_local_v1_release.sh

sh tools/validate_handoff.sh

Expected historical Local v1 marker:

LOCAL_V1_RELEASE_CHECK: PASS

For final Roadmap One completion, see:

releases/roadmap_one_complete/move_70_final/VERIFICATION_TRANSCRIPT_MOVE_70.md

For the adopted Rust-hardening block, read `HANDOFF_MOVES_71_TO_85.md`. The supported build route builds from source in the `rust/` workspace with Cargo. Held build/runtime evidence establishes Android/Termux AArch64 only; Linux x86_64, Linux AArch64, and Windows x86_64 remain unestablished.

## Layout

- src/ - latest version of each component, in pipeline order.
- verify/ - inherited verifier material plus adopted Rust-hardening fixtures, demonstrations, reports, comparison material, and `audit_pack_v01/`.
- rust/ - Cargo workspace containing the source-built `witness-verify` verifier.
- freeze_record/ - candidate and release freeze records.
- tools/ - runnable shell wrappers for tests, verifiers, demo, review checks, and release checks.
- releases/roadmap_one_complete/move_70_final/ - final Roadmap One package, checksum, changelog, and verification transcript.

See REPOSITORY_STRUCTURE.md for the full breakdown.

## Licence

Apache License 2.0 - see LICENSE.

## Status

Roadmap One complete: Steps 1-70.

Move 85 v08 technical-authority SHA-256: `f512cc9933153d2a6a97c3158515766fc3c9db0a226153cbb010b37fccb59665`
Frozen technical-authority commit: `0ae018bc00b5a59f6dcbb6629a2706cb9059280b`

Status exact marker: Current publication state (2026-08-10): Roadmap One, Steps 1–70, is complete as a local review/demo stack. Move 70.6 and RT-004 are adopted post-completion repairs. Move 71 Python behaviour freeze is adopted. Rust-hardening Moves 72–85 are adopted. Move 85 v08 is the current adopted technical authority for this publication state. Project Witness is not production-ready.

