"""Stage-targeted bundle fixtures (Move 79, Blocker 4).

A case intended to exercise, say, receipt linkage must actually REACH the
receipt stage — it must not die earlier at a checksum mismatch. So after
mutating a file, these builders REPAIR the declared hashes upstream of the
target stage (top-level companion_checksums.txt and any nested checksum
file that covers the mutated path), so the bundle is internally consistent
right up to the stage under test.

Read-only with respect to the frozen reference: every fixture is built in
a fresh copy.
"""

import hashlib
import json
import os
import shutil


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rewrite_checksums(bundle, rel_changed=None):
    """Repair declared hashes to a FIXPOINT.

    Repairing a nested checksum file changes that file, and its own hash
    is declared one level up — so a single pass leaves a cascade of stale
    hashes and the fixture dies at the wrong stage. Iterate until nothing
    changes."""
    for _ in range(10):
        if not _rewrite_pass(bundle):
            return
    raise RuntimeError('checksum repair did not reach a fixpoint')


def _rewrite_pass(bundle):
    any_changed = False
    for root, _dirs, files in os.walk(bundle):
        for name in sorted(files):
            if not name.endswith("checksums.txt"):
                continue
            sums_path = os.path.join(root, name)
            base = os.path.dirname(sums_path)
            with open(sums_path, "r", encoding="utf-8") as handle:
                lines = handle.read().splitlines()
            out = []
            changed = False
            for line in lines:
                if not line.strip():
                    out.append(line)
                    continue
                parts = line.split("  ")
                if len(parts) == 2:
                    digest, rel = parts
                    label = None
                elif len(parts) == 3:
                    label, digest, rel = parts
                else:
                    out.append(line)
                    continue
                target = os.path.join(base, rel)
                if not os.path.isfile(target) and label:
                    # labelled provenance entries (e.g. source_run_sha256)
                    # reference the SOURCE RUN file, not a sibling. Resolve
                    # it so the binding can be repaired and the fixture can
                    # actually reach its intended stage.
                    src = os.path.join(bundle, "coordinator_output",
                                       "sentinel_run", rel)
                    if os.path.isfile(src):
                        target = src
                if os.path.isfile(target):
                    new = _sha256(target)
                    if new != digest:
                        changed = True
                        out.append("%s  %s  %s" % (label, new, rel)
                                   if label else "%s  %s" % (new, rel))
                        continue
                out.append(line)
            if changed:
                any_changed = True
                with open(sums_path, "w", encoding="utf-8") as handle:
                    handle.write("\n".join(out) + "\n")
    return any_changed


def _fresh(ref, dest, name):
    path = os.path.join(dest, name)
    if os.path.isdir(path):
        shutil.rmtree(path)
    shutil.copytree(ref, path)
    return path


def _load(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _dump(path, obj):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(obj, handle, sort_keys=True, separators=(",", ":"),
                  ensure_ascii=False)
        handle.write("\n")


RUN = os.path.join("coordinator_output", "sentinel_run",
                   "sentinel_run.json")


def stage_manifest_field_missing(bundle):
    """Remove a required report field -> manifest stage."""
    report = os.path.join(bundle, "companion_report.json")
    obj = _load(report)
    obj.pop("sentinel_status", None)
    _dump(report, obj)
    _rewrite_checksums(bundle, "companion_report.json")


def stage_manifest_json_invalid(bundle):
    """Truncate the report -> manifest parse stage (hashes repaired)."""
    report = os.path.join(bundle, "companion_report.json")
    with open(report, "rb") as handle:
        data = handle.read()
    with open(report, "wb") as handle:
        handle.write(data[: len(data) // 2])
    _rewrite_checksums(bundle, "companion_report.json")


def stage_receipt_linkage_broken(bundle):
    """Break a prior_hash link -> receipt stage (all hashes repaired)."""
    run = os.path.join(bundle, RUN)
    obj = _load(run)
    if len(obj.get("receipts", [])) >= 2:
        obj["receipts"][1]["prior_hash"] = "e" * 64
    _dump(run, obj)
    _rewrite_checksums(bundle, RUN)


def stage_receipt_sequence_broken(bundle):
    """Renumber a receipt_id -> receipt sequence check."""
    run = os.path.join(bundle, RUN)
    obj = _load(run)
    if len(obj.get("receipts", [])) >= 2:
        obj["receipts"][1]["receipt_id"] = 7
    _dump(run, obj)
    _rewrite_checksums(bundle, RUN)


def stage_canonical_recompute_mismatch(bundle):
    """Change a hashed payload field WITHOUT updating canonical_hash ->
    canonical recomputation stage (declared linkage stays intact)."""
    run = os.path.join(bundle, RUN)
    obj = _load(run)
    if obj.get("receipts"):
        obj["receipts"][0]["reason_code"] = "TAMPERED_FOR_TEST"
    _dump(run, obj)
    _rewrite_checksums(bundle, RUN)




def stage_report_field_missing_hashes_repaired(bundle):
    """Remove a required report field AND repair all declared hashes to a
    fixpoint, so the bundle reaches report-structure logic in BOTH
    implementations rather than dying at a checksum mismatch. Python and
    Rust reject this at DIFFERENT stages (Python report-canonicality,
    Rust manifest required-field) — a real divergence, reported honestly."""
    report = os.path.join(bundle, "companion_report.json")
    obj = _load(report)
    obj.pop("sentinel_status", None)
    _dump(report, obj)
    _rewrite_checksums(bundle)


def stage_top_level_report_noncanonical_hashes_repaired(bundle):
    """Append one noncanonical byte to the top-level companion_report.json AND
    repair every declared hash to a fixpoint, so the shared declared-hash stage
    PASSES and the fixture reaches the canonical-report stage: Python rejects at
    report-canonicality (REPORT_NOT_CANONICAL / canonical_report), while Rust —
    whose declared-hash and receipt checks all pass — reaches its documented
    out-of-scope INCONCLUSIVE completion (OK / complete). The legacy fixture
    appended the byte WITHOUT repairing the declared hash, so it died early at
    the shared DECLARED_HASH_MISMATCH stage instead of its intended stage; this
    stage-targeted builder runs after the frozen generator and replaces that
    directory in place."""
    report = os.path.join(bundle, "companion_report.json")
    with open(report, "ab") as handle:
        handle.write(b" ")
    _rewrite_checksums(bundle)


BUILDERS = {
    "tamper_top_level_report":
        stage_top_level_report_noncanonical_hashes_repaired,
    "stage_report_field_missing_repaired":
        stage_report_field_missing_hashes_repaired,
    "stage_manifest_field_missing": stage_manifest_field_missing,
    "stage_manifest_json_invalid": stage_manifest_json_invalid,
    "stage_receipt_linkage_broken": stage_receipt_linkage_broken,
    "stage_receipt_sequence_broken": stage_receipt_sequence_broken,
    "stage_canonical_recompute_mismatch": stage_canonical_recompute_mismatch,
}


def build(reference_bundle, dest_dir):
    """Create every stage-targeted fixture. Returns the names built."""
    names = []
    for name, mutate in sorted(BUILDERS.items()):
        path = _fresh(reference_bundle, dest_dir, name)
        mutate(path)
        names.append(name)
    return names


if __name__ == "__main__":
    import sys
    for built in build(sys.argv[1], sys.argv[2]):
        print("built:", built)
