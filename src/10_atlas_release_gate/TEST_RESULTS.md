# Test Results — Atlas Release Gate v0.1

All authoritative release commands pass from a clean extraction. The unit suite
contains 75 tests across the eleven test modules; the selfcheck runs
eight in-process gates. The default suite is fully in-process: it injects a fake
Atlas runner / fake executor and spawns no subprocesses.

## Authoritative commands (all pass)

    python3 -m compileall -q .                                  OK
    python3 -m unittest discover -s tests -v                    OK (75 tests)
    python3 -O -m unittest discover -s tests -v                 OK (75 tests)
    python3 selfcheck.py                                        OK (8 gates)
    python3 -O selfcheck.py                                     OK (8 gates)
    python3 -W error::ResourceWarning -m unittest discover ...  OK (75 tests)
    sha256sum -c atlas_release_gate_v01.sha256                  OK
    python3 verify_release_manifest.py                          OK (no subprocesses)

## Coverage of required scenarios

The required test scenarios are covered as follows:

- Valid release accepted; missing root / required file / registry refused
  (test_validation.py).
- Registry-verify, export, and export-verify failures refused; fake export
  produces all three export files (test_runner.py).
- Real-Atlas subprocess adapter builds the correct frozen Atlas v0.1 argv
  shapes, asserted WITHOUT launching real Atlas via an injected executor
  (test_runner.py, TestSubprocessRunnerArgv):
    * verify        -> atlas.py verify --registry registry/atlas_registry.json
    * export        -> atlas.py export --registry registry/atlas_registry.json --out <export_dir>
    * verify-export -> atlas.py verify-export --export <export_dir>
- Missing documentation and missing honesty boundary refused; honest docs do
  not false-positive (test_documentation_checks.py).
- Honesty check accepts the real frozen Atlas v0.1 wording (read-only
  registry / records vocabulary / does not run workflows / does not prove
  truth / does not call components / does not decide truth) WITHOUT requiring
  "does not modify the registry"; docs lacking any read-only / no-workflow /
  no-truth boundary fail the honesty check (test_documentation_checks.py).
- Affirmative Coordinator / Companion / workflow / LLM / signing claims refused;
  honest limitation sentences produce no false positives (test_feature_checks.py).
- Forbidden-feature scanner reports only affirmative support claims:
  genuine frozen Atlas wording (workflow types; Coordinator/Companion as
  listed components; WRITE_FILE/DELETE_FILE/SHELL_COMMAND/NETWORK_CALL as
  refused out-of-roadmap actions; ontology expansion / signing / anchoring
  out of scope) produces no false positives, while all ten affirmative
  claims (integrates/connects/runs/uses/supports/provides ...) are caught
  (test_feature_checks.py).
- Fixed step order and failure short-circuit enforced (test_steps.py).
- Report and steps are canonical; all output files written (test_report.py).
- Checksums written; duplicate / unknown / missing / malformed / uppercase /
  single-space-separator all rejected (test_checksums.py).
- Valid output verifies; mutated report / steps / export-copy / export-summary,
  missing checksums, unknown top-level or export file, wrong step order, passed
  gate with a skipped step, and non-passed / non-verified statuses all fail
  verify (test_verify.py).
- Truth-like claims ("claims are true", "files are authentic") in the report
  are rejected; negated honesty statements are allowed (test_honesty.py).
- selfcheck passes (test_selfcheck.py).
- No bare runtime asserts; manifest checker passes and imports no subprocess
  (test_no_bare_asserts.py).

## Manual real-subprocess integration (not part of the freeze gate)

The repaired real-subprocess path was exercised end to end against the GENUINE frozen Atlas Registry v0.1 extraction via its own
atlas.py (real subprocess):

    python3 atlas_release_gate.py check --atlas-root <atlas_registry_v01> --out <out>
    python3 atlas_release_gate.py verify --run <out>

Result:

    release_gate_status = RELEASE_GATE_PASSED
    registry_status     = REGISTRY_VERIFIED
    export_status       = EXPORT_VERIFIED
    verify_ok           = true

Run the same two commands against a genuine frozen Atlas Registry v0.1
extraction to confirm in your environment.

## Determinism and boundaries confirmed

- Two independent check runs produce byte-identical canonical output.
- `python3 -O` does not change behaviour (no runtime asserts exist).
- The default unit tests and selfcheck spawn no subprocesses; the only module
  permitted to import subprocess is the Atlas runner, used solely by the manual
  smoke test.
- The release-gate report and steps carry only structural statements; the
  verifier rejects any truth-like claim.
