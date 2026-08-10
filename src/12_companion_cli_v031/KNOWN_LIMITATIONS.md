# Known Limitations — Companion CLI v0.3

## Verification depth (v0.3.2)

Before v0.3.2, `companion verify` hash-checked only the eight top-level
required files and did not recurse into nested component checksum files,
so tampered evidence bytes inside the run verified as ok at this layer
(RT-004). v0.3.2 adds deep verification: every nested `*checksums.txt` is
re-verified, the Aletheia manifest's `bundled_file_sha256` binding is
enforced, and Sentinel `source_run_sha256` records are bound to the source
run file when present. Remaining limits of deep verification:

- recorded provenance hashes whose source file is absent from the run
  folder are recorded-only and cannot be re-verified here
- deep verification proves hash consistency of the recorded run only; it
  does not prove evidence contents are true
- the evidence directory is verified as a closed set: files present there
  without a checksum entry fail verification (evidence added unexpectedly)
- whole-folder fabrication remains possible without signing (unchanged)

## Prior limitations

- one workflow type only (CREATE_EVIDENCE_REASONING_CASE)
- one evidence file only
- one Coordinator run only
- Atlas is read-only
- does not modify Atlas
- does not add Atlas terms
- does not prove truth
- does not verify external reality
- does not call lower components directly
- does not use natural language
- does not use an LLM
- no LLM
- no GUI
- no Android
- no Windows app
- no signing
- no external anchoring
- no queue
- no concurrency

## Scope of the Atlas boundary

Companion CLI v0.3 uses Atlas Registry v0.1 only as a read-only vocabulary
boundary, reached through Coordinator Workflow v0.3. Companion preserves the
Coordinator output (including the Atlas validation report and the byte-for-byte
Atlas registry copy) and mirrors the Atlas validation fields into its own report.
It does not prove that evidence contents are true, that ODIN claims are true, or
that any file or source is authentic.

## A note on ATLAS_VALIDATED

`ATLAS_VALIDATED` is the Coordinator v0.3 Atlas-validation result, not an Atlas
Registry v0.1 vocabulary term. Companion verify confirms
`atlas_validation_status` equals `ATLAS_VALIDATED` as a fixed expected value and
that the registry copy reports `REGISTRY_VERIFIED`; it does not look up
`ATLAS_VALIDATED` in the Atlas status vocabulary, because the frozen Atlas
Registry v0.1 does not (and should not) contain it.

## Subprocess boundary

The default unit tests and selfcheck inject an in-process fake Coordinator runner
and spawn no subprocesses. `subprocess` is imported only by the documented runtime
adapter (`companion_lib/coordinator_runner.py`); real Coordinator integration is a
manual smoke test only and is not part of the freeze gate.

## v0.3.1 repair note

v0.3.1 fixes coordinator request-file hygiene only: the request handed to the
frozen Coordinator CLI is written to a temp directory outside the output tree and
removed, so the final Companion output never carries a stray
`_coordinator_request.json`. The output schema is unchanged (version 0.3.0) and
the verifier still refuses any unknown top-level entry.
