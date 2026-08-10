# Linux Desktop Run Instructions

How to verify and run the Project Witness working stack on an ordinary Linux
desktop or laptop. Plain and technical. No hype.

This is roadmap **Move 52**. It adds instructions only. It does not change any
component, schema, or behaviour, and it does not complete the 70-step roadmap.

---

## Supported environment

An ordinary Linux desktop or laptop (for example Ubuntu, Debian, Fedora, Arch, or
similar). No special hardware. No root required. No network required.

## Required tools

All of these are present by default on most Linux desktops:

- `python3` (3.8 or newer)
- a POSIX shell (`sh`)
- `unzip`
- `sha256sum` (from coreutils)

Check they exist:

```sh
python3 --version
sh -c 'echo sh ok'
unzip -v | head -1
sha256sum --version | head -1
```

If `unzip` is missing, install it with your package manager, e.g.
`sudo apt install unzip` (Debian/Ubuntu) or `sudo dnf install unzip` (Fedora).
`python3`, `sh`, and `sha256sum` are normally already installed.

## No network, no extra Python packages

The stack is standard-library Python only. Nothing here downloads anything, opens
a socket, or needs `pip install`. You can run it fully offline. If any command
ever reports a missing third-party module, stop and report it — that would be a
defect, not an expected step.

---

## Step 1 — Verify the download checksum

Put `Project_Witness_WORKING_STACK_v03_MOVE_52.zip` and its
`Project_Witness_WORKING_STACK_v03_MOVE_52.zip.sha256` sidecar in the same folder,
then:

```sh
sha256sum -c Project_Witness_WORKING_STACK_v03_MOVE_52.zip.sha256
```

Expected:

```text
Project_Witness_WORKING_STACK_v03_MOVE_52.zip: OK
```

If it does not say `OK`, do not proceed — the file is incomplete or altered.

## Step 2 — Extract the zip

```sh
mkdir -p pw_review
cd pw_review
unzip ../Project_Witness_WORKING_STACK_v03_MOVE_52.zip
```

The archive contains only relative paths under a single top-level folder. There
are no absolute paths and no `..` traversal entries.

## Step 3 — Enter the extracted folder

```sh
cd Project_Witness_WORKING_STACK
```

---

## Step 4 — Run the main validator (one command)

```sh
sh tools/validate_handoff.sh
```

This runs the full component test suite, the three frozen-artifact verifiers, and
the live end-to-end demo, then prints a summary. It fails closed: a non-zero exit
means at least one stage failed, and the failing output is shown, not hidden.

Expected final line:

```text
HANDOFF_VALIDATION: PASS
```

## Step 5 — Run each verification command separately (optional)

If you want to run the stages individually instead of the single validator:

```sh
sh tools/run_all_tests.sh           # all 18 component unittest suites (1234 tests)
sh tools/run_independent_verify.sh  # independent check of the Move 45 freeze
sh tools/run_local_v1_verify.sh     # Move 50 Local v1 Release freeze record
sh tools/run_termux_verify.sh       # Move 51 Termux instructions package
```

## Step 6 — Run the live demo

```sh
sh tools/run_demo.sh
```

This runs the real pipeline end to end (Companion drives the lower stack) and then
verifies the produced output.

---

## Expected PASS markers

| Command | Expected marker |
|---|---|
| `sha256sum -c …` | `Project_Witness_WORKING_STACK_v03_MOVE_52.zip: OK` |
| `tools/validate_handoff.sh` | `HANDOFF_VALIDATION: PASS` |
| `tools/run_all_tests.sh` | `RESULT: PASS — ALL_COMPONENT_TESTS_PASSED` (18/18, 1234 tests) |
| `tools/run_independent_verify.sh` | `PROJECT_WITNESS_INDEPENDENT_VERIFICATION_PASSED` / `verify_ok = true` |
| `tools/run_local_v1_verify.sh` | `LOCAL_V1_CANDIDATE_VERIFIED` / `verify_ok = true` |
| `tools/run_termux_verify.sh` | `TERMUX_RUN_INSTRUCTIONS_VERIFIED` / `verify_ok = true` |
| `tools/run_demo.sh` | `COMPANION_COMPLETED` … `verify_ok: true` |

Every script exits `0` on pass and non-zero on failure.

## What failure means

- **Checksum not `OK`** — the download is incomplete or altered. Re-download; do
  not run it.
- **A component test FAIL** — the wrapper prints that component's full output and
  exits non-zero. Read the traceback; do not treat the stack as verified.
- **A verifier prints `verify_ok = false` / a `FAIL` marker** — a frozen artifact
  did not match its expected state. Stop and investigate the named artifact.
- **A missing third-party module error** — not expected; report it.

In all failure cases the correct response is to stop and read the output, not to
work around it.

## Known limits

This stack preserves and verifies structured provenance relationships between
files, hashes, manifests, receipts, statuses, and declared workflow outputs under
tested local conditions. It does **not**:

- prove external truth or that any evidence is factually correct,
- authenticate real-world identity or source trust,
- sign outputs or anchor them to any external timestamp or ledger,
- provide a GUI, network service, or cloud component.

It is **not** production-ready. It is a Local v1 **Candidate**, not a final Local
v1 Release. The roadmap is complete **through Move 58**; Moves
59-70 remain future work. Do not describe the 70-step roadmap as complete.


## Current release status

Status exact marker: Project Witness Roadmap One, Steps 1-70, is complete as a local review/demo stack. Post-completion repairs Move 70.6 and RT-004 are adopted. The Move 71 Python behaviour freeze is adopted. Rust Moves 72-78 are adopted, including ZipGuard archive safety. Part Two has started. Move 79 (verification-only Python/Rust agreement harness) is the current candidate; no full bundle verification capability exists or is claimed.
