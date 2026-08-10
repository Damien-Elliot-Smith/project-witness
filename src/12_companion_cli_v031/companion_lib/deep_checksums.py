"""Deep integrity verification for a Companion output folder (v0.3.2 repair).

Repairs RT-004: `companion verify` previously hash-checked only the eight
top-level REQUIRED_PATHS and never recursed into nested component checksum
files, so tampered evidence bytes inside the Aletheia bundle (or any other
nested component output) still verified as ok at the Companion layer.

This module adds two read-only deep passes:

1. Nested checksum files: every file named `*checksums.txt` anywhere under
   the output folder (except the top-level `companion_checksums.txt`, which
   is already verified strictly) is parsed and every entry it lists is
   re-hashed. Two line formats are accepted, matching the formats produced
   by the frozen components:
       <sha256-hex>  <relative-path>                    (standard)
       <label>  <sha256-hex>  <relative-path>           (Sentinel case)
   Listed paths are resolved relative to the checksum file's own directory
   and must stay inside it.

2. Aletheia manifest binding: if
   `coordinator_output/aletheia_bundle/evidence_manifest.json` exists and
   declares `bundled_file_sha256`, the declared bundled file must exist and
   its hash must match. This catches the checksums-file fix-up attack,
   where an attacker rewrites both the evidence bytes and the checksum
   entry but not the manifest.

Honesty boundary (unchanged): these passes prove hash consistency of the
recorded run only. They do not prove evidence contents are true, and
whole-folder fabrication remains possible without signing.
"""

import os
import re

from . import canonical
from .checksums import sha256_file
from .errors import VerifyError

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_TOP_LEVEL_CHECKSUMS = "companion_checksums.txt"
_ALETHEIA_MANIFEST_REL = os.path.join(
    "coordinator_output", "aletheia_bundle", "evidence_manifest.json")


def _require(cond, msg):
    if not cond:
        raise VerifyError(msg)


def _safe_join(base_dir, rel):
    """Join rel onto base_dir, refusing traversal, absolute and unsafe paths."""
    _require(isinstance(rel, str) and rel != "", "empty path in checksum entry")
    _require("\\" not in rel, "backslash path in checksum entry: %r" % rel)
    _require(not rel.startswith("/"), "absolute path in checksum entry: %r" % rel)
    parts = rel.split("/")
    _require("" not in parts, "empty path segment in checksum entry: %r" % rel)
    _require(".." not in parts, "path traversal in checksum entry: %r" % rel)
    joined = os.path.join(base_dir, *parts)
    real_base = os.path.realpath(base_dir)
    real_joined = os.path.realpath(joined)
    _require(real_joined == real_base or
             real_joined.startswith(real_base + os.sep),
             "checksum entry escapes its directory: %r" % rel)
    return joined


def _parse_line(raw_line, source_rel):
    """Return (digest, rel_path, labeled) from a 2- or 3-field checksum line."""
    parts = raw_line.split("  ")
    if len(parts) == 2:
        digest, rel, labeled = parts[0], parts[1], False
    elif len(parts) == 3:
        digest, rel, labeled = parts[1], parts[2], True
    else:
        raise VerifyError("malformed line in %s: %r" % (source_rel, raw_line))
    _require(digest == digest.lower(),
             "uppercase digest in %s: %r" % (source_rel, digest))
    _require(_HEX64.match(digest) is not None,
             "malformed digest in %s: %r" % (source_rel, digest))
    return digest, rel, labeled


def find_nested_checksum_files(out_dir):
    """Deterministically list nested checksum files under out_dir."""
    found = []
    for root, dirs, files in os.walk(out_dir):
        dirs.sort()
        for name in sorted(files):
            if not name.endswith("checksums.txt"):
                continue
            rel = os.path.relpath(os.path.join(root, name), out_dir)
            if rel == _TOP_LEVEL_CHECKSUMS:
                continue
            found.append(rel)
    return found


def verify_nested_checksums(out_dir):
    """Verify every entry of every nested checksum file. Returns count checked.

    Two-field entries list sibling files and are verified strictly. Three-
    field labeled entries (the Sentinel case format) may record provenance
    hashes of files that are not siblings: if the sibling is absent, the
    entry is bound against the documented source-run location
    (coordinator_output/sentinel_run/<name>) when that file exists; if it
    exists nowhere, the entry is a recorded provenance hash only, which
    cannot be re-verified here and is skipped without failure.
    """
    checked = 0
    for rel in find_nested_checksum_files(out_dir):
        source_path = os.path.join(out_dir, rel)
        base_dir = os.path.dirname(source_path)
        text = canonical.read_bytes(source_path).decode("utf-8")
        seen = set()
        for raw_line in text.splitlines():
            if raw_line.strip() == "":
                continue
            digest, entry_rel, labeled = _parse_line(raw_line, rel)
            _require(entry_rel not in seen,
                     "duplicate entry in %s: %r" % (rel, entry_rel))
            seen.add(entry_rel)
            target = _safe_join(base_dir, entry_rel)
            if not os.path.isfile(target):
                if labeled:
                    source_run = os.path.join(
                        out_dir, "coordinator_output", "sentinel_run")
                    bound = _safe_join(source_run, entry_rel) \
                        if os.path.isdir(source_run) else None
                    if bound is not None and os.path.isfile(bound):
                        _require(sha256_file(bound) == digest,
                                 "recorded source hash in %s does not match "
                                 "%r" % (rel, entry_rel))
                        checked += 1
                    continue
                raise VerifyError(
                    "file listed in %s is missing: %r" % (rel, entry_rel))
            if sha256_file(target) != digest:
                _require(_raw_manifest_fallback(base_dir, entry_rel, digest),
                         "deep checksum mismatch for %r (listed in %s)"
                         % (entry_rel, rel))
            checked += 1
    return checked


