# Public Explanation - Project Witness

Project Witness is a local verification/provenance working stack.

Current publication state (2026-08-10): Roadmap One, Steps 1–70, is complete as a local review/demo stack. Move 70.6 and RT-004 are adopted post-completion repairs. Move 71 Python behaviour freeze is adopted. Rust-hardening Moves 72–85 are adopted. Move 85 v08 is the current adopted technical authority for this publication state. Project Witness is not production-ready.

## Plain explanation

Project Witness checks whether a local package is internally consistent: files,
hashes, manifests, receipts, statuses, and declared workflow outputs must match
the documented structure and pass the local verification scripts.

It is designed to be boring, repeatable, and auditable. A reviewer should be able
to download the package, check the checksum, extract it, run the scripts, and see
clear result markers.

## What it does not do

It does not prove external truth. It does not prove the outside world is true. It does not prove a person is who
they say they are. It does not decide source trust. Move 65 signing is test-only
and Move 66 anchoring is local simulation only; no production-valid signing or
real external anchoring is claimed. It is not production-ready or a hosted
service. Move 67 web UI is read-only; no production GUI/app, cloud backend,
autonomy, or LLM integration is claimed.

No external reviewer approval is claimed. The feedback ledger records
`NO_EXTERNAL_FEEDBACK_RECORDED`.

## Safe one-paragraph description

> Project Witness is a local verification/provenance working stack. It does not
> prove external truth. It checks whether files, hashes, manifests, receipts,
> statuses, and declared workflow outputs inside a local package remain internally
> consistent under tested conditions. Roadmap One is complete as a local review/demo
> stack, and Rust-hardening Moves 72-85 are adopted. Move 85 v08 is the current
> adopted technical authority. The project is not a production system.

## Short demo route

For the inherited Roadmap One Python demo, read `FIVE_MINUTE_DEMO_SCRIPT.md`, then run:

```sh
sh tools/check_local_v1_release.sh
sh tools/run_demo.sh
```

Expected markers include `LOCAL_V1_RELEASE_CHECK: PASS`, `COMPANION_COMPLETED`,
and `verify_ok: true`.

For the adopted Rust-hardening demonstration and audit pack, read `HANDOFF_MOVES_71_TO_85.md` and `verify/demo_v01/README.md`. A clean Rust bundle result is `INCONCLUSIVE`, exit `3`, not PASS. Held Rust build/runtime evidence establishes Android/Termux AArch64 only.

Status exact marker: Current publication state (2026-08-10): Roadmap One, Steps 1–70, is complete as a local review/demo stack. Move 70.6 and RT-004 are adopted post-completion repairs. Move 71 Python behaviour freeze is adopted. Rust-hardening Moves 72–85 are adopted. Move 85 v08 is the current adopted technical authority for this publication state. Project Witness is not production-ready.
