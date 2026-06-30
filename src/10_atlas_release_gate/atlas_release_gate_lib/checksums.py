"""Strict checksum handling for the release-gate output folder."""

import hashlib
import os
import re

from . import canonical
from .errors import VerifyError

_HEX64 = re.compile(r"^[0-9a-f]{64}$")

# Fixed canonical relative paths, in fixed order.
REPORT_PATH = "atlas_release_gate_report.json"
STEPS_PATH = "atlas_release_gate_steps.json"
EXPORT_REGISTRY_COPY = "atlas_export/atlas_registry_copy.json"
EXPORT_SUMMARY = "atlas_export/atlas_summary.json"
EXPORT_CHECKSUMS = "atlas_export/atlas_checksums.txt"

CHECKSUMS_FILE = "atlas_release_gate_checksums.txt"

REQUIRED_PATHS = (
    REPORT_PATH,
    STEPS_PATH,
    EXPORT_REGISTRY_COPY,
    EXPORT_SUMMARY,
    EXPORT_CHECKSUMS,
)
_BASE_PATHS = (REPORT_PATH, STEPS_PATH)
_EXPORT_PATHS = (EXPORT_REGISTRY_COPY, EXPORT_SUMMARY, EXPORT_CHECKSUMS)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def present_canonical_paths(out_dir):
    """Return the canonical output paths that exist on disk, in fixed order.

    Report and steps are always included (they are written before checksums).
    The three export files are included only if all three are present.
    """
    paths = list(_BASE_PATHS)
    if all(os.path.isfile(os.path.join(out_dir, p)) for p in _EXPORT_PATHS):
        paths.extend(_EXPORT_PATHS)
    return paths


def build_checksums_text(out_dir, paths):
    lines = []
    for rel in paths:
        full = os.path.join(out_dir, rel)
        lines.append("%s  %s" % (sha256_file(full), rel))
    return ("\n".join(lines) + "\n").encode("utf-8")


def parse_checksums(text, expected_paths):
    """Parse and strictly validate a checksums file.

    Format per line: '<lowercase-sha256>  <relative-path>' (exactly two spaces).
    Enforces: required keys exactly once, no duplicates, no unknown keys,
    no missing keys, well-formed lowercase digests only.
    """
    if isinstance(text, (bytes, bytearray)):
        text = text.decode("utf-8")
    expected = set(expected_paths)
    result = {}
    for raw_line in text.splitlines():
        if raw_line.strip() == "":
            continue
        parts = raw_line.split("  ")
        if len(parts) != 2:
            raise VerifyError("malformed checksum line: %r" % raw_line)
        digest, path = parts[0], parts[1]
        if digest != digest.lower():
            raise VerifyError("uppercase digest not allowed: %r" % digest)
        if not _HEX64.match(digest):
            raise VerifyError("malformed digest: %r" % digest)
        if path not in expected:
            raise VerifyError("unknown checksum key: %r" % path)
        if path in result:
            raise VerifyError("duplicate checksum key: %r" % path)
        result[path] = digest
    missing = expected - set(result)
    if missing:
        raise VerifyError("missing checksum keys: %s" % sorted(missing))
    return result


def verify_checksums(out_dir, expected_paths):
    text = canonical.read_bytes(os.path.join(out_dir, CHECKSUMS_FILE))
    listed = parse_checksums(text, expected_paths)
    for rel, expected_digest in listed.items():
        actual = sha256_file(os.path.join(out_dir, rel))
        if actual != expected_digest:
            raise VerifyError("checksum mismatch for %s" % rel)
    return listed