def _raw_manifest_fallback(base_dir, entry_rel, digest):
    """Accept the Coordinator's documented case_manifest replacement.

    Coordinator Workflow v0.3 replaces the Case Bundle's case_manifest.json
    with a compatibility summary and preserves the original bytes as
    raw_case_bundle_manifest.json (declaring this in the summary itself).
    bundle_checksums.txt therefore lists the ORIGINAL manifest's hash under
    the old name. The fallback stays tamper-evident: the listed digest must
    match the preserved raw manifest exactly, and the replacement summary
    must explicitly declare the preservation. Anything else is a failure.
    """
    if entry_rel != "case_manifest.json":
        return False
    summary_path = os.path.join(base_dir, "case_manifest.json")
    raw_path = os.path.join(base_dir, "raw_case_bundle_manifest.json")
    if not (os.path.isfile(summary_path) and os.path.isfile(raw_path)):
        return False
    try:
        summary = canonical.load_json(summary_path)
    except (OSError, ValueError):
        return False
    if not isinstance(summary, dict):
        return False
    if summary.get("raw_case_bundle_manifest_preserved") is not True:
        return False
    if summary.get("raw_case_bundle_manifest") != "raw_case_bundle_manifest.json":
        return False
    return sha256_file(raw_path) == digest


def verify_aletheia_manifest_binding(out_dir):
    """Verify evidence_manifest.json's bundled_file_sha256 against the file.

    Returns True if the binding was present and checked, False if the
    manifest is absent or declares no bundled-file hash (older or fixture
    layouts). A declared binding that cannot be satisfied is a failure.
    """
    manifest_path = os.path.join(out_dir, _ALETHEIA_MANIFEST_REL)
    if not os.path.isfile(manifest_path):
        return False
    manifest = canonical.load_json(manifest_path)
    _require(isinstance(manifest, dict),
             "evidence_manifest.json is not a JSON object")
    declared = manifest.get("bundled_file_sha256")
    if declared is None:
        return False
    _require(isinstance(declared, str) and _HEX64.match(declared) is not None,
             "malformed bundled_file_sha256 in evidence_manifest.json")
    bundled_rel = manifest.get("bundled_file_path")
    _require(isinstance(bundled_rel, str) and bundled_rel != "",
             "bundled_file_sha256 declared without bundled_file_path")
    bundle_dir = os.path.dirname(manifest_path)
    target = _safe_join(bundle_dir, bundled_rel)
    _require(os.path.isfile(target),
             "bundled file declared in evidence_manifest.json is missing: %r"
             % bundled_rel)
    _require(sha256_file(target) == declared,
             "manifest bundled_file_sha256 does not match bundled file %r"
             % bundled_rel)
    return True


def verify_evidence_dir_completeness(out_dir):
    """Fail if the Aletheia evidence directory contains unlisted files.

    The evidence directory is a closed set: every file under
    coordinator_output/aletheia_bundle/evidence/ must appear in
    evidence_checksums.txt. A file planted there without a checksum entry
    is an integrity failure (evidence added unexpectedly), because a
    reader of the bundle would reasonably treat anything in the evidence
    directory as recorded evidence. Returns the number of evidence files
    accounted for; absent layouts return 0 without failure.
    """
    bundle_dir = os.path.join(out_dir, "coordinator_output",
                              "aletheia_bundle")
    sums_path = os.path.join(bundle_dir, "evidence_checksums.txt")
    evidence_dir = os.path.join(bundle_dir, "evidence")
    if not (os.path.isfile(sums_path) and os.path.isdir(evidence_dir)):
        return 0
    listed = set()
    text = canonical.read_bytes(sums_path).decode("utf-8")
    for raw_line in text.splitlines():
        if raw_line.strip() == "":
            continue
        _digest, entry_rel, _labeled = _parse_line(
            raw_line, "evidence_checksums.txt")
        if entry_rel.startswith("evidence/"):
            listed.add(entry_rel[len("evidence/"):])
    actual = set()
    for root, dirs, files in os.walk(evidence_dir):
        dirs.sort()
        for name in sorted(files):
            rel = os.path.relpath(os.path.join(root, name), evidence_dir)
            actual.add(rel.replace(os.sep, "/"))
    unlisted = sorted(actual - listed)
    _require(not unlisted,
             "unlisted file(s) in evidence directory: %s" % unlisted[:5])
    return len(actual)


def verify_deep(out_dir):
    """Run all deep passes. Raises VerifyError on any integrity failure."""
    checked = verify_nested_checksums(out_dir)
    verify_aletheia_manifest_binding(out_dir)
    verify_evidence_dir_completeness(out_dir)
    return checked
