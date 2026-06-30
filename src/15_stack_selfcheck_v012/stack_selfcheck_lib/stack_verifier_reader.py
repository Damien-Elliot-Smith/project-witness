"""Optional structural verification of a Stack Verifier v0.1 output (read-only)."""

import os
import re

from . import canonical
from .errors import CheckError, FAILED_STACK_VERIFIER_OUTPUT

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
REPORT_FILE = "stack_verification_report.json"
STEPS_FILE = "stack_verification_steps.json"
CHECKSUMS_FILE = "stack_verification_checksums.txt"
REQUIRED_FILES = (REPORT_FILE, STEPS_FILE, CHECKSUMS_FILE)
CHECKSUM_KEYS = (REPORT_FILE, STEPS_FILE)


def _sha256(path):
    import hashlib
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_output(run):
    if not run or not os.path.isdir(run):
        raise CheckError(FAILED_STACK_VERIFIER_OUTPUT, "stack verifier run not found")
    for f in REQUIRED_FILES:
        if not os.path.isfile(os.path.join(run, f)):
            raise CheckError(FAILED_STACK_VERIFIER_OUTPUT, "missing %s" % f)
    for f in (REPORT_FILE, STEPS_FILE):
        if not canonical.is_canonical_bytes(canonical.read_bytes(os.path.join(run, f))):
            raise CheckError(FAILED_STACK_VERIFIER_OUTPUT, "%s not canonical" % f)
    _verify_checksums(run)
    report = canonical.load_json(os.path.join(run, REPORT_FILE))
    if report.get("stack_verification_status") != "STACK_VERIFIED":
        raise CheckError(FAILED_STACK_VERIFIER_OUTPUT, "stack_verification_status not STACK_VERIFIED")
    if report.get("truth_boundary_valid") is not True:
        raise CheckError(FAILED_STACK_VERIFIER_OUTPUT, "truth_boundary_valid not true")
    if report.get("atlas_vocabulary_valid") is not True:
        raise CheckError(FAILED_STACK_VERIFIER_OUTPUT, "atlas_vocabulary_valid not true")
    return True


def _verify_checksums(run):
    text = canonical.read_bytes(os.path.join(run, CHECKSUMS_FILE)).decode("utf-8")
    listed = {}
    valid = set(CHECKSUM_KEYS)
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("  ")
        if len(parts) != 2:
            raise CheckError(FAILED_STACK_VERIFIER_OUTPUT, "verifier checksum malformed")
        digest, path = parts
        if digest != digest.lower() or not _HEX64.match(digest):
            raise CheckError(FAILED_STACK_VERIFIER_OUTPUT, "verifier digest invalid")
        if path not in valid:
            raise CheckError(FAILED_STACK_VERIFIER_OUTPUT, "verifier unknown key: %s" % path)
        if path in listed:
            raise CheckError(FAILED_STACK_VERIFIER_OUTPUT, "verifier duplicate key: %s" % path)
        listed[path] = digest
    if set(listed) != valid:
        raise CheckError(FAILED_STACK_VERIFIER_OUTPUT, "verifier missing keys")
    for rel, digest in listed.items():
        full = os.path.join(run, rel)
        if not os.path.isfile(full) or _sha256(full) != digest:
            raise CheckError(FAILED_STACK_VERIFIER_OUTPUT, "verifier checksum mismatch: %s" % rel)
