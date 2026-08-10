"""Move 80: inherited-tree checker bound to the REAL adopted v27 ZIP.

A candidate-contained file inventory is self-authenticating: a modified
inherited file and a regenerated inventory would pass together. This
checker therefore takes the actual adopted artifact as input and proves
against ITS bytes (review-mandated):

  1. the supplied ZIP's SHA-256 equals the adopted Move 79 v27 hash;
  2. the ZIP is safe to inspect: no duplicate names, no path traversal,
     no absolute paths, no symlink entries, single root
     project-witness-main/;
  3. every inherited candidate file equals the corresponding verified
     baseline ZIP member bytes -- none modified, none removed;
  4. every candidate file that is NOT a baseline member appears exactly
     in the Move 80 additions allowlist (allowlist.json) -- no
     undeclared addition, no phantom allowlist entry;
  5. no runtime droppings (rust/target, __pycache__, *.pyc);
  6. the human-readable diff report is generated from THIS real
     comparison.

Usage:
  python3 -B check_inherited_vs_zip.py --baseline-zip <abs path>
      [--report <file>]

Exit 0 PASS, 1 FAIL, 2 usage. The adoption gate additionally verifies
the ZIP hash independently with the trusted sha256sum before invoking
this checker; the in-tool hash check means the tool is also safe to run
standalone.
"""

import argparse
import hashlib
import json
import os
import stat
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

ADOPTED_V27_ZIP_SHA256 = (
    "4a95767a3f68ca812c1d543894b65183b82d56f3f8f56e9af61b82c19de1f26b")
ZIP_ROOT = "project-witness-main/"


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_allowlist():
    with open(os.path.join(HERE, "allowlist.json"), "r",
              encoding="utf-8") as handle:
        return sorted(json.load(handle)["added_paths"])


def inspect_zip_safety(zf):
    """Reject duplicate names, traversal, absolute paths, drive-letter
    paths, symlink entries, and anything outside the single expected
    root. Returns a list of problems (empty = safe)."""
    problems = []
    seen = set()
    for info in zf.infolist():
        name = info.filename
        if name in seen:
            problems.append("duplicate entry name: %s" % name)
        seen.add(name)
        if name.startswith("/") or name.startswith("\\"):
            problems.append("absolute path entry: %s" % name)
        if ":" in name.split("/")[0]:
            problems.append("drive-letter path entry: %s" % name)
        parts = name.replace("\\", "/").split("/")
        if ".." in parts:
            problems.append("path traversal entry: %s" % name)
        mode = (info.external_attr >> 16) & 0xFFFF
        if stat.S_ISLNK(mode):
            problems.append("symlink entry: %s" % name)
        if not name.startswith(ZIP_ROOT):
            problems.append("entry outside %s: %s" % (ZIP_ROOT, name))
    return problems


def zip_member_hashes(zf):
    """relpath (under the root, posix) -> sha256 for every FILE member."""
    out = {}
    for info in zf.infolist():
        if info.is_dir():
            continue
        rel = info.filename[len(ZIP_ROOT):]
        digest = hashlib.sha256()
        with zf.open(info, "r") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        out[rel] = digest.hexdigest()
    return out


def walk_candidate():
    files = {}
    droppings = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        rel_dir = os.path.relpath(dirpath, ROOT).replace(os.sep, "/")
        kept = []
        for name in sorted(dirnames):
            is_pycache = name == "__pycache__"
            is_rust_target = (name == "target"
                              and (rel_dir == "rust"
                                   or rel_dir.startswith("rust/")))
            if is_pycache or is_rust_target:
                droppings.append(
                    ((rel_dir + "/") if rel_dir != "." else "") + name)
                continue
            kept.append(name)
        dirnames[:] = kept
        for name in sorted(filenames):
            if name.endswith(".pyc"):
                droppings.append(
                    ((rel_dir + "/") if rel_dir != "." else "") + name)
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, ROOT).replace(os.sep, "/")
            files[rel] = full
    return files, droppings


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Prove no inherited path changed, directly against "
                    "the verified adopted Move 79 v27 ZIP bytes.")
    parser.add_argument("--baseline-zip", required=True,
                        help="path to project-witness-MOVE_79_candidate_"
                             "v27.zip (hash-verified before use)")
    parser.add_argument("--report", default=None,
                        help="also write the report text to this file")
    args = parser.parse_args(argv)

    if not os.path.isfile(args.baseline_zip):
        print("usage error: --baseline-zip is not a file: %s"
              % args.baseline_zip)
        return 2

    lines = []
    failures = []
    lines.append("MOVE 80 INHERITED-TREE DIFF / ALLOWLIST REPORT")
    lines.append("comparison source: the REAL adopted baseline artifact "
                 "supplied at run time (never a candidate-contained "
                 "inventory)")

    actual_hash = sha256_file(args.baseline_zip)
    if actual_hash != ADOPTED_V27_ZIP_SHA256:
        lines.append("  FAIL  supplied baseline ZIP sha256 %s does not "
                     "match the adopted v27 hash %s"
                     % (actual_hash, ADOPTED_V27_ZIP_SHA256))
        text = "\n".join(lines + ["MOVE_80_ALLOWLIST_DIFF: FAIL"]) + "\n"
        sys.stdout.write(text)
        if args.report:
            with open(args.report, "w", encoding="utf-8") as handle:
                handle.write(text)
        return 1
    lines.append("baseline ZIP sha256 verified: %s"
                 % ADOPTED_V27_ZIP_SHA256)

    with zipfile.ZipFile(args.baseline_zip) as zf:
        safety = inspect_zip_safety(zf)
        if safety:
            for problem in safety[:10]:
                failures.append("baseline ZIP unsafe: %s" % problem)
            inherited = {}
        else:
            lines.append("baseline ZIP safety: no duplicate names, no "
                         "traversal, no absolute paths, no symlinks, "
                         "single root %s" % ZIP_ROOT)
            inherited = zip_member_hashes(zf)

    allow = load_allowlist()
    files, droppings = walk_candidate()

    modified = []
    removed = []
    for rel, want in sorted(inherited.items()):
        full = files.get(rel)
        if full is None:
            removed.append(rel)
        elif sha256_file(full) != want:
            modified.append(rel)
    additions = sorted(set(files) - set(inherited))
    undeclared = sorted(set(additions) - set(allow))
    phantom = sorted(set(allow) - set(additions))

    lines.append("inherited baseline file members: %d" % len(inherited))
    lines.append("inherited files verified byte-identical to ZIP member "
                 "bytes: %d" % (len(inherited) - len(modified)
                                - len(removed)))
    if modified:
        failures.append("inherited files MODIFIED vs baseline ZIP: %s"
                        % modified[:10])
    if removed:
        failures.append("inherited files REMOVED vs baseline ZIP: %s"
                        % removed[:10])
    lines.append("declared additions (allowlist): %d" % len(allow))
    lines.append("observed additions: %d" % len(additions))
    for rel in additions:
        lines.append("  + %s" % rel)
    if undeclared:
        failures.append("UNDECLARED additions: %s" % undeclared[:10])
    if phantom:
        failures.append("allowlisted paths MISSING from tree: %s"
                        % phantom[:10])
    if droppings:
        failures.append("runtime droppings present: %s" % droppings[:10])

    for failure in failures:
        lines.append("  FAIL  %s" % failure)
    verdict = "PASS" if not failures else "FAIL"
    lines.append("MOVE_80_ALLOWLIST_DIFF: %s" % verdict)

    text = "\n".join(lines) + "\n"
    sys.stdout.write(text)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as handle:
            handle.write(text)
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
