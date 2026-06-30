# Known Limitations — Coordinator Workflow v0.3

- one workflow type only (CREATE_EVIDENCE_REASONING_CASE)
- one evidence file only
- one run at a time
- Atlas is read-only
- does not modify Atlas
- does not add Atlas terms
- does not prove truth
- does not verify external reality
- does not connect Companion yet
- no natural language
- no LLM
- no GUI
- no signing
- no external anchoring
- no queue
- no concurrency

## Scope of the Atlas boundary

Coordinator Workflow v0.3 uses Atlas Registry v0.1 only as a read-only vocabulary
boundary: it confirms that the workflow's vocabulary exists in Atlas, that Atlas
is truth-free, and that Atlas has no forbidden future action types. It does not
prove that evidence contents are true, that ODIN claims are true, or that any
file or source is authentic. The Atlas registry copy gives a deterministic record
of the vocabulary checked; it is not signed or externally anchored.

## Subprocess boundary

The default unit tests use in-process fake component runners and an in-process
Atlas verifier and spawn no subprocesses. No runtime module imports subprocess.
Real frozen-component integration is a documented manual smoke test only and is
not part of the freeze gate.

## v0.3.1 repair note

v0.3.1 wires the nine workflow steps to the frozen lower-component CLIs via
subprocess in one adapter module. The output schema is unchanged (version 0.3.0).
A real integration run against the frozen chain reaches WORKFLOW_COMPLETED and
verifies. The end-to-end Connected Demo through Companion CLI v0.3 is still
blocked, but the blocker is no longer in the Coordinator: Companion v0.3's own
SubprocessCoordinatorRunner writes a `_coordinator_request.json` file at the
companion-output top level that Companion's own verifier then rejects. That is a
Companion v0.3 defect, out of scope for this Coordinator repair; the Coordinator
output itself verifies cleanly. See TEST_RESULTS.md for the exact evidence.

## v0.3.2 repair note

v0.3.2 adds a coordinator compatibility summary at
case_bundle_v02/case_manifest.json carrying the workflow evidence_id (Case Bundle
v0.2 records none), preserving the raw manifest at raw_case_bundle_manifest.json.
The output schema is unchanged (version 0.3.0). With this, the real downstream
chain reaches Unified Manifest SOURCE_VERIFIED and Stack Verifier STACK_VERIFIED.
The end-to-end Connected Demo is still blocked at Stack Selfcheck v0.1, but the
blocker is no longer evidence_id: four early frozen components
(sentinel_core_v022, histor_lite_v012, case_bundle_v011, atlas_red_blue_pack_v01)
predate the documentation convention Stack Selfcheck requires of every component
(README.md + KNOWN_LIMITATIONS.md + RELEASE_COMMANDS.md), so it returns
FAILED_DOCUMENTATION_BOUNDARY. That is out of scope for this Coordinator repair.
