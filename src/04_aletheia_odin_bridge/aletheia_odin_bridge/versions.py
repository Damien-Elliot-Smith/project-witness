# aletheia_odin_bridge/versions.py
# Version constants and the honest status vocabulary for the Aletheia -> ODIN
# Bridge v0.1. The bridge converts Aletheia integrity/presence metadata into ODIN
# structured claims. It NEVER creates a claim about the truth of evidence contents.

BRIDGE_VERSION = "0.1.0"
ODIN_CLAIM_SET_VERSION = "0.1.0"

# Output file names.
ODIN_CLAIMS_NAME = "odin_claims.json"
BRIDGE_REPORT_NAME = "bridge_report.json"
CHECKSUMS_NAME = "bridge_checksums.txt"
MANIFEST_COPY_NAME = "aletheia_manifest_copy.json"

# The component these claims are sourced from.
SOURCE_COMPONENT = "aletheia_evidence_bundle"

# The ONLY predicates the bridge may generate. Anything else is out of scope.
PREDICATE_PRESENT = "evidence.present"
PREDICATE_INTEGRITY_VERIFIED = "evidence.integrity_verified"
ALLOWED_PREDICATES = (PREDICATE_PRESENT, PREDICATE_INTEGRITY_VERIFIED)

# Predicate fragments that would imply a truth/authenticity claim -> forbidden.
FORBIDDEN_PREDICATE_TOKENS = (
    "true", "truth", "authentic", "trusted", "proven", "real", "genuine",
    "accurate", "valid_content", "content",
)

# The Aletheia evidence_status the bridge requires before converting.
ALETHEIA_VERIFIED_PRESENT = "VERIFIED_PRESENT"

# Bridge statuses.
BRIDGE_CONVERTED = "CONVERTED"
BRIDGE_FAILED_ALETHEIA_VERIFY = "FAILED_ALETHEIA_VERIFY"
BRIDGE_FAILED_MANIFEST_INVALID = "FAILED_MANIFEST_INVALID"
BRIDGE_FAILED_STATUS_NOT_VERIFIED_PRESENT = "FAILED_STATUS_NOT_VERIFIED_PRESENT"
BRIDGE_FAILED_ODIN_VALIDATE = "FAILED_ODIN_VALIDATE"
BRIDGE_FAILED_CHECKSUMS_INVALID = "FAILED_CHECKSUMS_INVALID"

# ODIN validation status recorded in the report.
ODIN_VALIDATION_VALID = "VALID"
ODIN_VALIDATION_SKIPPED = "SKIPPED"

KNOWN_LIMITATIONS = [
    "The bridge converts Aletheia integrity metadata into ODIN structured claims "
    "only.",
    "It does not interpret evidence contents.",
    "It does not prove the evidence contents are true.",
    "It does not sign or externally anchor the output.",
    "Whole-bundle fabrication remains possible without signing.",
]
