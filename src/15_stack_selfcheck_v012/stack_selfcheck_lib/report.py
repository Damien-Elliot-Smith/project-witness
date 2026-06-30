"""Stack Selfcheck v0.1 report construction and the check orchestration."""

from . import (versions, inventory_reader, component_checks, sidecar_checks,
               documentation_checks, stack_verifier_reader, legacy_documentation)
from .errors import (STACK_SELFCHECK_PASSED, INVENTORY_VERIFIED,
                     STACK_VERIFIER_OUTPUT_VERIFIED, STACK_VERIFIER_NOT_PROVIDED,
                     COMPONENT_CHECKED, COMPONENT_LEGACY_DOCUMENTATION_ACCEPTED,
                     DOCUMENTATION_BOUNDARY_VERIFIED)

KNOWN_LIMITATIONS = (
    "Stack Selfcheck v0.1 checks stack inventory and release hygiene only.",
    "It does not run workflows.",
    "It does not execute a Project Witness case.",
    "It does not copy evidence contents.",
    "It does not prove evidence contents are true.",
    "It does not prove ODIN claims are true.",
    "It does not verify external reality.",
    "It does not sign or externally anchor outputs.",
)


def build_selfcheck_report(inventory_path, stack_verifier_run=None):
    """Run the stack selfcheck. Returns (report, checked_components).
    Raises CheckError on any failure."""
    # step_001 VALIDATE_INVENTORY
    inventory = inventory_reader.load_inventory(inventory_path)
    # step_002 CHECK_REQUIRED_COMPONENTS
    inventory_reader.confirm_required_present(inventory)

    components = inventory["components"]
    # step_003 CHECK_COMPONENT_ROOTS
    #   Legacy documentation compatibility (v0.1.1): each component's explicit,
    #   recorded legacy allowance (empty for non-legacy components) is resolved
    #   first; a false or unknown legacy claim is refused here. Only the exact
    #   allowed documentation files may then be omitted.
    legacy_allowances = {}        # component_id -> honest allowance record
    legacy_used = set()           # component_ids that actually omitted a doc
    for comp in components:
        component_checks.check_root(comp)
        allowed = legacy_documentation.resolve_allowance(comp)
        omitted = component_checks.check_expected_files(comp, allowed_missing=allowed)
        if legacy_documentation.declared_profile(comp) is not None:
            legacy_allowances[comp["component_id"]] = \
                legacy_documentation.allowance_record(comp, omitted)
            if omitted:
                legacy_used.add(comp["component_id"])
        component_checks.check_version(comp)
    # step_004 CHECK_ZIP_SIDECARS
    for comp in components:
        sidecar_checks.check_sidecar(comp)
    # step_005 CHECK_DOCUMENTATION_BOUNDARIES
    for comp in components:
        documentation_checks.check_boundaries(comp)
    # step_006 CHECK_TRUTH_BOUNDARY
    for comp in components:
        documentation_checks.check_truth_boundary(comp)
    # step_007 CHECK_OPTIONAL_STACK_VERIFIER_OUTPUT
    if stack_verifier_run is not None:
        stack_verifier_reader.verify_output(stack_verifier_run)
        stack_verifier_status = STACK_VERIFIER_OUTPUT_VERIFIED
    else:
        stack_verifier_status = STACK_VERIFIER_NOT_PROVIDED

    checked = []
    for comp in sorted(components, key=lambda c: c["component_id"]):
        cid = comp["component_id"]
        used_legacy = cid in legacy_used
        checked.append({
            "component_id": cid,
            "expected_version": comp["expected_version"],
            "component_type": comp["component_type"],
            "required": bool(comp["required"]),
            "root_present": True,
            "zip_checksum_valid": True,
            "documentation_boundary_present": True,
            "truth_boundary_present": True,
            "legacy_documentation_profile": (
                versions.LEGACY_DOCUMENTATION_PROFILE if used_legacy else None),
            "check_status": (COMPONENT_LEGACY_DOCUMENTATION_ACCEPTED
                             if used_legacy else COMPONENT_CHECKED),
        })

    report = {
        "stack_selfcheck_version": versions.STACK_SELFCHECK_VERSION,
        "stack_name": inventory["stack_name"],
        "stack_selfcheck_status": STACK_SELFCHECK_PASSED,
        "inventory_status": INVENTORY_VERIFIED,
        "required_components_present": True,
        "component_versions_consistent": True,
        "component_roots_present": True,
        "zip_sidecars_valid": True,
        "documentation_boundaries_present": True,
        "documentation_boundary_status": DOCUMENTATION_BOUNDARY_VERIFIED,
        "truth_boundary_valid": True,
        "stack_verifier_status": stack_verifier_status,
        "component_count": len(checked),
        "legacy_documentation_allowances": [
            legacy_allowances[k] for k in sorted(legacy_allowances)],
        "checked_components": checked,
        "known_limitations": list(KNOWN_LIMITATIONS),
    }
    return report, checked
