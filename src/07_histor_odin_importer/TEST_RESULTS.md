# Test results — Histor-lite ODIN Importer v0.1

The importer records a verified ODIN Claim Reasoner v0.1 output as a Histor-lite-
style reasoning case, and verifies it. Standard library only. It records structural
reasoning metadata only — never that any claim is true. All commands below were run
from a **clean extraction** of `histor_lite_odin_importer_v01.zip`.

## Authoritative freeze gate — each command passes individually (clean extraction)

The freeze gate is the explicit list of individual commands (see
RELEASE_COMMANDS.md) plus the static manifest check. No wrapper orchestrator is in
the gate; the default unit suite uses an in-process fake ODIN verifier, so the gate
spawns no subprocesses.

| Command | Result |
|---------|--------|
| `python3 -m compileall -q .` | PASS |
| `python3 -m unittest discover -s tests -v` | PASS — 76 tests, ~0.6s |
| `python3 -O -m unittest discover -s tests -v` | PASS — 76 tests |
| `python3 selfcheck.py` | PASS — 8/8 gates |
| `python3 -O selfcheck.py` | PASS — 8/8 gates |
| `python3 -W error::ResourceWarning -m unittest discover -s tests` | PASS |
| `sha256sum -c histor_lite_odin_importer_v01.sha256` | OK |
| `python3 verify_release_manifest.py` | PASS — 10/10 static checks, **no subprocesses** |

## Required behaviours (all covered)

| # | Required test | Where |
|---|---------------|-------|
| 1 | Valid ODIN run accepted | `test_odin_reader.py::test_1_valid_run_accepted` |
| 2 | Missing ODIN root refused | `test_importer.py::test_2_missing_odin_root_refused` |
| 3 | Missing ODIN run folder refused | `::test_3_missing_run_refused` |
| 4 | ODIN verify failure refused | `::test_4_odin_verify_failure_refused` |
| 5 | Missing reasoning report refused | `test_odin_reader.py::test_5_missing_report_refused` |
| 6 | Missing proof trace refused | `::test_6_missing_proof_trace_refused` |
| 7 | Missing claims file refused | `::test_7_missing_claims_refused` |
| 8 | INVALID_INPUT status refused | `test_odin_reader.py::test_8` + `test_importer.py::test_8` |
| 9 | CONSISTENT status accepted | `test_odin_reader.py::test_9` + `test_importer.py::test_9` |
| 10 | CONTRADICTION_DETECTED accepted | `test_odin_reader.py::test_10` + `test_importer.py::test_10` |
| 11 | Invalid case_id refused | `test_validation.py::test_11_invalid_case_id_refused` |
| 12 | Non-empty output dir refused | `test_importer.py::test_12_nonempty_output_dir_refused` |
| 13 | Valid import writes all files | `::test_13_valid_import_writes_all_files` |
| 14 | Copied ODIN files not rewritten | `::test_14_copies_not_rewritten` |
| 15 | Summary canonical | `::test_15_summary_is_canonical` |
| 16-18 | Copies canonical | `::test_16_17_18_copies_are_canonical` |
| 19 | Replay report written | `::test_19_replay_report_written` |
| 20 | Checksums written | `::test_20_checksums_written` |
| 21 | Verify valid case succeeds | `test_verify.py::test_21_verify_valid_case_succeeds` (+ contradiction) |
| 22 | Mutated summary fails | `::test_22_mutated_summary_fails` |
| 23 | Mutated report copy fails | `::test_23_mutated_report_copy_fails` |
| 24 | Mutated proof trace copy fails | `::test_24_mutated_trace_copy_fails` |
| 25 | Mutated claims copy fails | `::test_25_mutated_claims_copy_fails` |
| 26 | Mutated replay report fails | `::test_26_mutated_replay_report_fails` |
| 27 | Missing checksums fails | `::test_27_missing_checksums_fails` |
| 28 | Duplicate checksum key fails | `::test_28_duplicate_checksum_key_fails` |
| 29 | Unknown checksum key fails | `::test_29_unknown_checksum_key_fails` |
| 30 | Malformed checksum digest fails | `::test_30_malformed_digest_fails` |
| 31 | Uppercase checksum digest fails | `::test_31_uppercase_digest_fails` |
| 32 | Unknown extra output file fails | `::test_32_unknown_extra_file_fails` |
| 33 | Case ID mismatch fails | `::test_33_case_id_mismatch_fails` |
| 34 | Reasoning status mismatch fails | `::test_34_reasoning_status_mismatch_fails` |
| 35 | Claim count mismatch fails | `::test_35_claim_count_mismatch_fails` |
| 36 | Contradiction count mismatch fails | `::test_36_contradiction_count_mismatch_fails` |
| 37 | Proof step count mismatch fails | `::test_37_proof_step_count_mismatch_fails` |
| 38 | Import status mismatch fails | `::test_38_import_status_mismatch_fails` |
| 39 | INVALID_INPUT injected after import fails | `::test_39_invalid_input_injected_fails` |
| 40 | Truth-like claim in summary fails | `::test_40_truth_like_claim_in_summary_fails` |
| 41 | Truth-like claim in replay report fails | `::test_41_truth_like_claim_in_replay_report_fails` |
| 42 | `python -O` unchanged behaviour | full suite + selfcheck pass identically under `-O` |
| 43 | Selfcheck passes | `test_selfcheck.py::test_43_selfcheck_passes_in_process` |
| 44 | No bare runtime asserts | `test_no_bare_asserts.py::test_44_no_bare_asserts_in_runtime` |
| 45 | manifest verifier passes, no subprocesses | `test_no_bare_asserts.py::test_45_manifest_verifier_present_static_and_passes` |

Additional coverage: CLI-level exit codes (0 success, 2 path error, 1 ODIN verify
failure, 1 INVALID_INPUT) with an injected fake verifier; reasoning status and all
counts preserved through import; verbatim source bytes captured by the reader;
malformed report refused; other non-importable statuses refused; missing case dir
fails.

## Manual integration smoke test (NOT part of the freeze gate)

Against the real frozen ODIN v0.1:
- **Consistent run** -> `histor_odin.py import-reasoning` produced `import_status =
  IMPORTED_VERIFIED_ODIN`, `source_reasoning_status = CONSISTENT`, case_id /
  claim_count / contradiction_count / proof_step_count all preserved, the three ODIN
  copies byte-identical to the source files, `truth_claim: none` in the replay
  report; `histor_odin.py verify-case` passed.
- **Contradiction run** (two claims, same predicate, AFFIRMED + DENIED) -> ODIN
  yielded `reasoning_status = CONTRADICTION_DETECTED`; the importer produced
  `import_status = IMPORTED_VERIFIED_ODIN` with the contradiction status preserved;
  `verify-case` passed — confirming a structural contradiction is a valid reasoning
  outcome, not a failed import.

## Scope

verified ODIN structural reasoning output -> Histor-lite-style reasoning case record
-> verified imported reasoning case. Nothing else. Not connected to Aletheia,
Coordinator, or Companion. No new features beyond the spec.
