"""Strict checksum handling for the Coordinator v0.3 output folder."""

import hashlib
import os
import re

from . import canonical
from .errors import VerifyError

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
CHECKSUMS_FILE = "workflow_checksums.txt"

# Fixed canonical relative paths, in fixed order. The "keys" are these paths.
REQUIRED_PATHS = (
    "workflow_request_copy.json",
    "workflow_report.json",
    "workflow_steps.json",
    "atlas_validation_report.json",
    "atlas_registry_copy.json",
    "sentinel_run/run_report.json",
    "histor_sentinel_case/case_summary.json",
    "aletheia_bundle/evidence_manifest.json",
    "histor_aletheia_case/evidence_case_summary.json",
    "bridge_output/odin_claims.json",
    "odin_output/reasoning_report.json",
    "histor_odin_case/odin_case_summary.json",
    "case_bundle_v02/case_manifest.json",
)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def present_paths(out_dir):
    """Required canonical paths that currently exist on disk, in fixed order."""
    return [p for p in REQUIRED_PATHS if os.path.isfile(os.path.join(out_dir, p))]


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_checksums_text(out_dir, paths):
    lines = []
    for rel in paths:
        lines.append("%s  %s" % (sha256_file(os.path.join(out_dir, rel)), rel))
    return ("\n".join(lines) + "\n").encode("utf-8")


def parse_checksums(text, expected_paths):
    """Parse and strictly validate. Each line: '<lowercase-sha256>  <path>'."""
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
        if sha256_file(os.path.join(out_dir, rel)) != expected_digest:
            raise VerifyError("checksum mismatch for %s" % rel)
    return listed
