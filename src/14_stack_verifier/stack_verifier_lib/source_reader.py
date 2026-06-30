"""Locate and read an existing Coordinator v0.3 or Companion v0.3 case output.
Read-only: never modifies the source."""

import os

from . import canonical, versions
from .errors import (CheckError, FAILED_SOURCE_MISSING,
                     FAILED_SOURCE_STRUCTURE_INVALID)

COORD_REQUIRED_FILES = (
    "workflow_report.json", "workflow_steps.json", "atlas_validation_report.json",
    "atlas_registry_copy.json", "workflow_checksums.txt",
)
COORD_REQUIRED_DIRS = (
    "sentinel_run", "histor_sentinel_case", "aletheia_bundle",
    "histor_aletheia_case", "bridge_output", "odin_output",
    "histor_odin_case", "case_bundle_v02",
)
COORD_REQUIRED_NESTED = (
    "case_bundle_v02/case_manifest.json", "odin_output/reasoning_report.json",
    "bridge_output/odin_claims.json", "aletheia_bundle/evidence_manifest.json",
    "histor_sentinel_case/case_summary.json",
    "histor_aletheia_case/evidence_case_summary.json",
    "histor_odin_case/odin_case_summary.json", "sentinel_run/run_report.json",
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
COMPANION_CHECKSUM_PATHS = (
    "workflow_request.json", "companion_report.json", "companion_steps.json",
    "coordinator_output/workflow_report.json",
    "coordinator_output/workflow_steps.json",
    "coordinator_output/atlas_validation_report.json",
    "coordinator_output/atlas_registry_copy.json",
    "coordinator_output/case_bundle_v02/case_manifest.json",
)


def locate_coordinator_dir(source_type, source_run):
    if not os.path.isdir(source_run):
        raise CheckError(FAILED_SOURCE_MISSING, "source root not found")
    if source_type == versions.SOURCE_TYPE_COORDINATOR:
        return source_run, ""
    coord = os.path.join(source_run, "coordinator_output")
    if not os.path.isdir(coord):
        raise CheckError(FAILED_SOURCE_MISSING, "companion source missing coordinator_output/")
    return coord, "coordinator_output/"


def check_required_source_files(source_type, source_run, coord_dir):
    for f in COORD_REQUIRED_FILES:
        if not os.path.isfile(os.path.join(coord_dir, f)):
            raise CheckError(FAILED_SOURCE_STRUCTURE_INVALID,
                             "missing coordinator file: %s" % f)
    for d in COORD_REQUIRED_DIRS:
        if not os.path.isdir(os.path.join(coord_dir, d)):
            raise CheckError(FAILED_SOURCE_STRUCTURE_INVALID,
                             "missing coordinator folder: %s" % d)
    for rel in COORD_REQUIRED_NESTED:
        if not os.path.isfile(os.path.join(coord_dir, rel)):
            raise CheckError(FAILED_SOURCE_STRUCTURE_INVALID,
                             "missing coordinator file: %s" % rel)
    if source_type == versions.SOURCE_TYPE_COMPANION:
        for f in COMPANION_REQUIRED_FILES:
            if not os.path.isfile(os.path.join(source_run, f)):
                raise CheckError(FAILED_SOURCE_STRUCTURE_INVALID,
                                 "missing companion file: %s" % f)


def load_reports(source_type, source_run, coord_dir):
    reports = {
        "coordinator_workflow_report": canonical.load_json(
            os.path.join(coord_dir, "workflow_report.json")),
        "coordinator_workflow_steps": canonical.load_json(
            os.path.join(coord_dir, "workflow_steps.json")),
        "atlas_validation_report": canonical.load_json(
            os.path.join(coord_dir, "atlas_validation_report.json")),
        "atlas_registry_copy": canonical.load_json(
            os.path.join(coord_dir, "atlas_registry_copy.json")),
        "case_bundle_manifest": canonical.load_json(
            os.path.join(coord_dir, "case_bundle_v02", "case_manifest.json")),
        "bridge_claims": canonical.load_json(
            os.path.join(coord_dir, "bridge_output", "odin_claims.json")),
        "odin_reasoning_report": canonical.load_json(
            os.path.join(coord_dir, "odin_output", "reasoning_report.json")),
    }
    if source_type == versions.SOURCE_TYPE_COMPANION:
        reports["companion_report"] = canonical.load_json(
            os.path.join(source_run, "companion_report.json"))
        reports["workflow_request"] = canonical.load_json(
            os.path.join(source_run, "workflow_request.json"))
    return reports
