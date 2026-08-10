"""Move 80: pin derivation and authoring.

Derives the machine-readable pin files for the corrupted bundle pack:

  - fixture_hashes.json    : pinned fixture identity hashes
  - mutation_ledger.json   : every changed/added/removed file per fixture,
                             computed mechanically against the frozen seed
  - fixture_manifest.json  : fixture metadata, seed binding, commands

Run as a script it (re)writes those files next to itself. The integrity
checker imports the SAME derivation functions and asserts that freshly
generated fixtures reproduce the committed pins exactly, so the pins can
never silently drift from the generator.

expected_results.json is NOT derived here: expectations are declared from
the Move 80 Phase 1 contract inventory against the adopted v27 baseline,
never recorded from whatever current code emits.
"""

import hashlib
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, HERE)
import generate_fixtures as gen

SEED = gen.SEED
SEED_SIDECAR = gen.SEED_SIDECAR

# The frozen seed's single pre-existing stale checksum entry. It is part
# of the frozen bytes and must remain byte-identical in every fixture
# that retains the file (review-mandated; the v01 global fixpoint repair
# silently rewrote it).
STALE_ENTRY_FILE = os.path.join(
    "coordinator_output", "case_bundle_v02", "bundle_checksums.txt")
PRESERVED_STALE_ENTRY = {
    "checksum_file": "coordinator_output/case_bundle_v02/"
                     "bundle_checksums.txt",
    "line_no": 1,
    "entry_rel": "case_manifest.json",
    "declared_sha256": "cb1fc67c184dbf7039b9900f7994f0bb2e85287bc8a95f"
                       "296dea3aa746166b50",
    "actual_target_sha256": "5757263382f7b4c9edc38c62709dbd52ace113e06"
                            "06b96d841869e99a112748a",
    "status": "pre-existing stale entry in the FROZEN seed; deliberately "
              "left byte-identical by the selective closure repair",
}

PRINCIPAL_MUTATIONS = {
    "M80-CLEAN-001":
        "none (exact seed copy; clean control)",
    "M80-MISSING-MANIFEST-001":
        "delete companion_report.json — the exact file serving the adopted "
        "verifiers' manifest boundary (MANIFEST_FILE in "
        "rust/witness-verify/src/manifest.rs; first required file the "
        "frozen Python verifier demands)",
    "M80-CHANGED-EVIDENCE-001":
        "flip byte at offset 5 (XOR 0xFF) of "
        "coordinator_output/aletheia_bundle/evidence/evidence_001.bin via "
        "the frozen Move 71 generator's _flip_byte; the stale nested "
        "declared hash is deliberately retained — that mismatch is the "
        "corruption under test",
    "M80-BAD-RECEIPT-HASH-001":
        "receipts[0].reason_code -> 'TAMPERED_FOR_TEST' in "
        "coordinator_output/sentinel_run/sentinel_run.json via the adopted "
        "corpus builder stage_canonical_recompute_mismatch, so the declared "
        "canonical_hash no longer matches recomputation",
    "M80-DUPLICATE-RECEIPT-001":
        "append an exact duplicate of the final receipt object to the "
        "receipts array of coordinator_output/sentinel_run/sentinel_run.json",
    "M80-MALFORMED-JSON-001":
        "truncate companion_report.json to half its byte length "
        "(syntactically invalid JSON) via the adopted corpus builder "
        "stage_manifest_json_invalid",
    "M80-PATH-TRAVERSAL-001":
        "single-entry ZIP whose entry name is b'../evil', produced by the "
        "adopted deterministic archive builder build_archives._one — "
        "byte-identical to the Move 79 TERMUX-confirmed corpus case "
        "'traversal'",
    "M80-UNKNOWN-SCHEMA-001":
        "companion_report.json field companion_cli_version -> '9.9.9', "
        "re-serialized in project-canonical bytes by the adopted "
        "companion_lib.canonical.canonical_bytes (frozen report is already "
        "canonical, so the version value is the only in-report byte change)",
}

