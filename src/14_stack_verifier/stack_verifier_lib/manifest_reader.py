"""Read and cross-check an optional Unified Case Manifest v0.1 output.
Read-only: never modifies the manifest output."""

import os

from . import canonical
from .errors import (CheckError, FAILED_MANIFEST_MISSING,
                     FAILED_MANIFEST_STRUCTURE_INVALID, FAILED_MANIFEST_CHECKSUMS,
                     FAILED_MANIFEST_MISMATCH)

MANIFEST_FILE = "unified_case_manifest.json"
SOURCE_INDEX_FILE = "source_index.json"
CHECKSUMS_FILE = "unified_manifest_checksums.txt"
REQUIRED_FILES = (MANIFEST_FILE, SOURCE_INDEX_FILE, CHECKSUMS_FILE)
CHECKSUM_KEYS = (MANIFEST_FILE, SOURCE_INDEX_FILE)

_MIRROR_STATUS_FIELDS = (
    "workflow_type", "action_type", "companion_status",
    "coordinator_workflow_status", "atlas_validation_status",
    "atlas_registry_status", "sentinel_status", "aletheia_status",
    "bridge_status", "odin_reasoning_status", "case_bundle_status",
)


def structural_verify(manifest_run):
    if not os.path.isdir(manifest_run):
        raise CheckError(FAILED_MANIFEST_MISSING, "manifest run not found")
    for f in REQUIRED_FILES:
        if not os.path.isfile(os.path.join(manifest_run, f)):
            raise CheckError(FAILED_MANIFEST_STRUCTURE_INVALID,
                             "manifest missing file: %s" % f)
    for f in (MANIFEST_FILE, SOURCE_INDEX_FILE):
        if not canonical.is_canonical_bytes(
                canonical.read_bytes(os.path.join(manifest_run, f))):
            raise CheckError(FAILED_MANIFEST_STRUCTURE_INVALID,
                             "manifest %s not canonical" % f)
    _verify_checksums(manifest_run)


def _verify_checksums(manifest_run):
    from .checksums import sha256_file
    text = canonical.read_bytes(
        os.path.join(manifest_run, CHECKSUMS_FILE)).decode("utf-8")
    listed = {}
    valid = set(CHECKSUM_KEYS)
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("  ")
        if len(parts) != 2:
            raise CheckError(FAILED_MANIFEST_CHECKSUMS, "manifest checksum line malformed")
        digest, path = parts
        if digest != digest.lower() or len(digest) != 64:
            raise CheckError(FAILED_MANIFEST_CHECKSUMS, "manifest digest invalid")
        if path not in valid:
            raise CheckError(FAILED_MANIFEST_CHECKSUMS, "manifest unknown key: %s" % path)
        if path in listed:
            raise CheckError(FAILED_MANIFEST_CHECKSUMS, "manifest duplicate key: %s" % path)
        listed[path] = digest
    missing = valid - set(listed)
    if missing:
        raise CheckError(FAILED_MANIFEST_CHECKSUMS, "manifest missing keys: %s" % sorted(missing))
    for rel, digest in listed.items():
        full = os.path.join(manifest_run, rel)
        if not os.path.isfile(full) or sha256_file(full) != digest:
            raise CheckError(FAILED_MANIFEST_CHECKSUMS, "manifest checksum mismatch: %s" % rel)


def load(manifest_run):
    return (canonical.load_json(os.path.join(manifest_run, MANIFEST_FILE)),
            canonical.load_json(os.path.join(manifest_run, SOURCE_INDEX_FILE)))


def cross_check(manifest, stack_fields, source_artifacts):
    if manifest.get("case_id") != stack_fields["case_id"]:
        raise CheckError(FAILED_MANIFEST_MISMATCH, "manifest case_id mismatch")
    if manifest.get("evidence_id") != stack_fields["evidence_id"]:
        raise CheckError(FAILED_MANIFEST_MISMATCH, "manifest evidence_id mismatch")
    for field in _MIRROR_STATUS_FIELDS:
        if manifest.get(field) != stack_fields.get(field):
            raise CheckError(FAILED_MANIFEST_MISMATCH,
                             "manifest status mismatch: %s" % field)
    # artifact hashes must match where comparable (same relative_path)
    source_by_path = {a["relative_path"]: a["sha256"] for a in source_artifacts}
    for art in manifest.get("source_artifacts", []):
        rel = art.get("relative_path")
        if rel in source_by_path and art.get("sha256") != source_by_path[rel]:
            raise CheckError(FAILED_MANIFEST_MISMATCH,
                             "manifest artifact hash mismatch: %s" % rel)
