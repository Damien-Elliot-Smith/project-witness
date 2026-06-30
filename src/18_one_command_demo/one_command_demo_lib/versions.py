"""Version and identity constants for One-Command Demo Script v0.1."""

ONE_COMMAND_DEMO_SCRIPT_VERSION = "0.1.0"
ONE_COMMAND_DEMO_STEPS_VERSION = "0.1.0"
CONFIG_VERSION = "0.1.0"

# The seven required statuses the underlying Connected Demo must reach.
REQUIRED_STATUSES = {
    "connected_demo_status": "DEMO_COMPLETED",
    "companion_status": "COMPANION_COMPLETED",
    "coordinator_workflow_status": "WORKFLOW_COMPLETED",
    "atlas_validation_status": "ATLAS_VALIDATED",
    "source_status": "SOURCE_VERIFIED",
    "stack_verification_status": "STACK_VERIFIED",
    "stack_selfcheck_status": "STACK_SELFCHECK_PASSED",
}

KNOWN_LIMITATIONS = [
    "This script only runs and verifies the frozen Connected Demo.",
    "It does not prove evidence contents are true.",
    "It does not prove ODIN claims are true.",
    "It does not verify external reality.",
    "It does not sign or externally anchor outputs.",
    "Whole-folder fabrication remains possible under unkeyed hashes.",
]
