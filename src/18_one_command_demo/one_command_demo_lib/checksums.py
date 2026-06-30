"""Strict two-key checksum file build and verify. Lowercase SHA-256 only."""

import hashlib
import os
import re

from .errors import VerifyError

REPORT_FILE = "one_command_demo_report.json"
STEPS_FILE = "one_command_demo_steps.json"
CHECKSUMS_FILE = "one_command_demo_checksums.txt"

_REQUIRED_KEYS = (REPORT_FILE, STEPS_FILE)
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        h.update(handle.read())
    return h.hexdigest()


def build_checksums_text(out_dir):
    lines = []
    for name in _REQUIRED_KEYS:
        lines.append("%s  %s" % (_sha256(os.path.join(out_dir, name)), name))
    return ("\n".join(lines) + "\n").encode("utf-8")


def verify_checksums(out_dir):
    path = os.path.join(out_dir, CHECKSUMS_FILE)
    if not os.path.isfile(path):
        raise VerifyError("missing checksums file")
    with open(path, "r", encoding="utf-8") as handle:
        raw = handle.read()
    seen = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("  ")
        if len(parts) != 2:
            raise VerifyError("malformed checksum line: %r" % line)
        digest, name = parts[0], parts[1]
        if not _DIGEST.match(digest):
            raise VerifyError("malformed or non-lowercase digest: %r" % digest)
        if name in seen:
            raise VerifyError("duplicate checksum key: %s" % name)
        seen[name] = digest
    if set(seen) != set(_REQUIRED_KEYS):
        raise VerifyError("checksum keys must be exactly %s, got %s"
                          % (sorted(_REQUIRED_KEYS), sorted(seen)))
    for name, digest in seen.items():
        actual = _sha256(os.path.join(out_dir, name))
        if actual != digest:
            raise VerifyError("checksum mismatch for %s" % name)
