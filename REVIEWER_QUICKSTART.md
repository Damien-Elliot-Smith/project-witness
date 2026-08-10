# Reviewer Quickstart

A one-page guide for an external reviewer. Plain and technical. No hype.

## What this zip is

This repository contains the runnable **Project Witness Roadmap One** working stack
and the adopted Moves 71-85 Rust-hardening block. The inherited Roadmap One path
under `src/` is standard-library Python with no third-party Python packages and no
build step. The Rust verifier is source-built from the `rust/` workspace and
requires Cargo/Rust for the documented build route.

Current publication state (2026-08-10): Roadmap One, Steps 1–70, is complete as a local review/demo stack. Move 70.6 and RT-004 are adopted post-completion repairs. Move 71 Python behaviour freeze is adopted. Rust-hardening Moves 72–85 are adopted. Move 85 v08 is the current adopted technical authority for this publication state. Project Witness is not production-ready.

## What this is NOT

- It does **not** prove external truth or that any evidence is factually correct.
- It does **not** authenticate real-world identity or source trust.
- Move 65 signing is test-only; Move 66 anchoring is local simulation only. No production-valid signing or real external anchoring is claimed.
- It is **not** production-ready.
- It does **not** claim external reviewer approval. The feedback ledger records
  `NO_EXTERNAL_FEEDBACK_RECORDED`.

## Current authority and Rust-hardening route

Current adopted technical authority: `project-witness-MOVE_85_candidate_v08.zip`
SHA-256: `f512cc9933153d2a6a97c3158515766fc3c9db0a226153cbb010b37fccb59665`

Read `HANDOFF_MOVES_71_TO_85.md` for the exact source-build and run commands. The
held Rust build/runtime evidence establishes Android/Termux AArch64 only. Linux
x86_64, Linux AArch64, and Windows x86_64 remain unestablished. A clean Rust
bundle result is `INCONCLUSIVE`, exit `3`, not PASS.

## Historical Roadmap One package checksum route

The following checksum/extraction route is retained for the Roadmap One final package:

From the directory containing the zip and sidecar:

```sh
sha256sum -c Project_Witness_WORKING_STACK_v20_MOVE_70.zip.sha256
```

Expected:

```text
Project_Witness_WORKING_STACK_v20_MOVE_70.zip: OK
```

If `sha256sum` is unavailable, use:

```sh
shasum -a 256 Project_Witness_WORKING_STACK_v20_MOVE_70.zip
```

and compare the digest in the `.sha256` sidecar by eye.

## Extract safely

```sh
mkdir pw_review && cd pw_review
unzip ../Project_Witness_WORKING_STACK_v20_MOVE_70.zip
cd Project_Witness_WORKING_STACK
```

The archive is intended to contain relative paths under one top-level folder.

## Run the Roadmap One path

Requires `python3` and a POSIX shell. Run from the extracted
`Project_Witness_WORKING_STACK/` directory.

```sh
sh tools/check_local_v1_release.sh
sh tools/validate_handoff.sh
```

Optional individual checks:

```sh
sh tools/check_release_blockers.sh
sh tools/check_reviewer_feedback_round.sh
sh tools/check_five_minute_demo_script.sh
sh tools/check_public_explanation.sh
sh tools/check_private_reviewer_package.sh
sh tools/check_repository_structure.sh
sh tools/check_linux_desktop_instructions.sh
sh tools/check_windows_notes.sh
sh tools/run_all_tests.sh
sh tools/run_independent_verify.sh
sh tools/run_local_v1_verify.sh
sh tools/run_termux_verify.sh
sh tools/run_demo.sh
```

## Expected PASS markers

| Command | Expected marker |
|---|---|
| `check_local_v1_release.sh` | `LOCAL_V1_RELEASE_CHECK: PASS` |
| `check_release_blockers.sh` | `RELEASE_BLOCKERS_CHECK: PASS` |
| `check_reviewer_feedback_round.sh` | `REVIEWER_FEEDBACK_ROUND_CHECK: PASS` |
| `check_five_minute_demo_script.sh` | `FIVE_MINUTE_DEMO_SCRIPT_CHECK: PASS` |
| `check_public_explanation.sh` | `PUBLIC_EXPLANATION_CHECK: PASS` |
| `check_private_reviewer_package.sh` | `PRIVATE_REVIEWER_PACKAGE_CHECK: PASS` |
| `check_repository_structure.sh` | `REPOSITORY_STRUCTURE_CHECK: PASS` |
| `check_linux_desktop_instructions.sh` | `LINUX_DESKTOP_INSTRUCTIONS_CHECK: PASS` |
| `check_windows_notes.sh` | `WINDOWS_NOTES_CHECK: PASS` |
| `run_all_tests.sh` | `RESULT: PASS - ALL_COMPONENT_TESTS_PASSED` (18/18, 1234 tests) |
| `run_independent_verify.sh` | `PROJECT_WITNESS_INDEPENDENT_VERIFICATION_PASSED` / `verify_ok = true` |
| `run_local_v1_verify.sh` | `LOCAL_V1_CANDIDATE_VERIFIED` / `verify_ok = true` |
| `run_termux_verify.sh` | `TERMUX_RUN_INSTRUCTIONS_VERIFIED` / `verify_ok = true` |
| `run_demo.sh` | `COMPANION_COMPLETED` and `verify_ok: true` |
| `validate_handoff.sh` | `HANDOFF_VALIDATION: PASS` |

Each script exits 0 on pass and non-zero on failure.

## Where to look

- `CURRENT_RELEASE_STATE.md` - current Move 85 publication state.
- `HANDOFF_MOVES_71_TO_85.md` - Rust-hardening build/run/audit handoff.
- `LOCAL_V1_RELEASE.md` - historical Move 60 release boundary and validation.
- `START_HERE.md` - orientation and layout.
- `MOVE_INDEX.md` - Roadmap One Steps 1-70 plus adopted Moves 71-85.
- `STACK_STATUS.md` - verification record.
- `HANDOFF_NOTES.md` - scope and honesty boundary.
- `src/NN_*/` - each component's working code, with freeze-time docs in `_frozen/`.

Status exact marker: Current publication state (2026-08-10): Roadmap One, Steps 1–70, is complete as a local review/demo stack. Move 70.6 and RT-004 are adopted post-completion repairs. Move 71 Python behaviour freeze is adopted. Rust-hardening Moves 72–85 are adopted. Move 85 v08 is the current adopted technical authority for this publication state. Project Witness is not production-ready.
