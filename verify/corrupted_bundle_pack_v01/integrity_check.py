"""Move 80: fixture integrity checker.

Proves, before any verifier runs:

  1. the frozen clean seed is unchanged (every file matches the frozen
     Move 71 sidecar reference_bundle_hashes.sha256, no extras, and the
     pinned seed tree hash matches);
  2. all eight required fixtures exist with unique IDs and unique
     canonical filenames;
  3. every fixture is bound to the pinned clean seed;
  4. every declared mutation occurred and NO undeclared mutation
     occurred (normalized tree comparison against the seed: relative
     paths, file bytes, file type, permission bits, declared additions
     and deletions);
  5. every fixture hash matches the committed pins, and the committed
     pin files themselves are exactly reproducible from the generator
     (fixture_hashes / mutation_ledger / fixture_manifest re-derived and
     compared);
  6. two independent fresh generations are byte-identical;
  7. the expected-results manifest is well-formed: eight cases, verdict/
     exit consistency with the fixed map, and every declared Rust reason
     code exists in the adopted reason map (no invented reason codes).

Read-only with respect to the repository. Exit 0 on PASS, 1 on FAIL,
2 on usage.
"""

import argparse
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

sys.path.insert(0, HERE)
import generate_fixtures as gen
import author_pins

EXIT_FOR_VERDICT = {"PASS": 0, "FAIL": 1, "USAGE": 2, "INCONCLUSIVE": 3}

REASON_MAP = os.path.join(ROOT, "verify", "agreement_harness_v01",
                          "reason_map.json")

_failures = []


def ok(msg):
    print("  OK    %s" % msg)


def bad(msg):
    print("  FAIL  %s" % msg)
    _failures.append(msg)


def load_json(name):
    with open(os.path.join(HERE, name), "r", encoding="utf-8") as handle:
        return json.load(handle)


def check_seed():
    sidecar = gen.SEED_SIDECAR
    declared = {}
    with open(sidecar, "r", encoding="utf-8") as handle:
        for line in handle.read().splitlines():
            if not line.strip():
                continue
            digest, rel = line.split("  ", 1)
            rel = rel[2:] if rel.startswith("./") else rel
            declared[rel.replace(os.sep, "/")] = digest
    actual = author_pins._walk_files(gen.SEED)
    missing = sorted(set(declared) - set(actual))
    extra = sorted(set(actual) - set(declared))
    mismatched = sorted(rel for rel in set(declared) & set(actual)
                        if declared[rel] != actual[rel])
    if missing:
        bad("seed files missing vs frozen sidecar: %s" % missing[:3])
    if extra:
        bad("undeclared extra files in seed: %s" % extra[:3])
    if mismatched:
        bad("seed files differ from frozen sidecar: %s" % mismatched[:3])
    if not (missing or extra or mismatched):
        ok("clean seed unchanged: %d/%d files match the frozen sidecar"
           % (len(actual), len(declared)))
    seed_meta = load_json("mutation_ledger.json")["seed"]
    live_v0 = gen.seed_tree_hash_v0(gen.SEED)
    live_v1 = gen.entry_tree_hash_v1(gen.SEED)
    if (live_v0 == gen.SEED_TREE_HASH_V0
            and seed_meta["seed_tree_hash_v0"] == gen.SEED_TREE_HASH_V0):
        ok("APPROVED seed pin seed_tree_hash_v0 == %s"
           % gen.SEED_TREE_HASH_V0[:16])
    else:
        bad("approved seed_tree_hash_v0 pin violated (live %s, ledger %s,"
            " constant %s)" % (live_v0[:16],
                               seed_meta["seed_tree_hash_v0"][:16],
                               gen.SEED_TREE_HASH_V0[:16]))
    if (live_v1 == gen.SEED_ENTRY_TREE_HASH_V1
            and seed_meta["seed_entry_tree_hash_v1"]
            == gen.SEED_ENTRY_TREE_HASH_V1):
        ok("secondary seed pin seed_entry_tree_hash_v1 == %s"
           % gen.SEED_ENTRY_TREE_HASH_V1[:16])
    else:
        bad("secondary seed_entry_tree_hash_v1 pin violated")
    if live_v0 != live_v1:
        ok("the two named algorithms are distinct; neither value can "
           "be assigned to the other algorithm's name")
    else:
        bad("algorithm outputs collide; naming is meaningless")


def check_fixture_set(results):
    ids = list(results)
    if sorted(ids) == sorted(gen.FIXTURE_IDS) and len(ids) == 8:
        ok("all eight required fixtures exist")
    else:
        bad("fixture set mismatch: %s" % sorted(ids))
    names = [gen.fixture_filename(f) for f in gen.FIXTURE_IDS]
    if len(set(gen.FIXTURE_IDS)) == 8 and len(set(names)) == 8:
        ok("fixture IDs and canonical filenames are unique")
    else:
        bad("duplicate fixture ID or filename")


