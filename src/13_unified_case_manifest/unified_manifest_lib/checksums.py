"""Strict 2-key checksum handling for the unified manifest output folder."""

import hashlib
import os
import re

from . import canonical
from .errors import VerifyError

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
CHECKSUMS_FILE = "unified_manifest_checksums.txt"

REQUIRED_PATHS = ("unified_case_manifest.json", "source_index.json")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_checksums_text(out_dir):
    lines = ["%s  %s" % (sha256_file(os.path.join(out_dir, rel)), rel)
             for rel in REQUIRED_PATHS]
    return ("\n".join(lines) + "\n").encode("utf-8")


def parse_checksums(text):
    if isinstance(text, (bytes, bytearray)):
        text = text.decode("utf-8")
    expected = set(REQUIRED_PATHS)
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


def verify_checksums(out_dir):
    text = canonical.read_bytes(os.path.join(out_dir, CHECKSUMS_FILE))
    listed = parse_checksums(text)
    for rel, expected_digest in listed.items():
        if sha256_file(os.path.join(out_dir, rel)) != expected_digest:
            raise VerifyError("checksum mismatch for %s" % rel)
    return listed
