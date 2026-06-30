"""Release-gate report construction (canonical JSON)."""

from . import canonical, versions

_KNOWN_LIMITATIONS = (
    "Atlas Release Gate v0.1 checks Atlas Registry v0.1 release structure only.",
    "It does not modify the registry.",
    "It does not run Project Witness workflows.",
    "It does not prove truth.",
    "It does not connect Atlas to Coordinator or Companion.",
    "It does not sign or externally anchor the release.",
)


def build_report(release_gate_status, registry_status, export_status,
                 required_files_present, documentation_present,
                 honesty_boundary_present, forbidden_features_absent):
    return {
        "atlas_release_gate_version": versions.ATLAS_RELEASE_GATE_VERSION,
        "checked_component": versions.CHECKED_COMPONENT,
        "checked_component_version": versions.CHECKED_COMPONENT_VERSION,
        "release_gate_status": release_gate_status,
        "registry_status": registry_status,
        "export_status": export_status,
        "required_files_present": bool(required_files_present),
        "documentation_present": bool(documentation_present),
        "honesty_boundary_present": bool(honesty_boundary_present),
        "forbidden_features_absent": bool(forbidden_features_absent),
        "known_limitations": list(_KNOWN_LIMITATIONS),
    }


def write_report(path, report):
    canonical.write_canonical(path, report)
