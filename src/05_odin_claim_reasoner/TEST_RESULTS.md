# Test results — ODIN Claim Reasoner v0.1

ODIN Claim Reasoner v0.1 reasons deterministically over already-structured claims:
it validates a claim set, detects direct structural contradictions, preserves
support references, and emits a canonical reasoning report and proof trace.
Standard library only. It proves structural consistency only — never truth. All
commands below were run from a **clean extraction** of `odin_claim_reasoner_v01.zip`.

## Authoritative freeze gate — each command passes individually (clean extraction)

The freeze gate is the explicit list of individual commands (see
RELEASE_COMMANDS.md) plus the static manifest check. No wrapper orchestrator is in
the gate.

| Command | Result |
|---------|--------|
| `python3 -m compileall -q .` | PASS |
| `python3 -m unittest discover -s tests -v` | PASS — 70 tests, ~0.16s |
| `python3 -O -m unittest discover -s tests -v` | PASS — 70 tests |
| `python3 selfcheck.py` | PASS — 8/8 gates |
| `python3 -O selfcheck.py` | PASS — 8/8 gates |
| `python3 -W error::ResourceWarning -m unittest discover -s tests` | PASS |
| `sha256sum -c odin_claim_reasoner_v01.sha256` | OK |
| `python3 verify_release_manifest.py` | PASS — 8/8 static checks, **no subprocesses** |

## Required behaviours (all covered)

| # | Required test | Where |
|---|---------------|-------|
| 1 | Valid claim set accepted | `test_claim_schema.py::test_1_valid_claim_set_accepted` |
| 2 | Missing claims field refused | `::test_2_missing_claims_field_refused` |
| 3 | Extra top-level field refused | `::test_3_extra_top_level_field_refused` |
| 4 | Duplicate claim ID refused | `::test_4_duplicate_claim_id_refused` |
| 5 | Unsafe claim ID refused | `test_validation.py::test_5_unsafe_claim_id_refused` |
| 6 | Unsafe support ID refused | `::test_6_unsafe_support_id_refused` |
| 7 | Empty support list refused | `test_claim_schema.py::test_7_empty_support_list_refused` |
| 8 | Invalid polarity refused | `::test_8_invalid_polarity_refused` |
| 9 | Float object refused | `::test_9_float_object_refused` |
| 10 | Consistent claims produce CONSISTENT | `test_reasoning.py::test_10_consistent_claims_produce_consistent` |
| 11 | Different-object contradiction detected | `::TestContradictions::test_11_different_object_contradiction` |
| 12 | Opposite-polarity contradiction detected | `::test_12_opposite_polarity_contradiction` |
| 13 | Separate subjects accepted | `::test_13_non_contradictory_separate_subjects` |
| 14 | Separate predicates accepted | `::test_14_non_contradictory_separate_predicates` |
| 15 | Proof trace deterministic | `test_proof_trace.py::test_15_proof_trace_generated_deterministically` |
| 16 | Report canonical JSON | `test_reasoning.py::test_16_report_is_canonical_and_deterministic` |
| 17 | Checksums file written | `::test_17_checksums_file_written` |
| 18 | Verify valid output succeeds | `test_verify.py::test_18_verify_valid_output_succeeds` |
| 19 | Mutated claims fails verify | `::test_19_mutated_claims_fails` |
| 20 | Mutated report fails verify | `::test_20_mutated_report_fails` |
| 21 | Mutated proof trace fails verify | `::test_21_mutated_proof_trace_fails` |
| 22 | Missing checksums fails verify | `::test_22_missing_checksums_fails` |
| 23 | Duplicate checksum key fails | `::test_23_duplicate_checksum_key_fails` |
| 24 | Unknown checksum key fails | `::test_24_unknown_checksum_key_fails` |
| 25 | Unknown extra output file fails | `::test_25_unknown_extra_file_fails` |
| 26 | Report contradiction count mismatch fails | `::test_26_report_contradiction_count_mismatch_fails` |
| 27 | Proof trace unknown claim ID fails | `::test_27_proof_trace_unknown_claim_id_fails` |
| 28 | CONTRADICTION_DETECTED is not a truth claim | `test_no_bare_asserts.py::TestHonesty::test_28_...` |
| 29 | Aletheia import creates only integrity/presence claims | `test_aletheia_import.py::test_29_...` |
| 30 | Aletheia import refuses non-VERIFIED_PRESENT | `::test_30_import_refuses_non_verified_present` |
| 31 | Selfcheck passes | `test_selfcheck.py::test_31_selfcheck_passes_in_process` |
| 32 | No bare runtime asserts | `test_no_bare_asserts.py::test_32_no_bare_asserts_in_runtime` |
| 33 | `python -O` unchanged behaviour | full suite + selfcheck pass identically under `-O` |
| 34 | manifest verifier passes, no subprocesses | `test_no_bare_asserts.py::test_34_manifest_verifier_present_static_and_passes` |

Additional coverage: bool/int and null/false object distinction; three-way pairwise
contradictions; different-object precedence over opposite-polarity; order-
independent detection; status-mismatch detection; non-empty output dir refused;
support references preserved on import; import refuses missing fields / unsafe IDs /
bad sha; sha256 validator rejects uppercase and wrong length.

## Manual smoke test (NOT part of the freeze gate)

Building the example `claims.json` and running `reason` then `verify` yields
`reasoning_status = CONSISTENT`, `contradiction_count = 0`, and the ODIN output
verifies. Confirmed end to end, including the optional `import-aletheia` against a
real Aletheia v0.1 `VERIFIED_PRESENT` manifest (produces `evidence.present` +
`evidence.integrity_verified` claims that reason as CONSISTENT).

## Scope

Structured claims → deterministic validation → direct contradiction detection →
canonical proof trace. Nothing else. Not connected to the workflow. No new features
beyond the spec.
