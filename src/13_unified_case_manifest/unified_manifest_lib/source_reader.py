"""Locate, structurally verify, and read an existing Coordinator v0.3 or
Companion v0.3 case output. Read-only: never modifies the source."""

import os

from . import canonical, versions
from .errors import (BuildError, FAILED_SOURCE_MISSING,
                     FAILED_SOURCE_STRUCTURE_INVALID, FAILED_SOURCE_VERIFY)

# Coordinator v0.3 output shape (relative to the Coordinator output dir).
COORD_REQUIRED_FILES = (
    "workflow_report.json", "workflow_steps.json", "atlas_validation_report.json",
    "atlas_registry_copy.json", "workflow_checksums.txt",
)
COORD_REQUIRED_DIRS = (
    "sentinel_run", "histor_sentinel_case", "aletheia_bundle",
    "histor_aletheia_case", "bridge_output", "odin_output",
    "histor_odin_case", "case_bundle_v02",
)
COORD_CHECKSUM_PATHS = (
    "workflow_request_copy.json", "workflow_report.json", "workflow_steps.json",
    "atlas_validation_report.json", "atlas_registry_copy.json",
    "sentinel_run/run_report.json", "histor_sentinel_case/case_summary.json",
    "aletheia_bundle/evidence_manifest.json",
    "histor_aletheia_case/evidence_case_summary.json",
    "bridge_output/odin_claims.json", "odin_output/reasoning_report.json",
    "histor_odin_case/odin_case_summary.json",
    "case_bundle_v02/case_manifest.json",
)
COMPANION_REQUIRED_FILES = (
    "workflow_request.json", "companion_report.json", "companion_steps.json",
    "companion_checksums.txt",
)


def _fail(status, msg):
    raise BuildError(status, msg)


def locate_coordinator_dir(source_type, source_run):
    if not os.path.isdir(source_run):
        _fail(FAILED_SOURCE_MISSING, "source root not found: %s" % source_run)
    if source_type == versions.SOURCE_TYPE_COORDINATOR:
        return source_run, ""
    coord = os.path.join(source_run, "coordinator_output")
    if not os.path.isdir(coord):
        _fail(FAILED_SOURCE_MISSING, "companion source missing coordinator_output/")
    return coord, "coordinator_output/"


def check_required_source_files(source_type, source_run, coord_dir):
    for f in COORD_REQUIRED_FILES:
        if not os.path.isfile(os.path.join(coord_dir, f)):
            _fail(FAILED_SOURCE_STRUCTURE_INVALID,
                  "missing coordinator source file: %s" % f)
    for d in COORD_REQUIRED_DIRS:
        if not os.path.isdir(os.path.join(coord_dir, d)):
            _fail(FAILED_SOURCE_STRUCTURE_INVALID,
                  "missing coordinator source folder: %s" % d)
    for rel in ("case_bundle_v02/case_manifest.json",
                "odin_output/reasoning_report.json",
                "bridge_output/odin_claims.json",
                "aletheia_bundle/evidence_manifest.json",
                "histor_sentinel_case/case_summary.json",
                "histor_aletheia_case/evidence_case_summary.json",
                "histor_odin_case/odin_case_summary.json",
                "sentinel_run/run_report.json"):
        if not os.path.isfile(os.path.join(coord_dir, rel)):
            _fail(FAILED_SOURCE_STRUCTURE_INVALID,
                  "missing coordinator source file: %s" % rel)
    if source_type == versions.SOURCE_TYPE_COMPANION:
        for f in COMPANION_REQUIRED_FILES:
            if not os.path.isfile(os.path.join(source_run, f)):
                _fail(FAILED_SOURCE_STRUCTURE_INVALID,
                      "missing companion source file: %s" % f)


def _checksum_verify(folder, listing_file, valid_paths):
    from .checksums import sha256_file
    text = canonical.read_bytes(os.path.join(folder, listing_file)).decode("utf-8")
    listed = {}
    valid = set(valid_paths)
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("  ")
        if len(parts) != 2:
            _fail(FAILED_SOURCE_VERIFY, "source checksum line malformed")
        digest, path = parts
        if digest != digest.lower() or len(digest) != 64:
            _fail(FAILED_SOURCE_VERIFY, "source checksum digest invalid")
        if path not in valid:
            _fail(FAILED_SOURCE_VERIFY, "source checksum unknown key: %s" % path)
        if path in listed:
            _fail(FAILED_SOURCE_VERIFY, "source checksum duplicate key: %s" % path)
        listed[path] = digest
    for rel, digest in listed.items():
        full = os.path.join(folder, rel)
        if not os.path.isfile(full) or sha256_file(full) != digest:
            _fail(FAILED_SOURCE_VERIFY, "source checksum mismatch: %s" % rel)


def structural_verify_coordinator(coord_dir):
    for f in ("workflow_report.json", "workflow_steps.json",
              "atlas_validation_report.json"):
        if not canonical.is_canonical_bytes(
                canonical.read_bytes(os.path.join(coord_dir, f))):
            _fail(FAILED_SOURCE_VERIFY, "coordinator %s not canonical" % f)
    _checksum_verify(coord_dir, "workflow_checksums.txt", COORD_CHECKSUM_PATHS)
    report = canonical.load_json(os.path.join(coord_dir, "workflow_report.json"))
    if report.get("workflow_status") != "WORKFLOW_COMPLETED":
        _fail(FAILED_SOURCE_VERIFY, "coordinator workflow_status not WORKFLOW_COMPLETED")
    steps = canonical.load_json(os.path.join(coord_dir, "workflow_steps.json"))
    got = steps.get("steps")
    if not isinstance(got, list) or len(got) != 11 \
            or not all(s.get("status") == "COMPLETED" for s in got):
        _fail(FAILED_SOURCE_VERIFY, "coordinator steps not all completed")


def structural_verify_companion(source_run):
    for f in ("companion_report.json", "companion_steps.json",
              "workflow_request.json"):
        if not canonical.is_canonical_bytes(
                canonical.read_bytes(os.path.join(source_run, f))):
            _fail(FAILED_SOURCE_VERIFY, "companion %s not canonical" % f)
    _checksum_verify(source_run, "companion_checksums.txt", (
        "workflow_request.json", "companion_report.json", "companion_steps.json",
        "coordinator_output/workflow_report.json",
        "coordinator_output/workflow_steps.json",
        "coordinator_output/atlas_validation_report.json",
        "coordinator_output/atlas_registry_copy.json",
        "coordinator_output/case_bundle_v02/case_manifest.json"))
    report = canonical.load_json(os.path.join(source_run, "companion_report.json"))
    if report.get("companion_status") != "COMPANION_COMPLETED":
        _fail(FAILED_SOURCE_VERIFY, "companion_status not COMPANION_COMPLETED")


def load_reports(source_type, source_run, coord_dir):
    reports = {
        "coordinator_workflow_report": canonical.load_json(
            os.path.join(coord_dir, "workflow_report.json")),
        "atlas_validation_report": canonical.load_json(
            os.path.join(coord_dir, "atlas_validation_report.json")),
        "atlas_registry_copy": canonical.load_json(
            os.path.join(coord_dir, "atlas_registry_copy.json")),
        "case_bundle_manifest": canonical.load_json(
            os.path.join(coord_dir, "case_bundle_v02", "case_manifest.json")),
    }
    if source_type == versions.SOURCE_TYPE_COMPANION:
        reports["companion_report"] = canonical.load_json(
            os.path.join(source_run, "companion_report.json"))
        reports["workflow_request"] = canonical.load_json(
            os.path.join(source_run, "workflow_request.json"))
    return reports
