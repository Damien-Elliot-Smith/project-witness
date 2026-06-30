# odin_reasoner/versions.py
# Version constants and the honest status vocabulary for ODIN Claim Reasoner v0.1.
# ODIN v0.1 reasons over already-structured claims. It detects direct structural
# contradictions only — it never proves a claim TRUE.

ODIN_REASONER_VERSION = "0.1.0"
ODIN_CLAIM_SET_VERSION = "0.1.0"
PROOF_TRACE_VERSION = "0.1.0"

# Output file names.
CLAIMS_CANONICAL_NAME = "claims_canonical.json"
REASONING_REPORT_NAME = "reasoning_report.json"
PROOF_TRACE_NAME = "proof_trace.json"
CHECKSUMS_NAME = "odin_checksums.txt"

# Claim polarity.
POLARITY_AFFIRMED = "AFFIRMED"
POLARITY_DENIED = "DENIED"
POLARITIES = frozenset({POLARITY_AFFIRMED, POLARITY_DENIED})

# Reasoning statuses.
REASONING_CONSISTENT = "CONSISTENT"
REASONING_CONTRADICTION_DETECTED = "CONTRADICTION_DETECTED"
REASONING_INVALID_INPUT = "INVALID_INPUT"

# Per-claim statuses.
CLAIM_ACCEPTED = "ACCEPTED"
CLAIM_CONTRADICTED = "CONTRADICTED"
CLAIM_INVALID = "INVALID"

# Support statuses.
SUPPORT_SUPPORTED = "SUPPORTED"
SUPPORT_MISSING_SUPPORT = "MISSING_SUPPORT"
SUPPORT_INVALID_SUPPORT = "INVALID_SUPPORT"

# Proof-trace step types.
STEP_CLAIM_ACCEPTED = "CLAIM_ACCEPTED"
STEP_CONTRADICTION_DETECTED = "CONTRADICTION_DETECTED"

# Contradiction rule reasons.
RULE_DIFFERENT_OBJECT = "SAME_SUBJECT_PREDICATE_DIFFERENT_OBJECT"
RULE_OPPOSITE_POLARITY = "SAME_SUBJECT_PREDICATE_SAME_OBJECT_OPPOSITE_POLARITY"

# Claim-accepted reason.
REASON_SCHEMA_VALID = "CLAIM_SCHEMA_VALID_AND_SUPPORT_PRESENT"

KNOWN_LIMITATIONS = [
    "ODIN v0.1 detects only direct structural contradictions.",
    "ODIN v0.1 does not prove claims true.",
    "ODIN v0.1 does not interpret natural language.",
    "ODIN v0.1 does not use an LLM.",
    "ODIN v0.1 is not a full theorem prover.",
]
