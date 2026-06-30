# Companion CLI v0.3.1 — Repair Ledger

## What this is

v0.3.1 is a **narrow blocker repair for Move 30** (Project Witness Connected
Demo v0.1). It is not a new feature. The package folder/zip is named
`companion_cli_v031`; the output schema and `companion_cli_version` remain
**0.3.0** for compatibility with Unified Case Manifest v0.1, Stack Verifier v0.1,
Stack Selfcheck v0.1, and the Connected Demo.

## The blocker (v0.3.0)

After Coordinator Workflow v0.3.1 made the Coordinator complete a real run,
Companion v0.3 still failed:

    companion_status = FAILED_COMPANION_VERIFY
    error = unknown top-level entries: ['_coordinator_request.json']

Cause: `companion_lib/coordinator_runner.py`,
`SubprocessCoordinatorRunner.run`, wrote its Coordinator request copy to
`dirname(coord_dir)/_coordinator_request.json` — i.e. the **Companion-output top
level** — and never removed it. Companion's own `companion_lib/verifier.py` has
`ALLOWED_TOP_LEVEL = REQUIRED_TOP_FILES | {coordinator_output}`, which does not
include `_coordinator_request.json`, so Companion rejected a file it created
itself. The defect was masked until now because the v0.3.0 stub Coordinator
failed first (`FAILED_COORDINATOR_RUN`), so Companion never reached this verify.

## The repair (v0.3.1)

`SubprocessCoordinatorRunner.run` now writes the Coordinator request to a private
temp directory **outside** the output tree (`tempfile.mkdtemp(...)`), passes that
path to `coordinator_v03.py run --request`, and deletes it in a `finally` block.
The Coordinator only reads `--request` (it copies it into its own output as
`workflow_request_copy.json`), so Companion never needed to keep the file. The
final Companion output therefore contains only the allowed top-level entries:
`workflow_request.json`, `companion_report.json`, `companion_steps.json`,
`companion_checksums.txt`, and `coordinator_output/`.

The verifier was **not** weakened: it still refuses any unknown top-level entry
(two tests assert this, including the previously stray filename).

## Invariants preserved

- **No new feature, workflow, action type, or Atlas term.** Same nine-step flow,
  same CLI shape (`create-evidence-case` / `verify` / `selfcheck`).
- **No frozen component modified.** Coordinator v0.3.1, Sentinel, Histor-lite,
  Aletheia, Bridge, ODIN, Case Bundle, Atlas, Unified Manifest, Stack Verifier,
  and Stack Selfcheck are untouched.
- **Output schema unchanged.** `companion_cli_version` stays `0.3.0`; the
  Companion report/steps/checksums layout is byte-for-byte the v0.3.0 contract.
- **Freeze gate stays in-process.** `subprocess` remains confined to
  `coordinator_runner.py`; the default suite drives the real `run()` hygiene path
  with an in-process stub and spawns no process.

## R-numbers

- **R1 — request out of the output tree.** Write the Coordinator request to a
  private temp dir and delete it; never place it at the Companion-output top level.
- **R2 — verifier unchanged.** Keep `ALLOWED_TOP_LEVEL` strict; unknown top-level
  entries are still refused.
- **R3 — tests.** `tests/test_request_hygiene.py` asserts: no
  `_coordinator_request.json` at top level, the request is written outside the
  output and cleaned up, Companion verify passes after a real Coordinator
  completion, only allowed top-level entries remain, and unknown top-level files
  are still refused.
