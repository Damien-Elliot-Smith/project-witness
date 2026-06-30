# Test results — Case Bundle v0.2

Case Bundle v0.2 combines three already-verified Histor-lite case records (Sentinel
action, Aletheia evidence, ODIN reasoning) into one portable, self-checked Project
Witness bundle. Standard library only. It packages verified records only and never
claims the evidence contents or any ODIN claim is true. All commands below were run
from a **clean extraction** of `case_bundle_v02.zip`.

## Authoritative freeze gate — each command passes individually (clean extraction)

The freeze gate is the explicit list of individual commands (see
RELEASE_COMMANDS.md) plus the static manifest check. No subprocess orchestrator is
in the gate; the default unit suite uses in-process verifiers and synthesized case
folders, so the gate spawns no subprocesses.

| Command | Result |
|---------|--------|
| `python3 -m compileall -q .` | PASS |
| `python3 -m unittest discover -s tests -v` | PASS — 80 tests |
| `python3 -O -m unittest discover -s tests -v` | PASS — 80 tests |
| `python3 selfcheck.py` | PASS — 8/8 gates |
| `python3 -O selfcheck.py` | PASS — 8/8 gates |
| `python3 -W error::ResourceWarning -m unittest discover -s tests` | PASS |
| `sha256sum -c case_bundle_v02.sha256` | OK |
| `python3 verify_release_manifest.py` | PASS — 12/12 static checks, **no subprocesses** |

## Required behaviours (spec tests 1–48, all covered)

| # | Required test | Where |
|---|---------------|-------|
| 1 | Valid Sentinel case accepted | `test_input_verifiers::test_1_valid_sentinel_accepted` |
| 2 | Valid Aletheia case accepted | `::test_2_valid_aletheia_accepted` |
| 3 | Valid ODIN case accepted | `::test_3_valid_odin_accepted` |
| 4 | Missing Sentinel case refused | `test_builder::test_4_missing_sentinel_case_refused` |
| 5 | Missing Aletheia case refused | `::test_5_missing_aletheia_case_refused` |
| 6 | Missing ODIN case refused | `::test_6_missing_odin_case_refused` |
| 7 | Sentinel verify failure refused | `::test_7_sentinel_verify_failure_refused` |
| 8 | Aletheia verify failure refused | `::test_8_aletheia_verify_failure_refused` |
| 9 | ODIN verify failure refused | `::test_9_odin_verify_failure_refused` |
| 10 | Case ID mismatch refused | `::test_10_case_id_mismatch_refused` |
| 11 | Non-empty output dir refused | `::test_11_nonempty_output_dir_refused` |
| 12 | Valid build writes all files/folders | `::test_12_valid_build_writes_all` |
| 13 | Subcase files copied byte-identically | `::test_13_subcase_files_copied_byte_identically` |
| 14 | case_manifest.json canonical | `::test_14_manifest_is_canonical` |
| 15 | bundle_checksums.txt written (14 lines) | `::test_15_checksums_written` |
| 16 | Verify valid bundle succeeds | `test_verify::test_16_verify_valid_bundle_succeeds` |
| 17 | Mutated manifest fails | `::test_17_mutated_manifest_fails` |
| 18 | Mutated Sentinel summary fails | `::test_18_mutated_sentinel_summary_fails` |
| 19 | Mutated Sentinel replay fails | `::test_19_mutated_sentinel_replay_fails` |
| 20 | Mutated Aletheia summary fails | `::test_20_mutated_aletheia_summary_fails` |
| 21 | Mutated Aletheia manifest copy fails | `::test_21_mutated_aletheia_manifest_copy_fails` |
| 22 | Mutated Aletheia replay fails | `::test_22_mutated_aletheia_replay_fails` |
| 23 | Mutated ODIN summary fails | `::test_23_mutated_odin_summary_fails` |
| 24 | Mutated ODIN report copy fails | `::test_24_mutated_odin_report_copy_fails` |
| 25 | Mutated ODIN proof trace copy fails | `::test_25_mutated_odin_trace_copy_fails` |
| 26 | Mutated ODIN claims copy fails | `::test_26_mutated_odin_claims_copy_fails` |
| 27 | Mutated ODIN replay fails | `::test_27_mutated_odin_replay_fails` |
| 28 | Missing bundle checksums fails | `::test_28_missing_bundle_checksums_fails` |
| 29 | Duplicate checksum key fails | `::test_29_duplicate_checksum_key_fails` |
| 30 | Unknown checksum key fails | `::test_30_unknown_checksum_key_fails` |
| 31 | Malformed digest fails | `::test_31_malformed_digest_fails` |
| 32 | Uppercase digest fails | `::test_32_uppercase_digest_fails` |
| 33 | Unknown extra top-level file fails | `::test_33_unknown_top_level_file_fails` |
| 34 | Unknown extra subfolder file fails | `::test_34_unknown_subfolder_file_fails` |
| 35 | Internal Sentinel checksums mismatch fails | `::test_35_internal_sentinel_checksum_mismatch_fails` |
| 36 | Internal Aletheia checksums mismatch fails | `::test_36_internal_aletheia_checksum_mismatch_fails` |
| 37 | Internal ODIN checksums mismatch fails | `::test_37_internal_odin_checksum_mismatch_fails` |
| 38 | Bundle case ID mismatch fails | `::test_38_bundle_case_id_mismatch_fails` |
| 39 | Aletheia non-VERIFIED_PRESENT fails | `::test_39_aletheia_status_mutated_fails` |
| 40 | ODIN CONSISTENT accepted | `::test_40_odin_consistent_accepted` |
| 41 | ODIN CONTRADICTION_DETECTED accepted | `::test_41_odin_contradiction_accepted` |
| 42 | ODIN INVALID_INPUT fails | `::test_42_odin_invalid_input_fails` |
| 43 | Truth-like claim in manifest fails | `::test_43_truth_like_claim_in_manifest_fails` |
| 44 | Truth-like claim in replay fails | `::test_44_truth_like_claim_in_replay_fails` |
| 45 | `python -O` unchanged behaviour | full suite + selfcheck pass identically under `-O` |
| 46 | Selfcheck passes | `test_selfcheck::test_46_selfcheck_passes_in_process` |
| 47 | No bare runtime asserts | `test_no_bare_asserts::test_47_no_bare_asserts_in_runtime` |
| 48 | manifest verifier passes, no subprocesses | `test_no_bare_asserts::test_48_manifest_verifier_present_static_and_passes` |

