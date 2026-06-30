# atlas_registry_lib/versions.py
# Version constants and the required-vocabulary expectations for Atlas Registry v0.1.
# Atlas is a READ-ONLY registry + verifier of the vocabulary Project Witness already
# uses (components, versions, workflow/action types, statuses, predicates, record
# types). It runs no workflows, calls no components, and decides no truth.

ATLAS_REGISTRY_VERSION = "0.1.0"
REGISTRY_ID = "project_witness_local_v1_registry"

# --- Top-level registry schema ---
REQUIRED_TOP_FIELDS = (
    "atlas_registry_version", "registry_id", "components", "workflow_types",
    "action_types", "statuses", "claim_predicates", "case_record_types",
    "known_limitations",
)

# --- Allowed enumerations ---
ALLOWED_COMPONENT_TYPES = frozenset({
    "ACTION_GATE", "IMPORTER", "BUNDLER", "COORDINATOR", "COMPANION",
    "EVIDENCE_BUNDLE", "REASONER", "BRIDGE", "DEMO", "REGISTRY", "REVIEW_PACK",
})
ALLOWED_FROZEN_STATUS = frozenset({"FROZEN", "DONE", "IN_PROGRESS", "NOT_STARTED"})

# --- Required current components (up to Move 21) ---
REQUIRED_COMPONENT_IDS = (
    "sentinel_core", "histor_lite", "case_bundle_v011", "coordinator_workflow_v018",
    "companion_cli_v01", "aletheia_evidence_bundle", "odin_claim_reasoner",
    "aletheia_odin_bridge", "evidence_reasoning_demo",
    "histor_lite_aletheia_importer", "histor_lite_odin_importer", "case_bundle_v02",
    "coordinator_workflow_v02", "companion_cli_v02", "atlas_registry",
)
REQUIRED_WORKFLOW_TYPES = ("CREATE_CASE_DIRECTORY", "CREATE_EVIDENCE_REASONING_CASE")
REQUIRED_ACTION_TYPES = ("CREATE_DIRECTORY",)
REQUIRED_PREDICATES = ("evidence.present", "evidence.integrity_verified")

# Statuses that must appear somewhere in the registry's statuses section.
REQUIRED_STATUSES = (
    "PASS_STRICT", "PASS_WITH_ENVIRONMENTAL_EXCEPTIONS", "FAIL",
    "REPLAY_INCOMPATIBLE", "VERIFIED_PRESENT", "CONSISTENT",
    "CONTRADICTION_DETECTED", "INVALID_INPUT", "CONVERTED",
    "IMPORTED_VERIFIED_ALETHEIA", "IMPORTED_VERIFIED_ODIN", "BUNDLED_VERIFIED_CASE",
    "WORKFLOW_COMPLETED", "COMPANION_COMPLETED", "COMPLETED", "FAILED",
    "SKIPPED_AFTER_FAILURE",
)

# Action types that must NEVER appear (out of roadmap for v0.1).
FORBIDDEN_ACTION_TYPES = frozenset({
    "WRITE_FILE", "DELETE_FILE", "SHELL_COMMAND", "NETWORK_CALL",
})

# --- Truth-claim refusals ---
# Truth-like status names that must never appear (case-insensitive match on name).
FORBIDDEN_STATUS_NAMES = frozenset({
    "TRUE", "PROVEN_TRUE", "AUTHENTIC", "VERIFIED_TRUE", "SOURCE_TRUSTED",
    "REALITY_PROVEN",
})
# Truth-like predicate names that must never appear.
FORBIDDEN_PREDICATES = frozenset({
    "contents.true", "file.authentic", "source.trusted", "statement.proven",
    "reality.proven",
})

# --- Registry statuses (the verifier's verdicts) ---
REGISTRY_VERIFIED = "REGISTRY_VERIFIED"
FAILED_SCHEMA_INVALID = "FAILED_SCHEMA_INVALID"
FAILED_DUPLICATE_ENTRY = "FAILED_DUPLICATE_ENTRY"
FAILED_NON_CANONICAL_JSON = "FAILED_NON_CANONICAL_JSON"
FAILED_TRUTH_CLAIM = "FAILED_TRUTH_CLAIM"
FAILED_CHECKSUMS_INVALID = "FAILED_CHECKSUMS_INVALID"

# --- Export ---
EXPORT_REGISTRY_COPY = "atlas_registry_copy.json"
EXPORT_SUMMARY = "atlas_summary.json"
EXPORT_CHECKSUMS = "atlas_checksums.txt"
EXPORT_FILES = (EXPORT_REGISTRY_COPY, EXPORT_SUMMARY, EXPORT_CHECKSUMS)
EXPORT_CHECKSUM_KEYS = (EXPORT_REGISTRY_COPY, EXPORT_SUMMARY)

KNOWN_LIMITATIONS = [
    "Atlas Registry v0.1 is read-only.",
    "Atlas Registry v0.1 does not run workflows.",
    "Atlas Registry v0.1 does not prove truth.",
    "Atlas Registry v0.1 does not verify external reality.",
    "Atlas Registry v0.1 is not connected to Coordinator yet.",
    "Atlas Registry v0.1 is not connected to Companion yet.",
    "Atlas Registry v0.1 does not sign or externally anchor registry entries.",
]
