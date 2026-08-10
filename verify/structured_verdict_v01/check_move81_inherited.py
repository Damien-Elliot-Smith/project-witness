#!/usr/bin/env python3
"""Move 81 baseline-immutability checker.

Compares the candidate tree against the REAL adopted Move 80 v07 ZIP,
member by member, and requires:

  * every file inherited from the Move 80 v07 baseline is byte-identical
    to its member bytes in the real ZIP;
  * every file present in the candidate but not in the baseline is
    exactly on the Move 81 allowlist (added_paths);
  * every allowlisted addition is actually present;
  * no baseline file was deleted.

A candidate-contained inventory is never trusted; the authority is the
real verified ZIP bytes supplied at run time via --baseline-zip. The gate
hash-verifies that ZIP with the trusted sha256sum before calling this.

Exit 0 on full match; nonzero with a diagnostic otherwise.
"""

import argparse
import json
import os
import stat
import sys
import zipfile


IGNORED_DIR_NAMES = ("__pycache__",)
IGNORED_SUFFIXES = (".pyc",)
ZIP_ROOT = "project-witness-main/"


def inspect_zip_safety(zf):
    """Reject duplicate names, traversal, absolute paths, drive-letter
    paths, backslash ambiguity, symlink entries, encrypted entries, and
    anything outside the single expected root. Mirrors the adopted Move 80
    safety design. Returns a list of problems (empty = safe)."""
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
        if "\\" in name:
            problems.append("backslash path ambiguity: %s" % name)
        parts = name.replace("\\", "/").split("/")
        if ".." in parts:
            problems.append("path traversal entry: %s" % name)
        mode = (info.external_attr >> 16) & 0xFFFF
        ftype = mode & 0o170000
        if ftype == stat.S_IFLNK:
            problems.append("symlink entry: %s" % name)
        elif ftype and ftype not in (stat.S_IFREG, stat.S_IFDIR):
            # block/char devices, FIFOs, sockets. Entries written with no
            # file-type bits at all (the common case for archives built
            # from strings) are ordinary members, exactly as zipfile
            # itself treats them.
            problems.append("special-file entry: %s" % name)
        if info.flag_bits & 0x1:
            problems.append("encrypted entry: %s" % name)
        if not name.startswith(ZIP_ROOT):
            problems.append("entry outside %s: %s" % (ZIP_ROOT, name))
    roots = {n.split("/", 1)[0] for n in zf.namelist()}
    if roots != {ZIP_ROOT.rstrip("/")}:
        problems.append("baseline zip roots are not exactly %s: %s"
                        % (ZIP_ROOT, sorted(roots)))
    # CRC integrity of every member
    try:
        bad = zf.testzip()
    except Exception:
        problems.append("archive could not be read for CRC verification")
    else:
        if bad is not None:
            problems.append("CRC failure in member: %s" % bad)
    return problems


def _candidate_files(root):
    """Relative paths of every regular file in the candidate tree, minus
    build/cache artifacts that are never part of the packaged baseline."""
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIR_NAMES
                       and not (os.path.relpath(dirpath, root) == "rust"
                                and d == "target")]
        # also skip anything under rust/target at any depth
        rel_dir = os.path.relpath(dirpath, root)
        parts = rel_dir.split(os.sep)
        if "target" in parts and parts[0] == "rust":
            continue
        for name in filenames:
            if name.endswith(IGNORED_SUFFIXES):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            out[rel] = full
    return out


def _zip_members(zip_path, announce=True):
    """Map of relpath (below the single top-level root) -> bytes for every
    file member of the baseline ZIP. The ZIP is safety-inspected BEFORE any
    member bytes are read; an unsafe baseline fails closed. The inspection
    result is announced when it happens, so the evidence appears whatever
    the later comparison outcome is."""
    members = {}
    with zipfile.ZipFile(zip_path) as zf:
        problems = inspect_zip_safety(zf)
        if problems:
            for p in sorted(problems):
                print("BASELINE_ZIP_UNSAFE: %s" % p)
            raise SystemExit(
                "baseline zip failed safety inspection (%d problem(s))"
                % len(problems))
        if announce:
            print("baseline ZIP safety: no duplicate names, no traversal, "
                  "no absolute paths, no backslash ambiguity, no symlinks, "
                  "no encrypted entries, single root %s" % ZIP_ROOT)
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename
            if "/" not in name:
                continue
            rel = name.split("/", 1)[1]
            if rel == "":
                continue
            with zf.open(info) as handle:
                members[rel] = handle.read()
    return members


