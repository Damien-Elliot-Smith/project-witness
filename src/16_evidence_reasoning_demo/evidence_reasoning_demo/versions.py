# evidence_reasoning_demo/versions.py
# Version constants and the honest status vocabulary for the Evidence Reasoning
# Demo v0.1. The demo runs the local chain (Aletheia -> Bridge -> ODIN) and proves
# it executes and verifies. It NEVER claims the evidence contents are true.

DEMO_VERSION = "0.1.0"
DEMO_STEPS_VERSION = "0.1.0"

# Output names.
DEMO_REPORT_NAME = "demo_report.json"
DEMO_STEPS_NAME = "demo_steps.json"
CHECKSUMS_NAME = "demo_checksums.txt"

# Component output subfolders (produced by frozen components; preserved exactly).
ALETHEIA_BUNDLE_DIR = "aletheia_bundle"
BRIDGE_OUTPUT_DIR = "bridge_output"
ODIN_OUTPUT_DIR = "odin_output"
SUBFOLDERS = (ALETHEIA_BUNDLE_DIR, BRIDGE_OUTPUT_DIR, ODIN_OUTPUT_DIR)

# Files inside the component outputs that the demo references by hash.
ALETHEIA_MANIFEST_REL = f"{ALETHEIA_BUNDLE_DIR}/evidence_manifest.json"
BRIDGE_REPORT_REL = f"{BRIDGE_OUTPUT_DIR}/bridge_report.json"
ODIN_REASONING_REPORT_REL = f"{ODIN_OUTPUT_DIR}/reasoning_report.json"

# The only claim predicates the chain may surface.
PREDICATE_PRESENT = "evidence.present"
PREDICATE_INTEGRITY_VERIFIED = "evidence.integrity_verified"
ALLOWED_PREDICATES = (PREDICATE_PRESENT, PREDICATE_INTEGRITY_VERIFIED)

# Predicate fragments that would imply a truth/authenticity claim -> forbidden.
FORBIDDEN_PREDICATE_TOKENS = (
    "true", "truth", "authentic", "trusted", "proven", "real", "genuine",
    "accurate", "content",
)

# Expected upstream status values.
ALETHEIA_VERIFIED_PRESENT = "VERIFIED_PRESENT"
BRIDGE_CONVERTED = "CONVERTED"
ODIN_CONSISTENT = "CONSISTENT"

# demo_status values.
DEMO_COMPLETED = "DEMO_COMPLETED"
FAILED_INPUT_VALIDATION = "FAILED_INPUT_VALIDATION"
FAILED_ALETHEIA_BUNDLE = "FAILED_ALETHEIA_BUNDLE"
FAILED_ALETHEIA_VERIFY = "FAILED_ALETHEIA_VERIFY"
FAILED_BRIDGE_CONVERT = "FAILED_BRIDGE_CONVERT"
FAILED_BRIDGE_VERIFY = "FAILED_BRIDGE_VERIFY"
FAILED_ODIN_REASON = "FAILED_ODIN_REASON"
FAILED_ODIN_VERIFY = "FAILED_ODIN_VERIFY"
FAILED_CHECKSUMS_INVALID = "FAILED_CHECKSUMS_INVALID"

# Step statuses.
STEP_COMPLETED = "COMPLETED"
STEP_FAILED = "FAILED"
STEP_SKIPPED_AFTER_FAILURE = "SKIPPED_AFTER_FAILURE"

KNOWN_LIMITATIONS = [
    "This demo proves only that the local evidence-integrity reasoning chain "
    "executes and verifies.",
    "It does not prove the evidence contents are true.",
    "It does not interpret the evidence file.",
    "It does not use an LLM.",
    "It does not perform action gating.",
    "It is not connected to Companion or Coordinator yet.",
    "It does not sign or externally anchor outputs.",
]
