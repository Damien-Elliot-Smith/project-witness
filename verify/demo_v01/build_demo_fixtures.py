#!/usr/bin/env python3
"""Move 84 — demo fixture construction.

Builds the bundles the tamper-and-detect demonstration runs over, each
derived deterministically from the ADOPTED frozen reference bundle with
exactly one declared mutation.

Three cases, matching the binding rulings:

* `clean` — the frozen bundle, unmutated.
* `toplevel_tamper` — one byte flipped in a TOP-LEVEL declared file. This
  is the file set the adopted Rust hash stage genuinely verifies, so the
  Rust verifier detects it. **The reason code it returns is NOT declared
  here.** It is established by executing the adopted verifier.
* `nested_evidence_tamper` — one byte flipped in the genuine nested
  evidence payload `coordinator_output/aletheia_bundle/evidence/
  evidence_001.bin`, reproducing the adopted Move 80 case
  `M80-CHANGED-EVIDENCE-001` byte-for-byte. The Python lane detects this;
  the adopted Rust verifier does not, and that limit is the point.

Every mutation is verified independently after it is applied: the target
file's bytes must differ from the frozen original in exactly the declared
way, and every other file in the tree must remain byte-identical. No
expected Rust verdict is authored here.
"""

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys

# The nested evidence payload, from the frozen Move 71 generator.
NESTED_EVIDENCE = os.path.join(
    "coordinator_output", "aletheia_bundle", "evidence", "evidence_001.bin")

# A TOP-LEVEL declared file. Every entry of REQUIRED_HASH_PATHS is
# verified by the adopted Rust hash stage; this one is chosen because it
# is also the manifest the verifier parses first, so the demonstration
# exercises a file whose declared hash genuinely matters.
TOPLEVEL_DECLARED = "companion_steps.json"

# The frozen Move 71 byte-flip: offset 5, XOR 0xFF. Reused verbatim so the
# nested case reproduces the adopted fixture rather than inventing one.
FLIP_OFFSET = 5
FLIP_XOR = 0xFF

CASES = ("clean", "toplevel_tamper", "nested_evidence_tamper")

MUTATIONS = {
    "clean": None,
    "toplevel_tamper": TOPLEVEL_DECLARED,
    "nested_evidence_tamper": NESTED_EVIDENCE,
}


class DemoFixtureError(Exception):
    """Deterministic, message-only failure."""


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def tree_hashes(root):
    """Relative path -> sha256 for every regular file, sorted."""
    found = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            if os.path.islink(full) or not os.path.isfile(full):
                continue
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            found[rel] = sha256_file(full)
    return found


def flip_byte(path, offset=FLIP_OFFSET, value=FLIP_XOR):
    """Apply the frozen byte-flip and return (before, after)."""
    with open(path, "rb") as handle:
        data = bytearray(handle.read())
    if len(data) <= offset:
        raise DemoFixtureError(
            "%s is too short to flip offset %d" % (path, offset))
    before = data[offset]
    data[offset] ^= value
    after = data[offset]
    with open(path, "wb") as handle:
        handle.write(bytes(data))
    return before, after


def build_case(source_root, outdir, case_id):
    """Copy the frozen bundle and apply exactly the declared mutation."""
    if case_id not in MUTATIONS:
        raise DemoFixtureError("unknown case: %s" % case_id)
    dest = os.path.join(outdir, case_id)
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    shutil.copytree(source_root, dest, symlinks=True)

    before_hashes = tree_hashes(source_root)
    record = {"case_id": case_id, "root": dest,
              "mutated_path": MUTATIONS[case_id]}

    target = MUTATIONS[case_id]
    if target is None:
        record["mutation"] = None
    else:
        full = os.path.join(dest, target)
        if not os.path.isfile(full):
            raise DemoFixtureError(
                "%s: mutation target is absent: %s" % (case_id, target))
        before, after = flip_byte(full)
        record["mutation"] = {
            "path": target.replace(os.sep, "/"),
            "offset": FLIP_OFFSET,
            "operation": "xor",
            "operand": FLIP_XOR,
            "byte_before": before,
            "byte_after": after,
        }
        if before == after:
            raise DemoFixtureError(
                "%s: the flip did not change the byte" % case_id)

    # INDEPENDENT verification: exactly the declared file differs, and
    # every other file in the tree is byte-identical to the frozen source.
    after_hashes = tree_hashes(dest)
    if set(after_hashes) != set(before_hashes):
        raise DemoFixtureError(
            "%s: the file set changed; a fixture may only mutate content"
            % case_id)
    changed = sorted(rel for rel in before_hashes
                     if before_hashes[rel] != after_hashes[rel])
    expected_changed = ([] if target is None
                        else [target.replace(os.sep, "/")])
    if changed != expected_changed:
        raise DemoFixtureError(
            "%s: changed files are %s; exactly %s was declared"
            % (case_id, changed, expected_changed))
    record["changed_files"] = changed
    record["file_count"] = len(after_hashes)
    record["tree_digest"] = hashlib.sha256(
        json.dumps(after_hashes, sort_keys=True,
                   separators=(",", ":")).encode("utf-8")).hexdigest()
    if target is not None:
        record["target_sha256_before"] = before_hashes[
            target.replace(os.sep, "/")]
        record["target_sha256_after"] = after_hashes[
            target.replace(os.sep, "/")]
    return record


def build_all(source_root, outdir):
    if not os.path.isdir(source_root):
        raise DemoFixtureError("frozen bundle not found: %s" % source_root)
    os.makedirs(outdir, exist_ok=True)
    return [build_case(source_root, outdir, case_id) for case_id in CASES]


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Move 84 demo fixture construction")
    parser.add_argument("--source", required=True,
                        help="absolute path to the frozen reference bundle")
    parser.add_argument("--outdir", required=True,
                        help="absolute directory to build fixtures into")
    parser.add_argument("--manifest-out", default=None,
                        help="absolute path for the fixture manifest")
    args = parser.parse_args(argv)

    for label, path in (("--source", args.source),
                        ("--outdir", args.outdir)):
        if not os.path.isabs(path):
            print("usage error: %s must be absolute" % label)
            return 2
    if args.manifest_out and not os.path.isabs(args.manifest_out):
        print("usage error: --manifest-out must be absolute")
        return 2

    try:
        records = build_all(args.source, args.outdir)
    except (DemoFixtureError, OSError) as exc:
        print("DEMO_FIXTURES: FAIL (%s)" % exc)
        return 1

    payload = {"cases": records}
    if args.manifest_out:
        with open(args.manifest_out, "wb") as handle:
            handle.write((json.dumps(payload, sort_keys=True,
                                     separators=(",", ":"),
                                     ensure_ascii=False)
                          + "\n").encode("utf-8"))
    for record in records:
        mutation = record["mutation"]
        if mutation is None:
            print("DEMO_FIXTURE: %-24s unmutated (%d files)"
                  % (record["case_id"], record["file_count"]))
        else:
            print("DEMO_FIXTURE: %-24s %s offset %d %02x -> %02x"
                  % (record["case_id"], mutation["path"],
                     mutation["offset"], mutation["byte_before"],
                     mutation["byte_after"]))
    print("DEMO_FIXTURES: PASS (%d case(s))" % len(records))
    return 0


if __name__ == "__main__":
    sys.exit(main())
