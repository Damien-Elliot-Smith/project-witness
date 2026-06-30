# Test results — Evidence Reasoning Demo v0.1

The demo drives the local chain (Aletheia -> Bridge -> ODIN) from one evidence file
to a verified demo report. Standard library only. It proves the chain executes and
verifies — never that the evidence contents are true. All commands below were run
from a **clean extraction** of `evidence_reasoning_demo_v01.zip`.

## Authoritative freeze gate — each command passes individually (clean extraction)

The freeze gate is the explicit list of individual commands (see
RELEASE_COMMANDS.md) plus the static manifest check. No wrapper orchestrator is in
the gate; the default unit suite uses an in-process fake component runner, so the
gate spawns no subprocesses.

| Command | Result |
|---------|--------|
| `python3 -m compileall -q .` | PASS |
| `python3 -m unittest discover -s tests -v` | PASS — 68 tests, ~0.24s |
| `python3 -O -m unittest discover -s tests -v` | PASS — 68 tests |
| `python3 selfcheck.py` | PASS — 8/8 gates |
| `python3 -O selfcheck.py` | PASS — 8/8 gates |
| `python3 -W error::ResourceWarning -m unittest discover -s tests` | PASS |
| `sha256sum -c evidence_reasoning_demo_v01.sha256` | OK |
| `python3 verify_release_manifest.py` | PASS — 9/9 static checks, **no subprocesses** |

## Required behaviours (all covered)

| # | Required test | Where |
|---|---------------|-------|
| 1 | Valid IDs accepted | `test_validation.py::test_1_valid_ids_accepted` |
| 2 | Unsafe case ID refused | `::test_2_unsafe_case_id_refused` |
| 3 | Unsafe evidence ID refused | `::test_3_unsafe_evidence_id_refused` |
| 4 | Missing evidence file refused | `::test_4_missing_evidence_file_refused` |
| 5 | Directory evidence source refused | `::test_5_directory_evidence_source_refused` |
| 6 | Symlink evidence source refused | `::test_6_symlink_evidence_source_refused` |
| 7 | Missing Aletheia root refused | `test_runner.py::test_7_missing_aletheia_root_refused` |
| 8 | Missing Bridge root refused | `::test_8_missing_bridge_root_refused` |
| 9 | Missing ODIN root refused | `::test_9_missing_odin_root_refused` |
| 10 | Non-empty output dir refused | `::test_10_nonempty_output_dir_refused` |
| 11 | Aletheia bundle failure stops later | `::test_11_aletheia_bundle_failure_stops_later` |
| 12 | Aletheia verify failure stops later | `::test_12_aletheia_verify_failure_stops_later` |
| 13 | Bridge convert failure stops ODIN | `::test_13_bridge_convert_failure_stops_odin` |
| 14 | Bridge verify failure stops ODIN | `::test_14_bridge_verify_failure_stops_odin` |
| 15 | ODIN reason failure stops verify | `::test_15_odin_reason_failure_stops_verify` |
| 16 | ODIN verify failure -> failed status | `::test_16_odin_verify_failure_produces_failed_status` |
| 17 | Successful run writes all files | `::test_17_successful_run_writes_all_files` |
| 18 | demo_report.json canonical | `test_report.py::test_18_report_is_canonical` |
| 19 | demo_steps.json canonical | `test_steps.py::test_19_steps_canonical_and_deterministic` |
| 20 | demo_checksums.txt written | `test_checksums.py::test_20_format_roundtrip` + runner writes it |
| 21 | Verify valid demo output succeeds | `test_verify.py::test_21_verify_valid_output_succeeds` |
| 22 | Mutated demo_report.json fails | `::test_22_mutated_demo_report_fails` |
| 23 | Mutated demo_steps.json fails | `::test_23_mutated_demo_steps_fails` |
| 24 | Mutated Aletheia manifest hash fails | `::test_24_mutated_aletheia_manifest_hash_fails` |
| 25 | Mutated Bridge report hash fails | `::test_25_mutated_bridge_report_hash_fails` |
| 26 | Mutated ODIN reasoning report hash fails | `::test_26_mutated_odin_report_hash_fails` |
| 27 | Missing checksums fails | `::test_27_missing_checksums_fails` |
| 28 | Duplicate checksum key fails | `::test_28_duplicate_checksum_key_fails` |
| 29 | Unknown checksum key fails | `::test_29_unknown_checksum_key_fails` |
| 30 | Unknown extra top-level file fails | `::test_30_unknown_extra_top_level_file_fails` |
| 31 | Case ID mismatch fails | `::test_31_case_id_mismatch_fails` |
| 32 | Evidence ID mismatch fails | `::test_32_evidence_id_mismatch_fails` |
| 33 | Truth-like generated claim fails | `::test_33_truth_like_generated_claim_fails` |
| 34 | Non-CONSISTENT ODIN status fails | `::test_34_non_consistent_odin_status_fails` |
| 35 | Non-DEMO_COMPLETED status fails | `::test_35_non_completed_demo_status_fails` |
| 36 | `python -O` unchanged behaviour | full suite + selfcheck pass identically under `-O` |
| 37 | Selfcheck passes | `test_selfcheck.py::test_37_selfcheck_passes_in_process` |
| 38 | No bare runtime asserts | `test_no_bare_asserts.py::test_38_no_bare_asserts_in_runtime` |
| 39 | manifest verifier passes, no subprocesses | `test_no_bare_asserts.py::test_39_manifest_verifier_present_static_and_passes` |

Additional coverage: CLI-level exit codes (0 success, 2 validation/path error, 1
step failure) with an injected fake runner; report/steps field and status checks;
all six steps in fixed order; failure marks FAILED then SKIPPED_AFTER_FAILURE;
upstream truth-claim rejected at verify; missing subfolder fails; missing run dir
fails; checksums uppercase-digest and blank-line handling.

## Manual integration smoke test (NOT part of the freeze gate)

Against the real frozen Aletheia v0.1, Bridge v0.1, and ODIN v0.1: a real evidence
file produced `demo_status = DEMO_COMPLETED`, `aletheia_status = VERIFIED_PRESENT`,
`bridge_status = CONVERTED`, `odin_reasoning_status = CONSISTENT`,
`generated_claims = evidence.present, evidence.integrity_verified`, all three
component outputs preserved in their subfolders, and `demo.py verify` passed.

## Scope

local evidence file -> Aletheia bundle -> Bridge claims -> ODIN reasoning ->
verified demo report. Nothing else. Not connected to Companion or Coordinator. No
new features beyond the spec.
