# Project Witness — Working Stack

This folder is the clean, runnable working set: the **latest canonical version of
every component**, extracted and ready to read, run, and edit. Everything that is
superseded, adversarial, documentary, or a large review bundle lives in the
separate `Project_Witness_ARCHIVE/` folder.

Standard library only. No network. No signing. No external anchoring.

**External reviewer?** Start with `REVIEWER_QUICKSTART.md` — it covers checksum
verification, safe extraction, the exact commands, and the expected PASS markers.
**On a Linux desktop/laptop?** See `LINUX_DESKTOP_RUN_INSTRUCTIONS.md` for the
full step-by-step. **On Windows?** See `WINDOWS_NOTES.md` — native Windows is not
directly verified, so WSL2 + Ubuntu (then the Linux instructions) is the
recommended route.

---

## Layout

```
Project_Witness_WORKING_STACK/
  START_HERE.md            <- you are here
  STACK_STATUS.md          <- verification record (what was run, what passed)
  MOVE_INDEX.md            <- all 51 roadmap moves mapped to artifacts
  project_witness_70_step_roadmap.pdf
  src/                     <- the working code, in pipeline order (01..18)
    01_sentinel_core/      ... 18_one_command_demo/
      <component code>
      _frozen/             <- original frozen .zip + .sha256 + TEST_RESULTS + REPAIR_LEDGER
  verify/                  <- independent verifier + the Move 45 full-stack freeze it checks
  freeze_record/           <- Move 50 Local v1 Candidate freeze + Move 51 Termux instructions
  tools/
    run_all_tests.sh       <- runs every component's unittest suite
    run_live_e2e_demo.sh   <- runs the whole core pipeline live, end to end
```

Each `src/NN_*/` folder holds the working code at top level. The matching frozen
artifact (zip + sidecar) and its test/repair documentation sit in that folder's
`_frozen/` subfolder, so the integrity copy travels with the code.

---

## Pipeline order (src/)

```
01 sentinel_core            action gate: ALLOW / BLOCK / DRY_RUN + tamper-evident receipts
02 histor_lite              append-only case store
03 aletheia_evidence_bundle evidence packaging + manifest
04 aletheia_odin_bridge     evidence manifest -> ODIN claim format
05 odin_claim_reasoner      deterministic structural claim reasoner
06 histor_aletheia_importer imports Aletheia bundles into Histor-lite
07 histor_odin_importer     imports ODIN outputs into Histor-lite
08 case_bundle_v02          case bundle format + verifier
09 atlas_registry           read-only controlled vocabulary
10 atlas_release_gate       validates Coordinator output against Atlas
11 coordinator_workflow_v032 orchestrates the full lower stack
12 companion_cli_v031       human-facing entry point (drives Coordinator)
13 unified_case_manifest    cross-component manifest
14 stack_verifier           end-to-end stack output verifier
15 stack_selfcheck_v012     stack inventory / documentation selfcheck
16 evidence_reasoning_demo  evidence -> ODIN reasoning demonstration
17 connected_demo           end-to-end connected pipeline orchestrator
18 one_command_demo         one-command beginner demo wrapper
```

---

## How to run

From this folder. One command runs everything and fails closed:

```sh
sh tools/validate_handoff.sh     # all tests + all verifiers + live demo
```

Expected final line: `HANDOFF_VALIDATION: PASS` (exit 0).

Or run each stage on its own:

```sh
sh tools/run_all_tests.sh           # all 18 component test suites (1234 tests)
sh tools/run_independent_verify.sh  # independent check of the Move 45 freeze
sh tools/run_local_v1_verify.sh     # Move 50 Local v1 Candidate freeze record
sh tools/run_termux_verify.sh       # Move 51 Termux instructions package
sh tools/run_demo.sh                # live end-to-end pipeline run + verify
```

Each script prints a clear `RESULT:`/`verify_ok` marker and exits 0 on pass,
non-zero on failure (failure output is shown, not hidden). Expected markers are
listed in `REVIEWER_QUICKSTART.md`.

---

## Truth boundary

This stack preserves and verifies structured provenance relationships between
files, hashes, manifests, receipts, statuses, and declared workflow outputs under
tested local conditions.

It does **not** prove external truth, authenticate sources, sign outputs,
externally anchor outputs, or claim production readiness. The full limitation set
is preserved in `Project_Witness_ARCHIVE/03_review_and_documentation/master_known_limitations_v01/`.

This is a **Local v1 Candidate**, not a final Local v1 Release. The 70-step
roadmap is **not** complete — see `MOVE_INDEX.md`.
