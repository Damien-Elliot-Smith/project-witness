# Test results — Aletheia Evidence Bundle v0.1

Aletheia Evidence Bundle v0.1 bundles one local file as evidence and verifies the
bundle's integrity. Standard library only. It proves preservation/hash integrity
only — never truth of contents. All commands below were run from a **clean
extraction** of `aletheia_evidence_bundle_v01.zip`.

## Authoritative freeze gate — each command passes individually (clean extraction)

The freeze gate is the explicit list of individual commands (see
RELEASE_COMMANDS.md) plus the static manifest check. No wrapper orchestrator is in
the gate.

| Command | Result |
|---------|--------|
| `python3 -m compileall -q .` | PASS |
| `python3 -m unittest discover -s tests -v` | PASS — 55 tests, ~0.4s |
| `python3 -O -m unittest discover -s tests -v` | PASS — 55 tests |
| `python3 selfcheck.py` | PASS — 8/8 gates |
| `python3 -O selfcheck.py` | PASS — 8/8 gates |
| `python3 -W error::ResourceWarning -m unittest discover -s tests` | PASS |
| `sha256sum -c aletheia_evidence_bundle_v01.sha256` | OK |
| `python3 verify_release_manifest.py` | PASS — 7/7 static checks, **no subprocesses** |

## Required behaviours (all covered)

| # | Required test | Where |
|---|---------------|-------|
| 1 | Valid case ID accepted | `test_validation.py::test_1_valid_case_id_accepted` |
| 2 | Unsafe case ID refused | `::test_2_unsafe_case_id_refused` |
| 3 | Valid evidence ID accepted | `::test_3_valid_evidence_id_accepted` |
| 4 | Unsafe evidence ID refused | `::test_4_unsafe_evidence_id_refused` |
| 5 | Missing source file refused | `::test_5_missing_source_refused` |
| 6 | Directory source refused | `::test_6_directory_source_refused` |
| 7 | Symlink source refused | `::test_7_symlink_source_refused` |
| 8 | Oversized source refused | `::test_8_oversized_source_refused` |
| 9 | Valid file bundles successfully | `test_build_bundle.py::test_9_valid_file_bundles_successfully` |
| 10 | Bundle copies file into evidence/evidence_001.bin | `::test_10_bundle_copies_file_into_evidence_bin` |
| 11 | Manifest is canonical JSON | `::test_11_manifest_is_canonical_json` |
| 12 | Checksums file written | `::test_12_checksums_file_written` |
| 13 | Verify valid bundle succeeds | `test_verify_bundle.py::test_13_verify_valid_bundle_succeeds` |
| 14 | Mutated evidence file fails verify | `::test_14_mutated_evidence_file_fails` |
| 15 | Mutated manifest fails verify | `::test_15_mutated_manifest_fails` |
| 16 | Missing evidence file fails verify | `::test_16_missing_evidence_file_fails` |
| 17 | Missing manifest fails verify | `::test_17_missing_manifest_fails` |
| 18 | Missing checksums fails verify | `::test_18_missing_checksums_fails` |
| 19 | Duplicate checksum key fails | `test_checksums.py::test_19_duplicate_key_fails` |
| 20 | Unknown checksum key fails | `::test_20_unknown_key_fails` |
| 21 | Malformed checksum digest fails | `::test_21_malformed_digest_fails` |
| 22 | Unknown extra file in bundle fails | `test_verify_bundle.py::test_22_unknown_extra_file_fails` |
| 23 | Manifest source hash mismatch fails | `::test_23_manifest_source_hash_mismatch_fails` |
| 24 | Manifest bundled hash mismatch fails | `::test_24_manifest_bundled_hash_mismatch_fails` |
| 25 | Non-canonical manifest fails | `::test_25_non_canonical_manifest_fails` |
| 26 | VERIFIED_PRESENT does not claim truth | `::test_26_verified_present_is_not_a_truth_claim` + `test_no_bare_asserts.py::TestHonesty` |
| 27 | Selfcheck passes | `test_selfcheck.py::test_27_selfcheck_passes_in_process` |
| 28 | No bare runtime asserts | `test_no_bare_asserts.py::test_28_no_bare_asserts_in_runtime` |
| 29 | `python -O` unchanged behaviour | full suite + selfcheck pass identically under `-O` |
| 30 | manifest verifier passes, no subprocesses | `test_no_bare_asserts.py::test_30_manifest_verifier_present_static_and_passes` |

Additional coverage: checksums round-trip, missing-key and malformed-line and
uppercase-digest rejection; manifest field/shape/size/sha/status validation;
deterministic manifest under a fixed timestamp; non-empty output dir refused;
extra file inside `evidence/` refused; missing bundle dir fails.

## Manual smoke test (NOT part of the freeze gate)

```bash
printf "hello evidence\n" > /tmp/evidence.txt
python3 aletheia.py bundle-file --file /tmp/evidence.txt \
  --case-id case_001 --evidence-id evidence_001 --out /tmp/aletheia_bundle
python3 aletheia.py verify --bundle /tmp/aletheia_bundle
```

Confirmed: prints `Aletheia evidence bundle verified` and
`evidence_status = VERIFIED_PRESENT`; the bundle contains `evidence_manifest.json`,
`evidence_checksums.txt`, and `evidence/evidence_001.bin`; mutating the evidence
file, the manifest, the checksums, or adding an unknown file makes verify fail with
the correct `FAILED_*` status.

## Scope

One local file → deterministic evidence bundle → hash/checksum verification.
Nothing else. Not connected to the workflow. No new features beyond the spec.
