"""Move 79 Rust-source provenance verifier (B6; hardened in v13 for B3/B4).

Verifies that tools/rust_source_pin.json is DERIVED from the real adopted
Move 78 v10 artifact — not self-certified — and that its recorded audit
metadata is internally consistent.

v13 additions:
  - B3: the pinned set must EQUAL the mechanically enumerated behaviour-path
    set of BOTH the adopted baseline zip AND the current candidate tree, so a
    behaviour file cannot be omitted from the pin (and silently dropped).
  - B4: the pin's recorded adopted_baseline.artifact, adopted_baseline.sha256,
    and pinned_path_count must match the required identity, so contradictory
    audit metadata fails even when the external artifact is itself correct.

Importable: ``verify(real_move78, root, pin, required_zip_sha, required_artifact)``
returns a list of problem strings (empty == OK) and never raises for a
verification failure, so tests can drive it with CONTROLLED baselines.

Runnable: ``python3 verify_rust_provenance.py <real_move78>`` prints a marker
line and exits 0 (OK) / 1 (problem) / 2 (usage).
"""

import hashlib
import json
import os
import sys
import zipfile

REQUIRED_MOVE78_SHA = \
    "6030148c2c1bb373ad69393563e8e2e3078dff93e9f446d728edd18ea3c45252"
REQUIRED_ARTIFACT = "project-witness-MOVE_78_candidate_v10.zip"

PIN_REL = os.path.join("tools", "rust_source_pin.json")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_behaviour_rel(rel):
    """A behaviour-determining Rust path: under rust/, a .rs file or a
    Cargo.toml, excluding build output under rust/target/."""
    rel = rel.replace("\\", "/")
    if not rel.startswith("rust/"):
        return False
    if rel.startswith("rust/target/") or "/target/" in rel:
        return False
    return rel.endswith(".rs") or os.path.basename(rel) == "Cargo.toml"


def single_archive_root(names):
    tops = set()
    for name in names:
        norm = name.replace("\\", "/").lstrip("/")
        if not norm:
            continue
        head = norm.split("/", 1)[0]
        if "/" not in name.replace("\\", "/").rstrip("/") \
                and not name.endswith("/"):
            raise ValueError("AMBIGUOUS_ARCHIVE_ROOT")
        tops.add(head)
    tops.discard("")
    if len(tops) != 1:
        raise ValueError("AMBIGUOUS_ARCHIVE_ROOT")
    return next(iter(tops))


def behaviour_paths_in_zip(names, root):
    out = set()
    prefix = root + "/"
    for name in names:
        norm = name.replace("\\", "/")
        if norm.endswith("/") or not norm.startswith(prefix):
            continue
        rel = norm[len(prefix):]
        if _is_behaviour_rel(rel):
            out.add(rel)
    return out


def behaviour_paths_in_tree(root_dir):
    out = set()
    base = os.path.join(root_dir, "rust")
    for dirpath, dirnames, filenames in os.walk(base):
        if "target" in dirnames:
            dirnames.remove("target")
        for fn in filenames:
            rel = os.path.relpath(os.path.join(dirpath, fn), root_dir)
            rel = rel.replace("\\", "/")
            if _is_behaviour_rel(rel):
                out.add(rel)
    return out


