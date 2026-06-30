# histor_odin_importer/versions.py
# Version constants and the honest status vocabulary for the Histor-lite ODIN
# Importer v0.1. It records verified ODIN structural reasoning metadata as a
# Histor-lite-style reasoning case record. It NEVER claims any claim is true.

IMPORTER_VERSION = "0.1.0"

# Output file names (exactly these six; no others).
SUMMARY_NAME = "odin_case_summary.json"
REPORT_COPY_NAME = "odin_reasoning_report_copy.json"
TRACE_COPY_NAME = "odin_proof_trace_copy.json"
CLAIMS_COPY_NAME = "odin_claims_copy.json"
REPLAY_REPORT_NAME = "odin_replay_report.txt"
CHECKSUMS_NAME = "odin_case_checksums.txt"

# Source ODIN run file names.
ODIN_REPORT_NAME = "reasoning_report.json"
ODIN_TRACE_NAME = "proof_trace.json"
ODIN_CLAIMS_NAME = "claims_canonical.json"

SOURCE_COMPONENT = "odin_claim_reasoner"

# ODIN reasoning statuses the importer accepts as a successful case. A structural
# contradiction is a valid reasoning OUTCOME, not a failed import. INVALID_INPUT is
# explicitly NOT importable as a successful case.
ODIN_CONSISTENT = "CONSISTENT"
ODIN_CONTRADICTION_DETECTED = "CONTRADICTION_DETECTED"
ODIN_INVALID_INPUT = "INVALID_INPUT"
IMPORTABLE_REASONING_STATUSES = frozenset({ODIN_CONSISTENT,
                                           ODIN_CONTRADICTION_DETECTED})

# import_status values.
IMPORTED_VERIFIED_ODIN = "IMPORTED_VERIFIED_ODIN"
FAILED_ODIN_VERIFY = "FAILED_ODIN_VERIFY"
FAILED_REASONING_STATUS_INVALID = "FAILED_REASONING_STATUS_INVALID"
FAILED_REPORT_INVALID = "FAILED_REPORT_INVALID"
FAILED_PROOF_TRACE_INVALID = "FAILED_PROOF_TRACE_INVALID"
FAILED_CHECKSUMS_INVALID = "FAILED_CHECKSUMS_INVALID"

# Tokens that would imply a truth/authenticity claim -> forbidden anywhere in the
# case record (summary or replay report).
FORBIDDEN_TRUTH_TOKENS = (
    "contents_true", "contents.true", "claim.true", "file.authentic",
    "source.trusted", "statement.proven", "image.real", "authentic",
    "proven_true", "verified_true", "genuine",
)

# A required honest sentence that MUST appear in the replay report.
TRUTH_DISCLAIMER = (
    "This import records ODIN structural reasoning metadata only. It does not "
    "prove that any claim is true."
)

KNOWN_LIMITATIONS = [
    "This importer records verified ODIN reasoning metadata only.",
    "It does not prove claims are true.",
    "It does not interpret evidence contents.",
    "It does not import Aletheia evidence metadata.",
    "It is not connected to Coordinator or Companion yet.",
    "It does not sign or externally anchor the case record.",
]