def check_hashes(results):
    pinned = load_json("fixture_hashes.json")
    for fid in gen.FIXTURE_IDS:
        want = pinned.get(fid, {})
        got = results[fid]
        if (want.get("sha256") == got["hash"]
                and want.get("kind") == got["kind"]
                and want.get("filename") == gen.fixture_filename(fid)):
            ok("%s hash matches pin (%s)" % (fid, got["hash"][:16]))
        else:
            bad("%s does not match pinned hash/kind/filename" % fid)


def check_mutations(results):
    ledger = load_json("mutation_ledger.json")["fixtures"]
    seed_files = author_pins._walk_files(gen.SEED)
    seed_modes = _walk_modes(gen.SEED)
    for fid in gen.FIXTURE_IDS:
        entry = ledger[fid]["files"]
        declared_added = {a["path"] for a in entry["added"]}
        declared_removed = {r["path"] for r in entry["removed"]}
        declared_changed = {c["path"]: c["sha256"]
                            for c in entry["changed"]}
        if results[fid]["kind"] == "zip":
            want = load_json("fixture_hashes.json")[fid]["sha256"]
            if (declared_added == {gen.fixture_filename(fid)}
                    and not declared_removed and not declared_changed
                    and results[fid]["hash"] == want):
                ok("%s: declared standalone ZIP mutation verified" % fid)
            else:
                bad("%s: ZIP mutation record mismatch" % fid)
            continue
        fx_files = author_pins._walk_files(results[fid]["path"])
        fx_modes = _walk_modes(results[fid]["path"])
        added = set(fx_files) - set(seed_files)
        removed = set(seed_files) - set(fx_files)
        changed = {rel for rel in set(seed_files) & set(fx_files)
                   if seed_files[rel] != fx_files[rel]}
        problems = []
        if added != declared_added:
            problems.append("added %s != declared %s"
                            % (sorted(added), sorted(declared_added)))
        if removed != declared_removed:
            problems.append("removed %s != declared %s"
                            % (sorted(removed), sorted(declared_removed)))
        if changed != set(declared_changed):
            problems.append("changed %s != declared %s"
                            % (sorted(changed),
                               sorted(declared_changed)))
        for rel in changed & set(declared_changed):
            if fx_files[rel] != declared_changed[rel]:
                problems.append("changed file %s hash differs from "
                                "declared" % rel)
        perm_drift = sorted(
            rel for rel in set(fx_modes) & set(seed_modes)
            if fx_modes[rel] != seed_modes[rel])
        if perm_drift:
            problems.append("undeclared permission drift: %s"
                            % perm_drift[:3])
        if problems:
            bad("%s: %s" % (fid, "; ".join(problems)))
        else:
            ok("%s: every declared mutation occurred; no undeclared "
               "mutation (paths, bytes, types, permissions)" % fid)


def _walk_modes(root):
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            out[rel] = os.stat(full).st_mode & 0o777
    return out


STALE_FILE = os.path.join("coordinator_output", "case_bundle_v02",
                          "bundle_checksums.txt")