Additional coverage: ODIN contradiction accepted at the verifier boundary; ODIN
INVALID_INPUT refused at the input-verifier boundary; internal checksum mismatch on
each subcase (with the bundle checksums resynced) still caught; CLI build exit codes
(0 success, 2 path error, 1 case-id mismatch); missing bundle dir / missing
subfolder; truth-scan allows honest negated disclaimers but catches affirmative
truth claims; selfcheck and manifest verifier both AST-checked to import no
`subprocess`.

## Repair recorded this build

**R1 — truth-scan false positive against the bundle's own disclaimers.** The first
real end-to-end build self-verify failed `TRUTH_CLAIM` because the forbidden-token
list contained bare `"are true"`, which collides with the manifest's honest
disclaimer "does not prove evidence contents are true". Fixed by narrowing the
tokens to affirmative predicate forms and stripping known disclaimer sentences
before scanning. See REPAIR_LEDGER.md.

## Manual integration smoke test (NOT part of the freeze gate)

Built from the real frozen chain — Sentinel `PASS_STRICT` case (Histor-lite v0.1.2,
derived `case_id = case_83cd1ba75eddfa05`), a matching Aletheia evidence case
(`VERIFIED_PRESENT`), and a matching ODIN reasoning case sharing that case_id:
- `build` -> `bundle_status = BUNDLED_VERIFIED_CASE`; case_id preserved across all
  three records; every subcase file byte-identical to its source.
- `verify` -> passed.
- A second run with a real `CONTRADICTION_DETECTED` ODIN case also built and
  verified successfully, confirming a structural contradiction is a valid
  packageable outcome.

## Scope

verified Sentinel case + verified Aletheia evidence case + verified ODIN reasoning
case -> one unified portable Project Witness case bundle -> verified bundle. Nothing
else. No Coordinator/Companion integration, no Atlas, no LLM, no signing, no
anchoring.
