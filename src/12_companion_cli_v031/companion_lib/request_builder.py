"""Build a canonical Coordinator v0.3 request from Companion CLI arguments."""

from . import versions


def build_request(case_id, evidence_id, evidence_file, allowed_root,
                  case_directory_name, component_roots):
    return {
        "coordinator_workflow_request_version": versions.COORDINATOR_REQUEST_VERSION,
        "workflow_type": versions.WORKFLOW_TYPE,
        "requested_case_id": case_id,
        "evidence_id": evidence_id,
        "allowed_root": allowed_root,
        "case_directory_name": case_directory_name,
        "evidence_file": evidence_file,
        "component_roots": {
            "atlas_registry_root": component_roots["atlas_registry_root"],
            "sentinel_root": component_roots["sentinel_root"],
            "histor_lite_root": component_roots["histor_lite_root"],
            "aletheia_root": component_roots["aletheia_root"],
            "bridge_root": component_roots["bridge_root"],
            "odin_root": component_roots["odin_root"],
            "histor_aletheia_root": component_roots["histor_aletheia_root"],
            "histor_odin_root": component_roots["histor_odin_root"],
            "case_bundle_v02_root": component_roots["case_bundle_v02_root"],
        },
    }
