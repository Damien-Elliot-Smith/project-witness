"""Version and identity constants for Stack Selfcheck v0.1.2."""

STACK_SELFCHECK_VERSION = "0.1.2"
STACK_SELFCHECK_STEPS_VERSION = "0.1.2"
STACK_INVENTORY_VERSION = "0.1.0"
STACK_NAME = "project_witness_local_v1"

# ---------------------------------------------------------------------------
# Legacy documentation compatibility (added in v0.1.1)
#
# Four early frozen components were sealed before the later documentation
# convention (every required component carries README.md, KNOWN_LIMITATIONS.md,
# and RELEASE_COMMANDS.md) existed. They are NOT modified by this repair.
# Instead, the inventory may declare an explicit, recorded legacy profile for
# exactly these component IDs, and ONLY these documentation files may be
# omitted. Every other component must still carry the full documentation set.
#
# The allowance is opt-in per component via the inventory field
# `legacy_documentation_profile`; it is never automatic. The registry below is
# the single source of truth for which IDs may use it and which exact files
# each may omit. Omitting any file NOT listed here still fails.
# ---------------------------------------------------------------------------
LEGACY_DOCUMENTATION_PROFILE = "pre_documentation_convention_v0"

LEGACY_DOCUMENTATION_REASON = "component frozen before documentation convention"

# component_id -> frozenset of documentation files that component may omit.
LEGACY_DOCUMENTATION_ALLOWANCES = {
    "sentinel_core_v022": frozenset({"KNOWN_LIMITATIONS.md", "RELEASE_COMMANDS.md"}),
    "histor_lite_v012": frozenset({"RELEASE_COMMANDS.md"}),
    "case_bundle_v011": frozenset({"RELEASE_COMMANDS.md"}),
    "atlas_red_blue_pack_v01": frozenset({"KNOWN_LIMITATIONS.md", "RELEASE_COMMANDS.md"}),
}

REQUIRED_COMPONENT_IDS = (
    "sentinel_core_v022", "histor_lite_v012", "case_bundle_v011",
    "coordinator_workflow_v018", "companion_cli_v01",
    "aletheia_evidence_bundle_v01", "odin_claim_reasoner_v01",
    "aletheia_odin_bridge_v01", "evidence_reasoning_demo_v01",
    "histor_lite_aletheia_importer_v01", "histor_lite_odin_importer_v01",
    "case_bundle_v02", "coordinator_workflow_v02", "companion_cli_v02",
    "atlas_registry_v01", "atlas_release_gate_v01", "atlas_red_blue_pack_v01",
    "coordinator_workflow_v03", "companion_cli_v03", "unified_case_manifest_v01",
    "stack_verifier_v01", "stack_selfcheck_v01",
)

CURRENT_COMPONENT_ID = "stack_selfcheck_v01"

# Out-of-scope features that must never be claimed as supported (only negated).
OUT_OF_SCOPE_FEATURES = (
    "signing", "external anchoring", "anchoring", "llm", "natural language",
    "gui", "queue", "concurrency",
)
