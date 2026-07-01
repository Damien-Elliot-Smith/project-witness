# Public Explanation - Project Witness Local v1 Release

Project Witness is a local verification/provenance working stack.

Status: Local v1 Release. Roadmap complete through Move 60; Moves 61-70 remain future work. The 70-step roadmap is not complete.

## Plain explanation

Project Witness checks whether a local package is internally consistent: files,
hashes, manifests, receipts, statuses, and declared workflow outputs must match
the documented structure and pass the local verification scripts.

It is designed to be boring, repeatable, and auditable. A reviewer should be able
to download the package, check the checksum, extract it, run the scripts, and see
clear PASS/FAIL markers.

## What it does not do

It does not prove external truth. It does not prove the outside world is true. It does not prove a person is who
they say they are. It does not decide source trust. It does not sign or externally
anchor outputs. It is not production-ready. It is not a hosted service. It has no
GUI, app, network service, cloud backend, autonomy, or LLM integration.

No external reviewer approval is claimed. The feedback ledger records
`NO_EXTERNAL_FEEDBACK_RECORDED`.

## Safe one-paragraph description

> Project Witness is a local verification/provenance working stack. It does not
> prove external truth. It checks whether files, hashes, manifests, receipts,
> statuses, and declared workflow outputs inside a local package remain internally
> consistent under tested conditions. The current package is the Local v1 Release,
> not a production system.

## Short demo route

Read `FIVE_MINUTE_DEMO_SCRIPT.md`, then run:

```sh
sh tools/check_local_v1_release.sh
sh tools/run_demo.sh
```

Expected markers include `LOCAL_V1_RELEASE_CHECK: PASS`, `COMPANION_COMPLETED`,
and `verify_ok: true`.

Status exact marker: Roadmap complete through Move 60; Moves 61-70 remain future work.
