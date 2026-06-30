"""Version and identity constants for Coordinator Workflow v0.3."""

COORDINATOR_WORKFLOW_VERSION = "0.3.0"
COORDINATOR_WORKFLOW_REQUEST_VERSION = "0.3.0"
ATLAS_VALIDATION_VERSION = "0.1.0"
ATLAS_REGISTRY_VERSION = "0.1.0"

WORKFLOW_TYPE = "CREATE_EVIDENCE_REASONING_CASE"
ACTION_TYPE = "CREATE_DIRECTORY"

REQUIRED_COMPONENTS = (
    "sentinel_core",
    "histor_lite",
    "aletheia_evidence_bundle",
    "aletheia_odin_bridge",
    "odin_claim_reasoner",
    "histor_lite_aletheia_importer",
    "histor_lite_odin_importer",
    "case_bundle_v02",
    "coordinator_workflow_v02",
    "atlas_registry",
)

REQUIRED_PREDICATES = ("evidence.present", "evidence.integrity_verified")

FORBIDDEN_ACTION_TYPES = ("WRITE_FILE", "DELETE_FILE", "SHELL_COMMAND", "NETWORK_CALL")