def _first_line(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read().splitlines()[0]


def check_stale_line_preserved(results):
    """The frozen seed's pre-existing stale case_manifest.json entry
    (bundle_checksums.txt line 1) must remain byte-identical in EVERY
    fixture that retains the file: the selective closure repair never
    touches unrelated stale entries."""
    seed_line = _first_line(os.path.join(gen.SEED, STALE_FILE))
    for fid in gen.FIXTURE_IDS:
        if results[fid]["kind"] != "dir":
            continue
        target = os.path.join(results[fid]["path"], STALE_FILE)
        if not os.path.isfile(target):
            bad("%s: bundle_checksums.txt missing" % fid)
            continue
        if _first_line(target) == seed_line:
            ok("%s: unrelated stale case_manifest.json entry "
               "byte-identical to the frozen seed" % fid)
        else:
            bad("%s: unrelated stale case_manifest.json entry was "
                "repaired (selective closure violated)" % fid)


def check_line_repairs(results):
    """Every declared checksum line repair must be re-verifiable from
    bytes: old digest == the SEED's declared digest at that line; new
    digest == the FIXTURE's declared digest at that line == the actual
    hash of the resolved target inside the fixture."""
    ledger = load_json("mutation_ledger.json")["fixtures"]
    for fid in gen.FIXTURE_IDS:
        if results[fid]["kind"] != "dir":
            continue
        repairs = ledger[fid]["files"].get("checksum_line_repairs", [])
        problems = []
        for repair in repairs:
            rel_cs = repair["checksum_file"]
            line_no = repair["line_no"]
            with open(os.path.join(gen.SEED, rel_cs),
                      encoding="utf-8") as handle:
                seed_lines = handle.read().splitlines()
            with open(os.path.join(results[fid]["path"], rel_cs),
                      encoding="utf-8") as handle:
                fx_lines = handle.read().splitlines()
            if repair["old_sha256"] not in seed_lines[line_no - 1]:
                problems.append("%s:%d old digest not in seed line"
                                % (rel_cs, line_no))
            if repair["new_sha256"] not in fx_lines[line_no - 1]:
                problems.append("%s:%d new digest not in fixture line"
                                % (rel_cs, line_no))
            target = gen._resolve_entry_target(
                results[fid]["path"],
                os.path.join(results[fid]["path"], rel_cs),
                repair["entry_rel"], repair["label"])
            if (not os.path.isfile(target)
                    or gen.sha256_file(target) != repair["new_sha256"]):
                problems.append("%s:%d new digest does not match the "
                                "resolved target bytes"
                                % (rel_cs, line_no))
        if problems:
            bad("%s: %s" % (fid, "; ".join(problems)))
        elif repairs:
            ok("%s: all %d declared checksum line repairs re-verified "
               "from bytes" % (fid, len(repairs)))


def check_pins_reproducible():
    hashes, ledger, manifest = author_pins.derive()
    for name, derived in (("fixture_hashes.json", hashes),
                          ("mutation_ledger.json", ledger),
                          ("fixture_manifest.json", manifest)):
        committed = load_json(name)
        if committed == derived:
            ok("%s exactly reproducible from the generator" % name)
        else:
            bad("%s does not match a fresh derivation" % name)


def _tree_bytes(root):
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            with open(full, "rb") as handle:
                out[rel] = hashlib.sha256(handle.read()).hexdigest()
    return out


def check_two_generations(gen_a, gen_b):
    ta, tb = _tree_bytes(gen_a), _tree_bytes(gen_b)
    if ta == tb and ta:
        ok("two independent generations byte-identical (%d files)"
           % len(ta))
    else:
        only_a = sorted(set(ta) - set(tb))[:3]
        only_b = sorted(set(tb) - set(ta))[:3]
        diff = sorted(r for r in set(ta) & set(tb) if ta[r] != tb[r])[:3]
        bad("generations differ (only_a=%s only_b=%s diff=%s)"
            % (only_a, only_b, diff))


def check_expected_results():
    doc = load_json("expected_results.json")
    cases = doc.get("cases", {})
    if sorted(cases) == sorted(gen.FIXTURE_IDS):
        ok("expected_results.json declares exactly the eight fixtures")
    else:
        bad("expected_results.json case set mismatch")
    with open(REASON_MAP, "r", encoding="utf-8") as handle:
        rmap = json.load(handle)
    rust_codes = {e["value"] for e in rmap["rust_bundle"]}
    archive_codes = {e["value"] for e in rmap["archive"]}
    for fid, case in sorted(cases.items()):
        for key in ("python_expected", "rust_expected",
                    "archive_oracle_expected"):
            spec = case.get(key)
            if spec is None:
                continue
            if EXIT_FOR_VERDICT.get(spec["verdict"]) != spec["exit_code"]:
                bad("%s.%s verdict/exit inconsistent" % (fid, key))
            if key == "rust_expected" and fid != "M80-PATH-TRAVERSAL-001":
                if spec["reason_code"] not in rust_codes:
                    bad("%s: rust reason %s not in adopted reason map"
                        % (fid, spec["reason_code"]))
            if (key in ("archive_oracle_expected", "rust_expected")
                    and fid == "M80-PATH-TRAVERSAL-001"):
                if spec["reason_code"] not in archive_codes:
                    bad("%s: archive reason %s not in adopted reason map"
                        % (fid, spec["reason_code"]))
    ok("expected verdict/exit consistency and adopted-reason-code "
       "existence verified (no invented reason codes)")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Verify Move 80 fixture integrity.")
    parser.add_argument("--gen-a", required=True,
                        help="first freshly generated fixture directory")
    parser.add_argument("--gen-b", required=True,
                        help="second freshly generated fixture directory "
                             "(independent generation)")
    args = parser.parse_args(argv)
    for label, path in (("--gen-a", args.gen_a), ("--gen-b", args.gen_b)):
        if not os.path.isdir(path):
            print("usage error: %s is not a directory: %s" % (label, path))
            return 2

    results = {}
    for fid in gen.FIXTURE_IDS:
        target = os.path.join(args.gen_a, gen.fixture_filename(fid))
        if fid == "M80-PATH-TRAVERSAL-001":
            if not os.path.isfile(target):
                bad("missing fixture: %s" % fid)
                continue
            results[fid] = {"path": target, "kind": "zip",
                            "hash": gen.sha256_file(target)}
        else:
            if not os.path.isdir(target):
                bad("missing fixture: %s" % fid)
                continue
            results[fid] = {"path": target, "kind": "dir",
                            "hash": gen.entry_tree_hash_v1(target)}

    check_seed()
    if len(results) == 8:
        check_fixture_set(results)
        check_hashes(results)
        check_mutations(results)
        check_stale_line_preserved(results)
        check_line_repairs(results)
    check_two_generations(args.gen_a, args.gen_b)
    check_pins_reproducible()
    check_expected_results()

    if _failures:
        print("MOVE_80_FIXTURE_INTEGRITY: FAIL (%d)" % len(_failures))
        return 1
    print("MOVE_80_FIXTURE_INTEGRITY: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
