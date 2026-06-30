"""Build the source artifact index (relative paths + SHA-256) and source_index."""

import os

from . import versions
from .checksums import sha256_file
from .errors import BuildError, FAILED_SOURCE_STRUCTURE_INVALID

# (artifact_id, coord-relative path, artifact_type, produced_by)
_COORD_ARTIFACTS = (
    ("coordinator_workflow_report", "workflow_report.json", "workflow_report",
     "coordinator_workflow_v03"),
    ("coordinator_workflow_steps", "workflow_steps.json", "workflow_steps",
     "coordinator_workflow_v03"),
    ("coordinator_atlas_validation_report", "atlas_validation_report.json",
     "atlas_validation_report", "coordinator_workflow_v03"),
    ("coordinator_atlas_registry_copy", "atlas_registry_copy.json",
     "atlas_registry_copy", "atlas_registry_v01"),
    ("case_bundle_manifest", "case_bundle_v02/case_manifest.json",
     "case_bundle_manifest", "case_bundle_v02"),
    ("odin_reasoning_report", "odin_output/reasoning_report.json",
     "odin_reasoning_report", "odin_claim_reasoner_v01"),
    ("bridge_claims", "bridge_output/odin_claims.json", "bridge_claims",
     "aletheia_odin_bridge_v01"),
    ("aletheia_evidence_manifest", "aletheia_bundle/evidence_manifest.json",
     "aletheia_evidence_manifest", "aletheia_evidence_bundle_v01"),
    ("histor_sentinel_summary", "histor_sentinel_case/case_summary.json",
     "histor_sentinel_summary", "histor_lite_v012"),
    ("histor_aletheia_summary", "histor_aletheia_case/evidence_case_summary.json",
     "histor_aletheia_summary", "histor_lite_aletheia_importer_v01"),
    ("histor_odin_summary", "histor_odin_case/odin_case_summary.json",
     "histor_odin_summary", "histor_lite_odin_importer_v01"),
    ("sentinel_run_report", "sentinel_run/run_report.json", "sentinel_run_report",
     "sentinel_core_v022"),
)
# Companion-only artifacts (relative to the source run root).
_COMPANION_ARTIFACTS = (
    ("companion_report", "companion_report.json", "companion_report",
     "companion_cli_v03"),
    ("companion_steps", "companion_steps.json", "companion_steps",
     "companion_cli_v03"),
    ("companion_workflow_request", "workflow_request.json", "workflow_request",
     "companion_cli_v03"),
)


def build_source_artifacts(source_type, source_run, coord_dir, coord_prefix):
    artifacts = []
    seen_ids = set()
    seen_paths = set()

    def add(artifact_id, full_path, rel_path, artifact_type, produced_by):
        if not os.path.isfile(full_path):
            raise BuildError(FAILED_SOURCE_STRUCTURE_INVALID,
                             "artifact file missing: %s" % rel_path)
        if artifact_id in seen_ids:
            raise BuildError(FAILED_SOURCE_STRUCTURE_INVALID,
                             "duplicate artifact_id: %s" % artifact_id)
        if rel_path in seen_paths:
            raise BuildError(FAILED_SOURCE_STRUCTURE_INVALID,
                             "duplicate relative_path: %s" % rel_path)
        seen_ids.add(artifact_id)
        seen_paths.add(rel_path)
        artifacts.append({
            "artifact_id": artifact_id,
            "relative_path": rel_path,
            "sha256": sha256_file(full_path),
            "artifact_type": artifact_type,
            "produced_by": produced_by,
        })

    for artifact_id, coord_rel, atype, producer in _COORD_ARTIFACTS:
        add(artifact_id, os.path.join(coord_dir, coord_rel),
            coord_prefix + coord_rel, atype, producer)
    if source_type == versions.SOURCE_TYPE_COMPANION:
        for artifact_id, rel, atype, producer in _COMPANION_ARTIFACTS:
            add(artifact_id, os.path.join(source_run, rel), rel, atype, producer)
    return sorted(artifacts, key=lambda a: a["artifact_id"])


def count_source_files(source_run):
    total = 0
    for _root, _dirs, files in os.walk(source_run):
        total += len(files)
    return total


def build_source_index(source_type, source_run, artifacts):
    return {
        "source_index_version": versions.SOURCE_INDEX_VERSION,
        "source_type": source_type,
        "source_root_recorded_as": versions.SOURCE_ROOT_PLACEHOLDER,
        "source_files_indexed": count_source_files(source_run),
        "source_artifacts_indexed": len(artifacts),
        "notes": [
            "Absolute source path is not stored in the manifest.",
            "Only relative source artifact paths and hashes are recorded.",
        ],
    }