SUPPORTING_REPAIRS = {
    "M80-CLEAN-001": "none",
    "M80-MISSING-MANIFEST-001":
        "none — both engines reach their decisive manifest check before "
        "any hash comparison; companion_checksums.txt still lists the "
        "deleted file, which is irrelevant at the decisive stage",
    "M80-CHANGED-EVIDENCE-001":
        "none by design — the stale declared hash IS the tested fault",
    "M80-BAD-RECEIPT-HASH-001":
        "principal mutation: one receipt canonical_hash (index 0) -> fixed invalid 0*64, nothing else changed; then SELECTIVE dependency-closure repair of exactly the entries that "
        "declare sentinel_run.json (sentinel_case/checksums.txt:1, "
        "histor_sentinel_case/checksums.txt:1) and the one entry that "
        "declares the changed sentinel_case/checksums.txt "
        "(bundle_checksums.txt:4); the frozen stale "
        "bundle_checksums.txt:1 case_manifest.json entry is untouched. "
        "sentinel_run.json re-serialized by the adopted corpus _dump "
        "byte form (sorted keys, compact separators, trailing newline)",
    "M80-DUPLICATE-RECEIPT-001":
        "same declared transformation and identical selective closure as "
        "M80-BAD-RECEIPT-HASH-001: adopted corpus _dump re-serialization "
        "of sentinel_run.json (the frozen file is not project-canonical, "
        "so no undeclared general canonical rewrite is performed) plus "
        "repair of exactly the three declaring entries; the frozen stale "
        "bundle_checksums.txt:1 entry is untouched",
    "M80-MALFORMED-JSON-001":
        "SELECTIVE closure repair of exactly the one entry that declares "
        "companion_report.json (companion_checksums.txt:2); no other "
        "checksum byte changes; the frozen stale bundle_checksums.txt:1 "
        "entry is untouched",
    "M80-PATH-TRAVERSAL-001": "none",
    "M80-UNKNOWN-SCHEMA-001":
        "SELECTIVE closure repair of exactly the one entry that declares "
        "companion_report.json (companion_checksums.txt:2); the frozen "
        "stale bundle_checksums.txt:1 entry is untouched, so the "
        "unsupported schema pin is the sole fault",
}

# The verifier command per fixture is declared as argv templates with the
# placeholders <python3>, <companion.py>, <rust-bin>, <fixture>.
COMMANDS = {}
for _fid in gen.FIXTURE_IDS:
    if _fid == "M80-PATH-TRAVERSAL-001":
        COMMANDS[_fid] = {
            "rust": ["<rust-bin>", "inspect-archive", "<fixture>"],
            "python_oracle":
                "verify/agreement_harness_v01/oracles/zipguard_oracle."
                "inspect_archive(<fixture>)",
        }
    else:
        COMMANDS[_fid] = {
            "python": ["<python3>", "-B",
                       "src/12_companion_cli_v031/companion.py",
                       "verify", "--run", "<fixture>"],
            "rust": ["<rust-bin>", "verify", "<fixture>"],
        }


def sha256_file(path):
    return gen.sha256_file(path)


def seed_binding():
    return {
        "seed_path": "freeze_record/python_behaviour_freeze_v01/"
                     "reference_bundle",
        "seed_tree_hash_v0": gen.seed_tree_hash_v0(SEED),
        "seed_tree_hash_v0_algorithm":
            "APPROVED contract-inventory pin: files only, in "
            "sorted(os.walk) order with sorted filenames; per file: "
            "relpath bytes, NUL, raw file bytes, NUL; SHA-256 of the "
            "concatenation",
        "seed_entry_tree_hash_v1": gen.entry_tree_hash_v1(SEED),
        "seed_entry_tree_hash_v1_algorithm":
            "fixture-identity algorithm: sha256 over sorted entries of "
            "relpath NUL type(F|D) NUL sha256(file bytes; empty for "
            "directories) NUL; permission bits deliberately excluded "
            "from the pin (checked against the seed by the "
            "undeclared-mutation comparison instead)",
        "seed_sidecar": "freeze_record/python_behaviour_freeze_v01/"
                        "reference_bundle_hashes.sha256",
        "seed_sidecar_sha256": sha256_file(SEED_SIDECAR),
    }


