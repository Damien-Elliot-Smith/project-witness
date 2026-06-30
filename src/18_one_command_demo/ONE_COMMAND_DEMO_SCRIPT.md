# One-Command Demo Script — how it works

This document explains, in plain terms, what the wrapper does internally. It is a
**usability wrapper only**: it runs the frozen Connected Demo v0.1 through its own
public CLI and records what happened. It changes nothing about how the demo
behaves.

## The eight steps

1. **VALIDATE_CONFIG** — read the config file, confirm `config_version` is
   `0.1.0`, and confirm it names a `connected_demo_root` and a
   `connected_demo_config`. A bad config fails with `FAILED_CONFIG_INVALID`.
2. **CHECK_CONNECTED_DEMO_ROOT** — confirm the Connected Demo folder exists and
   contains `connected_demo.py`. Otherwise `FAILED_CONNECTED_DEMO_RUN`.
3. **RUN_CONNECTED_DEMO** — call the frozen `connected_demo.py run` with the
   parameters from `connected_demo_config`, writing into
   `connected_demo_output/`. A non-zero result fails with
   `FAILED_CONNECTED_DEMO_RUN`.
4. **VERIFY_CONNECTED_DEMO** — call the frozen `connected_demo.py verify` on that
   output. If it does not report `verify_ok`, fail with
   `FAILED_CONNECTED_DEMO_VERIFY`.
5. **READ_CONNECTED_DEMO_REPORT** — read the demo's own report and collect its
   `demo_status` and `observed_statuses`, plus the structural
   `truth_boundary_valid` from the Stack Verifier output it produced.
6. **CHECK_REQUIRED_STATUSES** — confirm all seven required statuses are present
   and that the truth boundary is valid. A missing status fails with
   `FAILED_REQUIRED_STATUS_MISSING`; an invalid truth boundary fails with
   `FAILED_TRUTH_BOUNDARY`.
7. **WRITE_ONE_COMMAND_REPORT** — write the canonical wrapper report, the steps
   file, and the checksums file.
8. **VERIFY_ONE_COMMAND_OUTPUT** — re-check the wrapper's own output (exact
   top-level entries, canonical report, valid checksums, required statuses, no
   truth claims, no absolute paths). A problem fails with
   `FAILED_CHECKSUMS_INVALID`.

## What it never does

It never edits frozen folders, never patches component outputs, never invents a
status, and never fakes `DEMO_COMPLETED`. If the underlying demo does not reach
all seven statuses, the wrapper says so honestly and stops. It does not sign,
anchor, use an LLM, or touch the network.

## Truth boundary

One-Command Demo Script v0.1 runs and verifies the frozen Project Witness
Connected Demo v0.1. It does not prove evidence contents are true, does not prove
ODIN claims are true, and does not verify external reality.
