#!/usr/bin/env python3
"""Move 84 baseline-immutability checker.

Compares the candidate tree against the REAL adopted Move 83 v13 ZIP,
member by member, and requires:

  * every file inherited from the Move 83 v13 baseline is byte-identical
    to its member bytes in the real ZIP;
  * every file present in the candidate but not in the baseline is
    exactly on the Move 84 allowlist (added_paths);
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
    anything outside the single expected root. Mirrors the adopted Move 81
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


FORBIDDEN_LIVE_DIRS = ("__pycache__",)


def verify_tree_matches_zip(zip_path, root):
    """Prove the LIVE tree is byte-identical to the verified archive.

    Uses lstat semantics throughout: a symlink whose TARGET happens to
    contain matching bytes is not the reviewed file, and following it
    would let an attacker substitute content while the comparison
    reported success. Every packaged path must be a regular live file.

    Cache and build directories are REJECTED rather than ignored: at this
    pre-build stage a __pycache__, .pyc or rust/target must not exist, so
    silently skipping them would hide state that could influence the
    build."""
    problems = []
    with zipfile.ZipFile(zip_path) as zf:
        safety = inspect_zip_safety(zf)
        if safety:
            return ["candidate zip failed safety inspection: %s" % p
                    for p in sorted(safety)]
        members = {}
        modes = {}
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
            modes[rel] = (info.external_attr >> 16) & 0o7777

        live = {}
        for dirpath, dirnames, filenames in os.walk(root):
            for d in list(dirnames):
                full = os.path.join(dirpath, d)
                rel = os.path.relpath(full, root).replace(os.sep, "/")
                if os.path.islink(full):
                    problems.append("live symlink directory present: %s"
                                    % rel)
                    dirnames.remove(d)
                    continue
                if d in FORBIDDEN_LIVE_DIRS:
                    problems.append(
                        "cache directory present before build: %s" % rel)
                    dirnames.remove(d)
                    continue
                if rel == "rust/target" or rel.startswith("rust/target/"):
                    problems.append(
                        "build directory present before build: %s" % rel)
                    dirnames.remove(d)
            for name in filenames:
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, root).replace(os.sep, "/")
                st = os.lstat(full)
                if stat.S_ISLNK(st.st_mode):
                    problems.append("live symlink present: %s" % rel)
                    continue
                if not stat.S_ISREG(st.st_mode):
                    problems.append("non-regular live file present: %s"
                                    % rel)
                    continue
                if name.endswith(".pyc"):
                    problems.append("bytecode present before build: %s"
                                    % rel)
                    continue
                live[rel] = (full, st)

        for rel, data in members.items():
            if rel not in live:
                problems.append("packaged file missing from live tree: %s"
                                % rel)
                continue
            full, st = live[rel]
            with open(full, "rb") as handle:
                if handle.read() != data:
                    problems.append(
                        "live file differs from candidate member: %s" % rel)
                    continue
            packaged_mode = modes.get(rel, 0)
            if packaged_mode:
                # EXACT permission bits, not merely executable-or-not: a
                # packaged 0644 against a live 0600 is real drift.
                if (packaged_mode & 0o777) != (st.st_mode & 0o777):
                    problems.append(
                        "mode differs from candidate member: %s "
                        "(packaged %04o, live %04o)"
                        % (rel, packaged_mode & 0o777, st.st_mode & 0o777))

        for rel in live:
            if rel not in members:
                problems.append("unlisted live file not in candidate: %s"
                                % rel)

        # The COMPLETE path set, including directory entries: an extra
        # empty live directory has no packaged counterpart and must fail.
        packaged_dirs = set()
        for name in zf.namelist():
            if "/" not in name:
                continue
            rel = name.split("/", 1)[1]
            if not rel:
                continue
            parts = rel.rstrip("/").split("/")
            for i in range(1, len(parts) + (1 if name.endswith("/") else 0)):
                packaged_dirs.add("/".join(parts[:i]))
        for dirpath, _dn, _fn in os.walk(root):
            rel = os.path.relpath(dirpath, root).replace(os.sep, "/")
            if rel == ".":
                continue
            if rel not in packaged_dirs:
                problems.append("unlisted live directory not in candidate: "
                                "%s" % rel)

    return problems


IGNORED_LIVE_DIRS = ("__pycache__", "target")
IGNORED_LIVE_SUFFIXES = (".pyc",)


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


def _is_strictly_additive(adopted_bytes, live_bytes):
    """True when `live` is `adopted` with lines ADDED and none changed or
    removed: every adopted line must appear in the live file, in order."""
    adopted = adopted_bytes.split(b"\n")
    live = live_bytes.split(b"\n")
    index = 0
    for line in adopted:
        found = False
        while index < len(live):
            if live[index] == line:
                index += 1
                found = True
                break
            index += 1
        if not found:
            return False
    return True


def zip_member_modes(zip_path):
    """Mode metadata for every file member of the baseline archive, so an
    inherited executable bit change is detected as well as a byte change."""
    modes = {}
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename
            if "/" not in name:
                continue
            rel = name.split("/", 1)[1]
            if rel:
                modes[rel] = (info.external_attr >> 16) & 0o7777
    return modes


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


SHARED_STORAGE_PATTERNS = (
    "/storage/downloads", "/storage/emulated", "/storage/shared",
    "/sdcard",
)
DOWNLOAD_DIR_NAMES = ("download", "downloads")


def validate_output_dir(supplied, run_dir, candidate_root):
    """Validate MOVE82_OUTPUT_DIR. Factored out of the gate so the rules
    are EXECUTABLE and testable rather than asserted by reading shell
    source. This is the production path the gate calls -- not a test-only
    reimplementation, and not a bypass.

    Returns a list of problems; empty means acceptable."""
    problems = []
    if not supplied or not os.path.isabs(supplied):
        problems.append("output directory must be absolute as supplied")
        return problems
    if os.path.islink(supplied):
        problems.append("output directory is a symlink")
        return problems
    if not os.path.isdir(supplied):
        problems.append("output directory is not a pre-created directory")
        return problems
    real = os.path.realpath(supplied)
    lowered = real.lower()
    for marker in SHARED_STORAGE_PATTERNS:
        if lowered == marker or lowered.startswith(marker + "/") \
                or ("/" + marker.strip("/") + "/") in lowered + "/":
            problems.append("output directory is under Android shared "
                            "storage: %s" % marker)
            break
    parts = [p for p in lowered.split("/") if p]
    if any(p in DOWNLOAD_DIR_NAMES for p in parts):
        problems.append("output directory is under a Downloads path")
    if os.listdir(real):
        problems.append("output directory is not empty")
    candidate_real = os.path.realpath(candidate_root)
    if real == candidate_real or real.startswith(candidate_real + os.sep):
        problems.append("output directory is inside the candidate source "
                        "root")
    run_real = os.path.realpath(run_dir)
    if not real.startswith(run_real + os.sep):
        problems.append("output directory is not inside the internal run "
                        "directory")
    return problems


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
    parser = argparse.ArgumentParser(description="Move 84 baseline check")
    parser.add_argument("--baseline-zip", required=False,
                        default="")
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
    parser.add_argument("--check-output-dir", default=None)
    parser.add_argument("--run-dir", default=None)
    parser.add_argument("--candidate-root", default=None)
    parser.add_argument(
        "--verify-tree-matches-zip", default=None,
        help="absolute path to the LIVE tree that must be byte-identical "
             "to the verified candidate archive")
    args = parser.parse_args(argv)

    if args.check_output_dir is not None:
        if not args.run_dir or not args.candidate_root:
            print("usage error: --check-output-dir needs --run-dir and "
                  "--candidate-root")
            return 2
        problems = validate_output_dir(
            args.check_output_dir, args.run_dir, args.candidate_root)
        for problem in sorted(problems):
            print("OUTPUT_DIR_PROBLEM: %s" % problem)
        if problems:
            print("MOVE_84_OUTPUT_DIR: FAIL (%d problem(s))"
                  % len(problems))
            return 1
        print("MOVE_84_OUTPUT_DIR: PASS")
        return 0

    if not os.path.isfile(args.baseline_zip):
        print("usage error: --baseline-zip is not a file: %s"
              % args.baseline_zip)
        return 2
    if args.verify_tree_matches_zip is not None:
        if not os.path.isabs(args.verify_tree_matches_zip) \
                or not os.path.isdir(args.verify_tree_matches_zip):
            print("usage error: --verify-tree-matches-zip must be an "
                  "absolute directory")
            return 2
    elif args.extract_to is None:
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
            print("MOVE_84_INHERITED_CHECK: FAIL (baseline hash mismatch; "
                  "extraction and comparison not attempted)")
            return 1
        print("REAL_MOVE83 independently matched --expect-sha256 in the "
              "baseline checker:")
        print(args.expect_sha256)

    if args.verify_tree_matches_zip is not None:
        problems = verify_tree_matches_zip(
            args.baseline_zip, args.verify_tree_matches_zip)
        if problems:
            for problem in sorted(problems):
                print("SOURCE_BINDING_MISMATCH: %s" % problem)
            print("MOVE_84_SOURCE_BINDING: FAIL (%d problem(s))"
                  % len(problems))
            return 1
        print("live tree is byte-identical to the verified candidate "
              "archive in both directions")
        print("MOVE_84_SOURCE_BINDING: PASS")
        return 0

    if args.extract_to is not None:
        root = extract_baseline(args.baseline_zip, args.extract_to)
        if root is None:
            print("MOVE_84_BASELINE_EXTRACT: FAIL")
            return 1
        print("EXTRACTED_ROOT: %s" % root)
        print("MOVE_84_BASELINE_EXTRACT: PASS")
        return 0

    try:
        with open(args.allowlist, encoding="utf-8") as handle:
            data = json.load(handle)
        allow = set(data["added_paths"])
    except (ValueError, OSError, KeyError, TypeError):
        print("usage error: --allowlist is not a readable allowlist "
              "document with an added_paths list")
        return 2
    if not all(isinstance(item, str) and item for item in allow):
        print("usage error: --allowlist added_paths must be non-empty "
              "strings")
        return 2

    baseline = _zip_members(args.baseline_zip)
    # Move 84 is ADDITIVE ONLY. Move 83's single additive main.rs
    # modification was a one-off authorisation; Move 84 has none, so this
    # must be empty and any inherited change is a failure.
    allowed_modifications = set(data.get("modified_paths", []))
    if allowed_modifications:
        problems.append(
            "Move 84 declares modified_paths, but no inherited "
            "modification is authorised")
    additive_modifications = []
    baseline_modes = zip_member_modes(args.baseline_zip)
    candidate = _candidate_files(args.root)

    problems = []

    # 1. every baseline file present and byte-identical
    for rel, data in baseline.items():
        if rel not in candidate:
            problems.append("deleted inherited file: %s" % rel)
            continue
        with open(candidate[rel], "rb") as handle:
            live = handle.read()
        if live != data:
            if rel not in allowed_modifications:
                problems.append("inherited file modified: %s" % rel)
                continue
            # Move 84 is the first move authorised to modify an inherited
            # file. A declared modification must be STRICTLY ADDITIVE:
            # removing the added lines must reproduce the adopted bytes
            # exactly, so nothing adopted can be altered or deleted under
            # cover of an addition.
            if not _is_strictly_additive(data, live):
                problems.append(
                    "declared modification to %s is not strictly additive: "
                    "adopted lines were changed or removed" % rel)
            else:
                additive_modifications.append(rel)
            continue
        packaged_mode = baseline_modes.get(rel, 0)
        if packaged_mode:
            live_mode = os.lstat(candidate[rel]).st_mode
            if (packaged_mode & 0o777) != (live_mode & 0o777):
                problems.append(
                    "inherited mode changed: %s (adopted %04o, live %04o)"
                    % (rel, packaged_mode & 0o777, live_mode & 0o777))

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
        print("MOVE_84_INHERITED_CHECK: FAIL (%d problem(s))" % len(problems))
        return 1

    inherited = len(baseline)
    additions = len(candidate) - inherited
    modified = sorted(additive_modifications)
    print("inherited baseline file members: %d" % inherited)
    print("byte-identical inherited files: %d" % (inherited - len(modified)))
    print("declared additive modifications: %d" % len(modified))
    for rel in modified:
        print("  strictly additive (every adopted line preserved in "
              "order): %s" % rel)
    unused = sorted(allowed_modifications - set(modified))
    for rel in unused:
        print("  declared modification not observed (file is unchanged): "
              "%s" % rel)
    print("declared additions (allowlist): %d" % len(allow))
    print("observed additions: %d" % additions)
    print("MOVE_84_INHERITED_CHECK: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