def verify(real_move78, root, pin, required_zip_sha=REQUIRED_MOVE78_SHA,
           required_artifact=REQUIRED_ARTIFACT):
    """Return a list of problems (empty == provenance verified)."""
    problems = []

    if not real_move78:
        return ["REAL_MOVE78 not supplied"]
    if not os.path.isfile(real_move78):
        return ["REAL_MOVE78 not a file: %s" % real_move78]

    got_sha = sha256_file(real_move78)
    if got_sha != required_zip_sha:
        return ["REAL_MOVE78 sha256 %s != required %s"
                % (got_sha[:16], required_zip_sha[:16])]

    prov = pin["provenance"]
    pinned = pin["pinned_paths"]
    pinned_set = set(pinned)
    base_pin = prov["baseline_file_sha256"]
    cand_pin = prov["candidate_file_sha256"]
    declared_changed = sorted(prov["files_changed_from_baseline"])

    # B4: the pin's recorded audit metadata must match the required identity,
    # even though the external artifact is independently correct.
    ab = prov.get("adopted_baseline", {})
    if ab.get("artifact") != required_artifact:
        problems.append("pin records wrong adopted artifact: %r"
                        % ab.get("artifact"))
    if ab.get("sha256") != required_zip_sha:
        problems.append("pin records wrong adopted baseline sha256")
    if pin.get("pinned_path_count") != len(pinned):
        problems.append("pinned_path_count %r != len(pinned_paths) %d"
                        % (pin.get("pinned_path_count"), len(pinned)))

    with zipfile.ZipFile(real_move78) as zf:
        names = zf.namelist()
        try:
            arch_root = single_archive_root(names)
        except ValueError as exc:
            return problems + [str(exc)]

        # B3: the mechanically enumerated baseline behaviour set must EQUAL
        # the pinned set — no behaviour file may be omitted from the pin.
        zip_behaviour = behaviour_paths_in_zip(names, arch_root)
        if zip_behaviour != pinned_set:
            extra = sorted(zip_behaviour - pinned_set)
            missing = sorted(pinned_set - zip_behaviour)
            problems.append("baseline behaviour set != pinned set "
                            "(unpinned=%s missing=%s)" % (extra, missing))

        name_counts = {}
        for n in names:
            name_counts[n] = name_counts.get(n, 0) + 1

        for rel in pinned:
            if not _is_behaviour_rel(rel):
                problems.append("unexpected behaviour path in pin: %s" % rel)
        baseline_bytes = {}
        for rel in pinned:
            full = "%s/%s" % (arch_root, rel)
            if name_counts.get(full, 0) == 0:
                problems.append("pinned path missing from baseline: %s" % rel)
                continue
            if name_counts[full] > 1:
                problems.append("duplicate pinned path in baseline: %s" % rel)
                continue
            with zf.open(full) as fh:
                baseline_bytes[rel] = fh.read()

    if problems:
        return problems

    # B3: the candidate behaviour set must EQUAL the pinned set too.
    tree_behaviour = behaviour_paths_in_tree(root)
    if tree_behaviour != pinned_set:
        extra = sorted(tree_behaviour - pinned_set)
        missing = sorted(pinned_set - tree_behaviour)
        problems.append("candidate behaviour set != pinned set "
                        "(extra=%s removed=%s)" % (extra, missing))
        return problems

    derived_baseline = {rel: sha256_bytes(baseline_bytes[rel])
                        for rel in pinned}
    for rel in pinned:
        if derived_baseline[rel] != base_pin.get(rel):
            problems.append("baseline hash mismatch (pin falsified?): %s" % rel)

    derived_candidate = {}
    for rel in pinned:
        p = os.path.join(root, rel)
        if not os.path.isfile(p):
            problems.append("candidate file missing: %s" % rel)
            continue
        derived_candidate[rel] = sha256_file(p)
        if derived_candidate[rel] != cand_pin.get(rel):
            problems.append("candidate hash mismatch: %s" % rel)

    if problems:
        return problems

    mechanical_changed = sorted(
        rel for rel in pinned
        if derived_baseline[rel] != derived_candidate[rel])
    if mechanical_changed != declared_changed:
        problems.append("declared change set %s != mechanical %s"
                        % (declared_changed, mechanical_changed))

    for rel in pinned:
        if rel not in mechanical_changed \
                and derived_baseline[rel] != derived_candidate[rel]:
            problems.append("unchanged file not byte-identical: %s" % rel)

    for rel in declared_changed:
        if base_pin.get(rel) == cand_pin.get(rel):
            problems.append("declared-changed file has equal pin hashes: %s"
                            % rel)

    return problems


def _main(argv):
    if len(argv) != 2:
        print("usage: verify_rust_provenance.py <REAL_MOVE78.zip>")
        print("RUST_PROVENANCE_CHECK: USAGE")
        return 2
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    with open(os.path.join(root, PIN_REL)) as handle:
        pin = json.load(handle)
    problems = verify(argv[1], root, pin)
    if problems:
        for p in problems:
            print("  problem:", p)
        print("RUST_PROVENANCE_CHECK: FAIL")
        return 1
    print("  baseline + candidate behaviour sets equal the pinned set; "
          "%d hashes derived from the adopted artifact; %d declared change(s) "
          "confirmed mechanically; audit metadata consistent"
          % (len(pin["pinned_paths"]),
             len(pin["provenance"]["files_changed_from_baseline"])))
    print("RUST_PROVENANCE_CHECK: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
