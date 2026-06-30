# Test results — Aletheia -> ODIN Bridge v0.1

The bridge converts a verified Aletheia Evidence Bundle v0.1 into an ODIN Claim
Reasoner v0.1 claim set (integrity/presence claims only), writes a deterministic
output folder, and verifies it. Standard library only. It converts integrity
metadata only — never truth of contents. All commands below were run from a **clean
extraction** of `aletheia_odin_bridge_v01.zip`.

## Authoritative freeze gate — each command passes individually (clean extraction)

The freeze gate is the explicit list of individual commands (see
RELEASE_COMMANDS.md) plus the static manifest check. No wrapper orchestrator is in
the gate; the default unit suite uses in-process fakes for the Aletheia/ODIN
boundaries, so the gate spawns no subprocesses.

| Command | Result |
|---------|--------|
| `python3 -m compileall -q .` | PASS |
| `python3 -m unittest discover -s tests -v` | PASS — 62 tests, ~0.3s |
| `python3 -O -m unittest discover -s tests -v` | PASS — 62 tests |
| `python3 selfcheck.py` | PASS — 8/8 gates |
| `python3 -O selfcheck.py` | PASS — 8/8 gates |
| `python3 -W error::ResourceWarning -m unittest discover -s tests` | PASS |
| `sha256sum -c aletheia_odin_bridge_v01.sha256` | OK |
| `python3 verify_release_manifest.py` | PASS — 8/8 static checks, **no subprocesses** |

## Required behaviours (all covered)

| # | Required test | Where |
|---|---------------|-------|
| 1 | Valid Aletheia manifest accepted | `test_manifest_reading.py::test_1_valid_manifest_accepted` |
| 2 | Missing manifest field refused | `::test_2_missing_field_refused` |
| 3 | Extra manifest field (subset validation boundary) | `::test_3_extra_field_tolerated_by_subset_validation` |
| 4 | Non-VERIFIED_PRESENT manifest refused | `::test_4_non_verified_present_refused` + `test_convert.py::test_4_...` |
| 5 | Missing Aletheia bundle refused | `test_convert.py::test_5_missing_bundle_refused` |
| 6 | Aletheia verify failure refused | `::test_6_aletheia_verify_failure_refused` |
| 7 | Missing Aletheia root refused | `::test_7_missing_aletheia_root_refused` |
| 8 | Missing ODIN root refused | `::test_8_missing_odin_root_refused` |
| 9 | Claims generated canonically | `test_claim_builder.py::test_9_claims_generated_canonically` |
| 10 | Exactly two claims generated | `::test_10_exactly_two_claims` |
| 11 | Only evidence.present + evidence.integrity_verified | `::test_11_only_allowed_predicates` |
| 12 | Support preserves evidence ID | `::test_12_support_preserves_evidence_id` |
| 13 | Support SHA equals bundled SHA | `::test_13_support_sha_equals_bundled_sha` |
| 14 | No truth predicates generated | `::test_14_no_truth_predicates` + `test_honesty.py` |
| 15 | ODIN validation failure refused | `test_convert.py::test_15_odin_validation_failure_refused` |
| 16 | Valid conversion writes all files | `::test_16_valid_conversion_writes_all_files` |
| 17 | bridge_report.json canonical | `::test_17_bridge_report_canonical` |
| 18 | bridge_checksums.txt written | `::test_18_checksums_written` |
| 19 | Verify valid bridge output succeeds | `test_verify.py::test_19_verify_valid_output_succeeds` |
| 20 | Mutated odin_claims.json fails | `::test_20_mutated_claims_fails` |
| 21 | Mutated bridge_report.json fails | `::test_21_mutated_report_fails` |
| 22 | Mutated aletheia_manifest_copy.json fails | `::test_22_mutated_manifest_copy_fails` |
| 23 | Missing checksums fails | `::test_23_missing_checksums_fails` |
| 24 | Duplicate checksum key fails | `::test_24_duplicate_checksum_key_fails` |
| 25 | Unknown checksum key fails | `::test_25_unknown_checksum_key_fails` |
| 26 | Unknown extra output file fails | `::test_26_unknown_extra_file_fails` |
| 27 | Report claim count mismatch fails | `::test_27_report_claim_count_mismatch_fails` |
| 28 | Report case ID mismatch fails | `::test_28_report_case_id_mismatch_fails` |
| 29 | Claim support SHA mismatch fails | `::test_29_support_sha_mismatch_fails` |
| 30 | Truth-like predicate injected fails | `::test_30_truth_predicate_injected_fails` |
| 31 | Non-canonical JSON fails | `::test_31_non_canonical_json_fails` |
| 32 | Selfcheck passes | `test_selfcheck.py::test_32_selfcheck_passes_in_process` |
| 33 | No bare runtime asserts | `test_no_bare_asserts.py::test_33_no_bare_asserts_in_runtime` |
| 34 | `python -O` unchanged behaviour | full suite + selfcheck pass identically under `-O` |
| 35 | manifest verifier passes, no subprocesses | `test_no_bare_asserts.py::test_35_manifest_verifier_present_static_and_passes` |

Additional coverage: CLI-level exit codes (0 success, 2 path error, 1
Aletheia/ODIN failure) with injected fakes; ODIN validation SKIPPED when no
`--odin-root`; no evidence file copied; non-empty output dir refused; manifest copy
matches source; evidence_id mismatch fails; missing run dir fails; the claim-builder
guard rejects forbidden predicates directly.

## Manual integration smoke test (NOT part of the freeze gate)

Against the real frozen Aletheia v0.1 and ODIN v0.1: built an evidence bundle;
`bridge.py convert` produced `bridge_status = CONVERTED` with
`odin_validation_status = VALID` and generated exactly `evidence.present` +
`evidence.integrity_verified`; `bridge.py verify` passed; ODIN `reason` over the
generated claims returned `reasoning_status = CONSISTENT`; ODIN `verify` passed.

## Scope

Aletheia evidence manifest -> ODIN integrity/presence claims -> bridge report.
Nothing else. Not connected to the workflow. No new features beyond the spec.
