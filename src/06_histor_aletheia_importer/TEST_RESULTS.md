# Test results — Histor-lite Aletheia Importer v0.1

The importer records a verified Aletheia Evidence Bundle v0.1 as a Histor-lite-style
evidence case, and verifies it. Standard library only. It records integrity metadata
only — never that the evidence contents are true. All commands below were run from a
**clean extraction** of `histor_lite_aletheia_importer_v01.zip`.

## Authoritative freeze gate — each command passes individually (clean extraction)

The freeze gate is the explicit list of individual commands (see
RELEASE_COMMANDS.md) plus the static manifest check. No wrapper orchestrator is in
the gate; the default unit suite uses an in-process fake Aletheia verifier, so the
gate spawns no subprocesses.

| Command | Result |
|---------|--------|
| `python3 -m compileall -q .` | PASS |
| `python3 -m unittest discover -s tests -v` | PASS — 68 tests, ~0.28s |
| `python3 -O -m unittest discover -s tests -v` | PASS — 68 tests |
| `python3 selfcheck.py` | PASS — 8/8 gates |
| `python3 -O selfcheck.py` | PASS — 8/8 gates |
| `python3 -W error::ResourceWarning -m unittest discover -s tests` | PASS |
| `sha256sum -c histor_lite_aletheia_importer_v01.sha256` | OK |
| `python3 verify_release_manifest.py` | PASS — 10/10 static checks, **no subprocesses** |

## Required behaviours (all covered)

| # | Required test | Where |
|---|---------------|-------|
| 1 | Valid Aletheia manifest accepted | `test_aletheia_reader.py::test_1_valid_manifest_accepted` |
| 2 | Missing Aletheia root refused | `test_importer.py::test_2_missing_aletheia_root_refused` |
| 3 | Missing bundle folder refused | `::test_3_missing_bundle_refused` |
| 4 | Aletheia verify failure refused | `::test_4_aletheia_verify_failure_refused` |
| 5 | Non-VERIFIED_PRESENT status refused | `::test_5_non_verified_present_refused` + reader test |
| 6 | Missing manifest field refused | `::test_6_missing_manifest_field_refused` |
| 7 | Invalid case_id refused | `test_validation.py::test_7_invalid_case_id_refused` |
| 8 | Invalid evidence_id refused | `::test_8_invalid_evidence_id_refused` |
| 9 | Non-empty output dir refused | `test_importer.py::test_9_nonempty_output_dir_refused` |
| 10 | Valid import writes all files | `::test_10_valid_import_writes_all_files` |
| 11 | Evidence file not copied | `::test_11_evidence_file_not_copied` |
| 12 | Summary canonical | `::test_12_summary_is_canonical` |
| 13 | Manifest copy canonical | `::test_13_manifest_copy_is_canonical` |
| 14 | Replay report written | `::test_14_replay_report_written` |
| 15 | Checksums written | `::test_15_checksums_written` |
| 16 | Verify valid case succeeds | `test_verify.py::test_16_verify_valid_case_succeeds` |
| 17 | Mutated summary fails | `::test_17_mutated_summary_fails` |
| 18 | Mutated manifest copy fails | `::test_18_mutated_manifest_copy_fails` |
| 19 | Mutated replay report fails | `::test_19_mutated_replay_report_fails` |
| 20 | Missing checksums fails | `::test_20_missing_checksums_fails` |
| 21 | Duplicate checksum key fails | `::test_21_duplicate_checksum_key_fails` |
| 22 | Unknown checksum key fails | `::test_22_unknown_checksum_key_fails` |
| 23 | Malformed checksum digest fails | `::test_23_malformed_digest_fails` |
| 24 | Uppercase checksum digest fails | `::test_24_uppercase_digest_fails` |
| 25 | Unknown extra output file fails | `::test_25_unknown_extra_file_fails` |
| 26 | Case ID mismatch fails | `::test_26_case_id_mismatch_fails` |
| 27 | Evidence ID mismatch fails | `::test_27_evidence_id_mismatch_fails` |
| 28 | Source status mismatch fails | `::test_28_source_status_mismatch_fails` |
| 29 | Source file SHA mismatch fails | `::test_29_source_file_sha_mismatch_fails` |
| 30 | Bundled file SHA mismatch fails | `::test_30_bundled_file_sha_mismatch_fails` |
| 31 | Truth-like claim in summary fails | `::test_31_truth_like_claim_in_summary_fails` |
| 32 | Truth-like claim in replay report fails | `::test_32_truth_like_claim_in_replay_report_fails` |
| 33 | `python -O` unchanged behaviour | full suite + selfcheck pass identically under `-O` |
| 34 | Selfcheck passes | `test_selfcheck.py::test_34_selfcheck_passes_in_process` |
| 35 | No bare runtime asserts | `test_no_bare_asserts.py::test_35_no_bare_asserts_in_runtime` |
| 36 | manifest verifier passes, no subprocesses | `test_no_bare_asserts.py::test_36_manifest_verifier_present_static_and_passes` |

Additional coverage: CLI-level exit codes (0 success, 2 path error, 1 Aletheia
verify failure) with an injected fake verifier; status and both SHAs preserved
through import; replay report contains both SHAs and the disclaimer; import_status
mismatch fails; missing case dir fails; sha256 validator rejects uppercase / wrong
length; malformed/uppercase digests and blank-line handling in checksums.

## Manual integration smoke test (NOT part of the freeze gate)

Against the real frozen Aletheia v0.1: built an evidence bundle;
`histor_aletheia.py import-evidence` produced `import_status =
IMPORTED_VERIFIED_ALETHEIA`, `source_evidence_status = VERIFIED_PRESENT`, case_id /
evidence_id / source_file_sha256 / bundled_file_sha256 all preserved, exactly the
four case files written with `truth_claim: none` in the replay report;
`histor_aletheia.py verify-case` passed.

## Scope

verified Aletheia evidence metadata -> Histor-lite-style evidence case record ->
verified imported case. Nothing else. Not connected to ODIN, Coordinator, or
Companion. No new features beyond the spec.