def extract_baseline(zip_path, dest_dir):
    """Safely extract the already hash-verified baseline ZIP into a
    private destination directory.

    The ZIP is fully safety-inspected BEFORE a single byte is written, so
    a hostile archive cannot escape the destination. Only regular files
    and directories are created; every member is re-checked against the
    destination boundary as it is written. Returns the absolute path of
    the single extracted root."""
    with zipfile.ZipFile(zip_path) as zf:
        problems = inspect_zip_safety(zf)
        if problems:
            for problem in sorted(problems):
                print("BASELINE_ZIP_UNSAFE: %s" % problem)
            return None
        print("baseline ZIP safety: no duplicate names, no traversal, no "
              "absolute paths, no backslash ambiguity, no symlinks, no "
              "special files, no encrypted entries, CRC verified, single "
              "root %s" % ZIP_ROOT)
        dest_real = os.path.realpath(dest_dir)
        for info in zf.infolist():
            name = info.filename
            target = os.path.realpath(os.path.join(dest_real, name))
            # defence in depth: every write stays inside the destination
            if target != dest_real and not target.startswith(
                    dest_real + os.sep):
                print("BASELINE_ZIP_UNSAFE: member escapes destination: %s"
                      % name)
                return None
            if info.is_dir():
                os.makedirs(target, exist_ok=True)
                continue
            parent = os.path.dirname(target)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as dst:
                dst.write(src.read())
            mode = (info.external_attr >> 16) & 0o7777
            if mode:
                os.chmod(target, mode)
    root = os.path.join(os.path.realpath(dest_dir), ZIP_ROOT.rstrip("/"))
    if not os.path.isdir(root):
        print("BASELINE_EXTRACT_FAILED: expected root missing: %s" % root)
        return None
    return root


def sha256_file(path):
    import hashlib
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Move 81 baseline check")
    parser.add_argument("--baseline-zip", required=True)
    parser.add_argument("--root", default=None)
    parser.add_argument("--allowlist", default=None)
    parser.add_argument(
        "--expect-sha256", default=None,
        help="required adopted baseline SHA-256; when supplied the hash "
             "is verified FIRST and no safety inspection, extraction or "
             "member comparison is performed unless it matches exactly")
    parser.add_argument(
        "--extract-to", default=None,
        help="safely extract the verified baseline into this private "
             "directory and print its single extracted root")
    args = parser.parse_args(argv)

    if not os.path.isfile(args.baseline_zip):
        print("usage error: --baseline-zip is not a file: %s"
              % args.baseline_zip)
        return 2
    if args.extract_to is None:
        if not args.root or not args.allowlist:
            print("usage error: --root and --allowlist are required "
                  "unless --extract-to is used")
            return 2
        if not os.path.isdir(args.root):
            print("usage error: --root is not a directory: %s" % args.root)
            return 2
    else:
        if not os.path.isdir(args.extract_to):
            print("usage error: --extract-to is not a directory: %s"
                  % args.extract_to)
            return 2

    # HASH AUTHORITY FIRST. On mismatch the baseline is not opened, not
    # safety-inspected, not extracted and not compared: a different,
    # byte-modified, or merely renamed ZIP can never become the authority.
    if args.expect_sha256 is not None:
        actual = sha256_file(args.baseline_zip)
        if actual != args.expect_sha256:
            print("BASELINE_HASH_MISMATCH: supplied %s != adopted %s"
                  % (actual, args.expect_sha256))
            print("MOVE_81_INHERITED_CHECK: FAIL (baseline hash mismatch; "
                  "extraction and comparison not attempted)")
            return 1
        print("REAL_MOVE80 independently matched --expect-sha256 in the "
              "baseline checker:")
        print(args.expect_sha256)

    if args.extract_to is not None:
        root = extract_baseline(args.baseline_zip, args.extract_to)
        if root is None:
            print("MOVE_81_BASELINE_EXTRACT: FAIL")
            return 1
        print("EXTRACTED_ROOT: %s" % root)
        print("MOVE_81_BASELINE_EXTRACT: PASS")
        return 0

    with open(args.allowlist, encoding="utf-8") as handle:
        allow = set(json.load(handle)["added_paths"])

    baseline = _zip_members(args.baseline_zip)
    candidate = _candidate_files(args.root)

    problems = []

    # 1. every baseline file present and byte-identical
    for rel, data in baseline.items():
        if rel not in candidate:
            problems.append("deleted inherited file: %s" % rel)
            continue
        with open(candidate[rel], "rb") as handle:
            if handle.read() != data:
                problems.append("inherited file modified: %s" % rel)

    # 2. every candidate file is either inherited or exactly allowlisted
    for rel in candidate:
        if rel in baseline:
            continue
        if rel not in allow:
            problems.append("unlisted addition: %s" % rel)

    # 3. every allowlisted addition is actually present
    for rel in allow:
        if rel not in candidate:
            problems.append("declared addition missing: %s" % rel)

    if problems:
        for p in sorted(problems):
            print("BASELINE_MISMATCH: %s" % p)
        print("MOVE_81_INHERITED_CHECK: FAIL (%d problem(s))" % len(problems))
        return 1

    inherited = len(baseline)
    additions = len(candidate) - inherited
    print("inherited baseline file members: %d" % inherited)
    print("byte-identical inherited files: %d" % inherited)
    print("declared additions (allowlist): %d" % len(allow))
    print("observed additions: %d" % additions)
    print("MOVE_81_INHERITED_CHECK: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
