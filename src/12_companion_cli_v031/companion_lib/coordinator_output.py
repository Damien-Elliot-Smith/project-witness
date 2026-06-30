"""Readers and a structural fallback verifier for a preserved Coordinator v0.3
output folder. The structural fallback lets Companion verify confirm the
Coordinator output without needing the Coordinator root or a subprocess.
"""

import os

from . import canonical, fixtures
from .errors import VerifyError

REQUIRED_FILES = (
    "workflow_report.json", "workflow_steps.json", "atlas_validation_report.json",
    "atlas_registry_copy.json", "workflow_checksums.txt",
)
REQUIRED_DIRS = (
    "sentinel_run", "histor_sentinel_case", "aletheia_bundle",
    "histor_aletheia_case", "bridge_output", "odin_output",
    "histor_odin_case", "case_bundle_v02",
)


def _require(cond, msg):
    if not cond:
        raise VerifyError(msg)


def read_workflow_report(coord_dir):
    return canonical.load_json(os.path.join(coord_dir, "workflow_report.json"))


def read_atlas_validation(coord_dir):
    return canonical.load_json(os.path.join(coord_dir, "atlas_validation_report.json"))


def read_registry(coord_dir):
    return canonical.load_json(os.path.join(coord_dir, "atlas_registry_copy.json"))


def structural_verify(coord_dir):
    """Structural fallback: confirm a preserved Coordinator v0.3 output is
    self-consistent (present, canonical, checksum-valid, completed)."""
    for f in REQUIRED_FILES:
        _require(os.path.isfile(os.path.join(coord_dir, f)),
                 "coordinator output missing file: %s" % f)
    for d in REQUIRED_DIRS:
        _require(os.path.isdir(os.path.join(coord_dir, d)),
                 "coordinator output missing folder: %s" % d)

    for f in ("workflow_report.json", "workflow_steps.json",
              "atlas_validation_report.json"):
        raw = canonical.read_bytes(os.path.join(coord_dir, f))
        _require(canonical.is_canonical_bytes(raw),
                 "coordinator %s not canonical" % f)
    copy_raw = canonical.read_bytes(os.path.join(coord_dir, "atlas_registry_copy.json"))
    _require(canonical.is_atlas_canonical_bytes(copy_raw),
             "coordinator atlas_registry_copy.json not canonical")

    _verify_coordinator_checksums(coord_dir)

    report = read_workflow_report(coord_dir)
    _require(report.get("workflow_status") == "WORKFLOW_COMPLETED",
             "coordinator workflow_status is not WORKFLOW_COMPLETED")
    steps = canonical.load_json(os.path.join(coord_dir, "workflow_steps.json"))
    got = steps.get("steps")
    _require(isinstance(got, list) and len(got) == 11,
             "coordinator steps malformed")
    _require(all(s.get("status") == "COMPLETED" for s in got),
             "coordinator has a non-COMPLETED step")
    return True


def _verify_coordinator_checksums(coord_dir):
    from .checksums import sha256_file
    text = canonical.read_bytes(
        os.path.join(coord_dir, "workflow_checksums.txt")).decode("utf-8")
    listed = {}
    valid = set(fixtures.COORD_PATHS)
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("  ")
        _require(len(parts) == 2, "coordinator checksum line malformed")
        digest, path = parts
        _require(digest == digest.lower() and len(digest) == 64,
                 "coordinator checksum digest invalid")
        _require(path in valid, "coordinator checksum unknown key: %s" % path)
        _require(path not in listed, "coordinator checksum duplicate key: %s" % path)
        listed[path] = digest
    for rel, digest in listed.items():
        full = os.path.join(coord_dir, rel)
        _require(os.path.isfile(full), "coordinator checksum missing file: %s" % rel)
        _require(sha256_file(full) == digest,
                 "coordinator checksum mismatch: %s" % rel)
