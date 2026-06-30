# One-Command Demo Script v0.1

A small **usability wrapper** that lets a beginner run and verify the already-frozen
Project Witness **Connected Demo v0.1** with one clear command, then writes a tiny
wrapper report.

One-Command Demo Script v0.1 runs and verifies the frozen Project Witness
Connected Demo v0.1. It does not prove evidence contents are true, does not prove
ODIN claims are true, and does not verify external reality.

It only orchestrates the Connected Demo's public CLI. It does not modify any
frozen component, does not modify the Connected Demo, does not invent statuses,
and never fakes DEMO_COMPLETED. Standard library only; no network; no signing or
anchoring; no LLM.

## Commands

Run:

    python3 one_command_demo.py run \
      --config /path/to/demo_config.json \
      --out /path/to/output

Verify a finished run:

    python3 verify_one_command_demo.py \
      --run /path/to/output

Self-check (no frozen components needed):

    python3 one_command_demo.py selfcheck

## Config file

The config points to the frozen Connected Demo package and the Connected Demo's
own parameters. Absolute paths are allowed **in this input config only**; they are
never stored in the wrapper report.

    {
      "config_version": "0.1.0",
      "connected_demo_root": "/path/to/connected_demo_v01",
      "connected_demo_config": "/path/to/connected_demo_config.json"
    }

`connected_demo_config` is a JSON file holding the Connected Demo `run`
parameters (the component roots, the evidence file, the writable allowed-root, the
case identifiers, and the inventory). The wrapper passes them straight to the
frozen `connected_demo.py run` CLI; it does not change their meaning.

## Success condition

The wrapper reports success only if the underlying Connected Demo reaches **all
seven** statuses: DEMO_COMPLETED, COMPANION_COMPLETED, WORKFLOW_COMPLETED,
ATLAS_VALIDATED, SOURCE_VERIFIED, STACK_VERIFIED, STACK_SELFCHECK_PASSED. If any
one is missing, the wrapper fails honestly with a specific `FAILED_...` status.

## Output

A successful run writes, under `--out`, exactly:

    one_command_demo_report.json
    one_command_demo_steps.json
    one_command_demo_checksums.txt
    connected_demo_output/

`connected_demo_output/` holds the real output from the frozen Connected Demo
v0.1. See RUN_FORMAT.md for the report and step formats.

## Boundaries

- It does not modify frozen folders or patch component outputs.
- It does not bypass Connected Demo verification.
- It does not sign or anchor anything, use an LLM, or call the network.
- It adds no new workflow logic; it is a wrapper only.

This is Step 32. The Demo Output Bundle (Step 33) and the Architecture Diagram
(Step 34) are deferred and are not part of this package.
