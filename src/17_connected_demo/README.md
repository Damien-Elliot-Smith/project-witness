# Project Witness Connected Demo v0.1

A thin, deterministic orchestrator that runs the top-level Project Witness chain
end to end and records the terminal statuses. It drives the frozen Companion
v0.3.1, Unified Case Manifest v0.1, Stack Verifier v0.1, and Stack Selfcheck
v0.1.2 CLIs (Companion in turn drives Coordinator v0.3.2 and the lower stack). It
is standard-library only.

It does not modify any frozen component, does not copy evidence contents, and
does not prove truth. It only records the statuses the frozen components already
report, and reaches DEMO_COMPLETED when all of these hold:

    COMPANION_COMPLETED
    WORKFLOW_COMPLETED
    ATLAS_VALIDATED
    SOURCE_VERIFIED
    STACK_VERIFIED
    STACK_SELFCHECK_PASSED

## Stages (fixed order, short-circuit)

1. Companion `create-evidence-case` (Coordinator v0.3.2 + Atlas validation + the
   lower stack) -> COMPANION_COMPLETED, WORKFLOW_COMPLETED, ATLAS_VALIDATED
2. Unified Case Manifest `build` -> SOURCE_VERIFIED
3. Stack Verifier `check` -> STACK_VERIFIED (and SOURCE_VERIFIED)
4. Stack Selfcheck v0.1.2 `check --stack-verifier-run ...` -> STACK_SELFCHECK_PASSED

If any stage does not reach its required status, the demo records DEMO_FAILED and
stops. No status is ever faked.

## Run (real chain)

    python3 connected_demo.py run \
      --companion-root ... --coordinator-root ... --atlas-registry-root ... \
      --sentinel-root ... --histor-lite-root ... --aletheia-root ... \
      --bridge-root ... --odin-root ... --histor-aletheia-root ... \
      --histor-odin-root ... --case-bundle-v02-root ... \
      --unified-manifest-root ... --stack-verifier-root ... \
      --stack-selfcheck-root ... \
      --case-id CASE-DEMO --evidence-id EV-DEMO \
      --evidence-file /path/to/evidence.txt \
      --allowed-root /path/to/writable_root \
      --case-directory-name demo_case \
      --inventory /path/to/stack_inventory.json \
      --out /path/to/connected_demo_output

## Verify / selfcheck

    python3 connected_demo.py verify --run /path/to/connected_demo_output
    python3 connected_demo.py selfcheck

`selfcheck` and the unit tests use a fixture runner and spawn no subprocesses and
need no frozen components. The real chain is driven only by `run`.

## Boundaries

- It does not run workflows itself; it invokes the frozen components that do.
- It does not call frozen components except through their public CLIs.
- It does not copy evidence contents.
- It does not prove truth; it records reported statuses only.