def _walk_files(root):
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            out[rel] = sha256_file(full)
    return out


def diff_against_seed(fixture_dir):
    """Mechanical mutation record: files added, removed, or byte-changed
    relative to the frozen seed, with content hashes on both sides."""
    seed_files = _walk_files(SEED)
    fx_files = _walk_files(fixture_dir)
    added = sorted(set(fx_files) - set(seed_files))
    removed = sorted(set(seed_files) - set(fx_files))
    changed = sorted(rel for rel in set(seed_files) & set(fx_files)
                     if seed_files[rel] != fx_files[rel])
    return {
        "added": [{"path": rel, "sha256": fx_files[rel]} for rel in added],
        "removed": [{"path": rel, "seed_sha256": seed_files[rel]}
                    for rel in removed],
        "changed": [{"path": rel, "seed_sha256": seed_files[rel],
                     "sha256": fx_files[rel]} for rel in changed],
    }


def derive(work_dir=None):
    """Generate fixtures into a temp dir and derive all pin structures.
    Returns (fixture_hashes, mutation_ledger, fixture_manifest)."""
    own_tmp = work_dir is None
    if own_tmp:
        work_dir = tempfile.mkdtemp(prefix="m80_pins_")
    try:
        results = gen.generate(os.path.join(work_dir, "fixtures"))
        hashes = {}
        ledger = {"seed": seed_binding(), "fixtures": {}}
        manifest = {"seed": seed_binding(), "fixtures": {}}
        for fid in gen.FIXTURE_IDS:
            info = results[fid]
            fname = gen.fixture_filename(fid)
            hashes[fid] = {"filename": fname, "kind": info["kind"],
                           "sha256": info["hash"]}
            if info["kind"] == "dir":
                mutations = diff_against_seed(info["path"])
                mutations["checksum_line_repairs"] = \
                    info["checksum_line_repairs"]
                mutations["preserved_stale_entries"] = (
                    [PRESERVED_STALE_ENTRY]
                    if os.path.isfile(os.path.join(
                        info["path"], STALE_ENTRY_FILE)) else [])
            else:
                mutations = {
                    "added": [{"path": fname,
                               "sha256": info["hash"],
                               "note": "standalone ZIP fixture; not "
                                       "seed-derived. Entry list: "
                                       "single entry '../evil'"}],
                    "removed": [], "changed": [],
                }
            ledger["fixtures"][fid] = {
                "principal_mutation": PRINCIPAL_MUTATIONS[fid],
                "supporting_repairs": SUPPORTING_REPAIRS[fid],
                "files": mutations,
            }
            manifest["fixtures"][fid] = {
                "fixture_id": fid,
                "filename": fname,
                "kind": info["kind"],
                "fixture_sha256": info["hash"],
                "commands": COMMANDS[fid],
            }
        return hashes, ledger, manifest
    finally:
        if own_tmp:
            shutil.rmtree(work_dir, ignore_errors=True)


def _write(name, obj):
    path = os.path.join(HERE, name)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(obj, handle, indent=1, sort_keys=True)
        handle.write("\n")
    return path


def main():
    hashes, ledger, manifest = derive()
    for name, obj in (("fixture_hashes.json", hashes),
                      ("mutation_ledger.json", ledger),
                      ("fixture_manifest.json", manifest)):
        print("wrote", _write(name, obj))
    return 0


if __name__ == "__main__":
    sys.exit(main())
