# Reviewer Quickstart

A one-page guide for an external reviewer. Plain and technical. No hype.

---

## What this zip is

The runnable **working stack** of Project Witness: the latest version of each
component (extracted, in pipeline order under `src/`), the frozen verification
artifacts, and shell scripts to run everything. Standard library Python only.
No network, no third-party packages, no build step.

It is a **Local v1 Candidate** — a local, runnable integrity-verification stack
that checks structured provenance relationships between files, hashes, manifests,
receipts, statuses, and declared workflow outputs under tested local conditions.

## What this is NOT

- It does **not** prove external truth or that any evidence is factually correct.
- It does **not** authenticate real-world identity or source trust.
- It does **not** sign outputs or anchor them to any external timestamp/ledger.
- It is **not** production-ready and **not** a final Local v1 Release.
- It does **not** complete the 70-step roadmap. Moves 52–70 remain future work.

## Verify the download checksum

From the directory containing the zip and its `.sha256` sidecar:

```sh
sha256sum -c Project_Witness_WORKING_STACK_v02.zip.sha256
```

Expected: `Project_Witness_WORKING_STACK_v02.zip: OK`.

(If `sha256sum` is unavailable, `shasum -a 256 Project_Witness_WORKING_STACK_v02.zip`
and compare the digest in the `.sha256` file by eye.)

## Extract safely

```sh
mkdir pw_review && cd pw_review
unzip ../Project_Witness_WORKING_STACK_v02.zip
cd Project_Witness_WORKING_STACK
```

The archive contains only relative paths under a single top-level folder; there
are no absolute paths and no `..` traversal entries.

## Run it

Requires `python3` (3.8+) and a POSIX shell. Run from the extracted
`Project_Witness_WORKING_STACK/` directory.

**On a Linux desktop or laptop?** See `LINUX_DESKTOP_RUN_INSTRUCTIONS.md` for the
full step-by-step (required tools, checksum, extraction, and each command). You
can confirm your machine is ready with `sh tools/check_linux_desktop_instructions.sh`.

**On Windows?** See `WINDOWS_NOTES.md`. Native Windows execution is not tested; the
recommended route is WSL2 + Ubuntu, then follow the Linux instructions inside WSL2.

One command for everything (runs all of the below and fails closed):

```sh
sh tools/validate_handoff.sh
```

Or run each stage individually:

```sh
sh tools/run_all_tests.sh           # all 18 component unittest suites
sh tools/run_independent_verify.sh  # independent check of the Move 45 freeze
sh tools/run_local_v1_verify.sh     # Move 50 Local v1 Candidate freeze record
sh tools/run_termux_verify.sh       # Move 51 Termux instructions package
sh tools/run_demo.sh                # live end-to-end pipeline run + verify
```

## Expected PASS markers

| Command | Expected marker |
|---|---|
| `run_all_tests.sh` | `RESULT: PASS — ALL_COMPONENT_TESTS_PASSED` (18/18, 1234 tests) |
| `run_independent_verify.sh` | `PROJECT_WITNESS_INDEPENDENT_VERIFICATION_PASSED` / `verify_ok = true` |
| `run_local_v1_verify.sh` | `LOCAL_V1_CANDIDATE_VERIFIED` / `verify_ok = true` |
| `run_termux_verify.sh` | `TERMUX_RUN_INSTRUCTIONS_VERIFIED` / `verify_ok = true` |
| `run_demo.sh` | `COMPANION_COMPLETED` … `verify_ok: true` |
| `validate_handoff.sh` | `HANDOFF_VALIDATION: PASS` |

Each script exits `0` on pass and non-zero on failure, so they can be wired into
CI or a manual checklist. On failure, the failing component's full output is
printed (not suppressed).

## Where to look

- `START_HERE.md` — orientation and layout.
- `MOVE_INDEX.md` — every roadmap move (1–51) mapped to an artifact.
- `STACK_STATUS.md` — the verification record (what was run, what passed).
- `HANDOFF_NOTES.md` — scope, archive relationship, honesty boundaries.
- `src/NN_*/` — each component's working code, with its freeze-time docs in `_frozen/`.
