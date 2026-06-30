"""Version and identity constants for Companion CLI v0.3."""

COMPANION_CLI_VERSION = "0.3.0"
COMPANION_STEPS_VERSION = "0.3.0"
COORDINATOR_REQUEST_VERSION = "0.3.0"
COORDINATOR_WORKFLOW_VERSION = "0.3.0"

WORKFLOW_TYPE = "CREATE_EVIDENCE_REASONING_CASE"
ACTION_TYPE = "CREATE_DIRECTORY"

REQUIRED_PREDICATES = ("evidence.present", "evidence.integrity_verified")
FORBIDDEN_ACTION_TYPES = ("WRITE_FILE", "DELETE_FILE", "SHELL_COMMAND", "NETWORK_CALL")

# component_roots keys for the Coordinator v0.3 request
COMPONENT_ROOT_KEYS = (
    "atlas_registry_root", "sentinel_root", "histor_lite_root", "aletheia_root",
    "bridge_root", "odin_root", "histor_aletheia_root", "histor_odin_root",
    "case_bundle_v02_root",
)
