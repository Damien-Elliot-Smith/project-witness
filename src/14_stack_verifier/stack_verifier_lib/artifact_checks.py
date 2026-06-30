"""Record checked artifact paths and hashes (relative paths only)."""

import os

from . import versions
from .checksums import sha256_file
from .errors import (CheckError, FAILED_SOURCE_STRUCTURE_INVALID, ARTIFACT_CHECKED)

# (artifact_id, coord-relative path, artifact_type)
_COORD_ARTIFACTS = (
    ("coordinator_workflow_report", "workflow_report.json", "workflow_report"),
    ("coordinator_workflow_steps", "workflow_steps.json", "workflow_steps"),
    ("coordinator_atlas_validation_report", "atlas_validation_report.json",
     "atlas_validation_report"),
    ("coordinator_atlas_registry_copy", "atlas_registry_copy.json",
     "atlas_registry_copy"),
    ("case_bundle_manifest", "case_bundle_v02/case_manifest.json",
     "case_bundle_manifest"),
    ("odin_reasoning_report", "odin_output/reasoning_report.json",
     "odin_reasoning_report"),
    ("bridge_claims", "bridge_output/odin_claims.json", "bridge_claims"),
    ("aletheia_evidence_manifest", "aletheia_bundle/evidence_manifest.json",
     "aletheia_evidence_manifest"),
    ("histor_sentinel_summary", "histor_sentinel_case/case_summary.json",
     "histor_sentinel_summary"),
    ("histor_aletheia_summary", "histor_aletheia_case/evidence_case_summary.json",
     "histor_aletheia_summary"),
    ("histor_odin_summary", "histor_odin_case/odin_case_summary.json",
     "histor_odin_summary"),
    ("sentinel_run_report", "sentinel_run/run_report.json", "sentinel_run_report"),
)
_COMPANION_ARTIFACTS = (
    ("companion_report", "companion_report.json", "companion_report"),
    ("companion_steps", "companion_steps.json", "companion_steps"),
    ("companion_workflow_request", "workflow_request.json", "workflow_request"),
)
_MANIFEST_ARTIFACTS = (
    ("unified_case_manifest", "unified_case_manifest.json", "unified_case_manifest"),
    ("unified_source_index", "source_index.json", "unified_source_index"),
)


def build_checked_artifacts(source_type, source_run, coord_dir, coord_prefix,
                            manifest_run=None):
    artifacts = []
    seen = set()

    def add(label, artifact_id, full_path, rel_path, artifact_type):
        if not os.path.isfile(full_path):
            raise CheckError(FAILED_SOURCE_STRUCTURE_INVALID,
                             "artifact file missing: %s" % rel_path)
        if (label, artifact_id) in seen:
            raise CheckError(FAILED_SOURCE_STRUCTURE_INVALID,
                             "duplicate artifact_id: %s/%s" % (label, artifact_id))
        if (label, rel_path) in seen:
            raise CheckError(FAILED_SOURCE_STRUCTURE_INVALID,
                             "duplicate relative_path: %s/%s" % (label, rel_path))
        seen.add((label, artifact_id))
        seen.add((label, rel_path))
        artifacts.append({
            "artifact_id": artifact_id, "source_label": label,
            "relative_path": rel_path, "sha256": sha256_file(full_path),
            "artifact_type": artifact_type, "check_status": ARTIFACT_CHECKED,
        })

    for artifact_id, coord_rel, atype in _COORD_ARTIFACTS:
        add(versions.LABEL_SOURCE, artifact_id, os.path.join(coord_dir, coord_rel),
            coord_prefix + coord_rel, atype)
    if source_type == versions.SOURCE_TYPE_COMPANION:
        for artifact_id, rel, atype in _COMPANION_ARTIFACTS:
            add(versions.LABEL_SOURCE, artifact_id,
                os.path.join(source_run, rel), rel, atype)
    if manifest_run is not None:
        for artifact_id, rel, atype in _MANIFEST_ARTIFACTS:
            add(versions.LABEL_MANIFEST, artifact_id,
                os.path.join(manifest_run, rel), rel, atype)
    return sorted(artifacts, key=lambda a: (a["source_label"], a["artifact_id"]))
