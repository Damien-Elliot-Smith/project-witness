"""Structural and checksum verification of a source case output."""

import os

from . import canonical, versions, source_reader
from .errors import (CheckError, FAILED_SOURCE_STRUCTURE_INVALID,
                     FAILED_SOURCE_CHECKSUMS)


def verify_structure(source_type, source_run, coord_dir):
    for f in ("workflow_report.json", "workflow_steps.json",
              "atlas_validation_report.json"):
        if not canonical.is_canonical_bytes(
                canonical.read_bytes(os.path.join(coord_dir, f))):
            raise CheckError(FAILED_SOURCE_STRUCTURE_INVALID,
                             "coordinator %s not canonical" % f)
    if not canonical.is_atlas_canonical_bytes(
            canonical.read_bytes(os.path.join(coord_dir, "atlas_registry_copy.json"))):
        raise CheckError(FAILED_SOURCE_STRUCTURE_INVALID,
                         "atlas_registry_copy.json not canonical")
    report = canonical.load_json(os.path.join(coord_dir, "workflow_report.json"))
    if report.get("workflow_status") != "WORKFLOW_COMPLETED":
        raise CheckError(FAILED_SOURCE_STRUCTURE_INVALID,
                         "coordinator workflow_status not WORKFLOW_COMPLETED")
    steps = canonical.load_json(os.path.join(coord_dir, "workflow_steps.json"))
    got = steps.get("steps")
    if not isinstance(got, list) or len(got) != 11 \
            or not all(s.get("status") == "COMPLETED" for s in got):
        raise CheckError(FAILED_SOURCE_STRUCTURE_INVALID,
                         "coordinator steps not all completed")
    if source_type == versions.SOURCE_TYPE_COMPANION:
        for f in ("companion_report.json", "companion_steps.json",
                  "workflow_request.json"):
            if not canonical.is_canonical_bytes(
                    canonical.read_bytes(os.path.join(source_run, f))):
                raise CheckError(FAILED_SOURCE_STRUCTURE_INVALID,
                                 "companion %s not canonical" % f)
        creport = canonical.load_json(os.path.join(source_run, "companion_report.json"))
        if creport.get("companion_status") != "COMPANION_COMPLETED":
            raise CheckError(FAILED_SOURCE_STRUCTURE_INVALID,
                             "companion_status not COMPANION_COMPLETED")


def _verify_listing(folder, listing_file, valid_paths):
    from .checksums import sha256_file
    text = canonical.read_bytes(os.path.join(folder, listing_file)).decode("utf-8")
    listed = {}
    valid = set(valid_paths)
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("  ")
        if len(parts) != 2:
            raise CheckError(FAILED_SOURCE_CHECKSUMS, "source checksum line malformed")
        digest, path = parts
        if digest != digest.lower() or len(digest) != 64:
            raise CheckError(FAILED_SOURCE_CHECKSUMS, "source checksum digest invalid")
        if path not in valid:
            raise CheckError(FAILED_SOURCE_CHECKSUMS, "source checksum unknown key: %s" % path)
        if path in listed:
            raise CheckError(FAILED_SOURCE_CHECKSUMS, "source checksum duplicate: %s" % path)
        listed[path] = digest
    for rel, digest in listed.items():
        full = os.path.join(folder, rel)
        if not os.path.isfile(full) or sha256_file(full) != digest:
            raise CheckError(FAILED_SOURCE_CHECKSUMS, "source checksum mismatch: %s" % rel)


def verify_checksums(source_type, source_run, coord_dir):
    _verify_listing(coord_dir, "workflow_checksums.txt",
                    source_reader.COORD_CHECKSUM_PATHS)
    if source_type == versions.SOURCE_TYPE_COMPANION:
        _verify_listing(source_run, "companion_checksums.txt",
                        source_reader.COMPANION_CHECKSUM_PATHS)
