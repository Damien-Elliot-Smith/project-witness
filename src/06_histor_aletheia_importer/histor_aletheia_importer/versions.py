# histor_aletheia_importer/versions.py
# Version constants and the honest status vocabulary for the Histor-lite Aletheia
# Importer v0.1. It records verified Aletheia integrity metadata as a Histor-lite-
# style evidence case record. It NEVER claims the evidence contents are true.

IMPORTER_VERSION = "0.1.0"

# Output file names (exactly these four; no others).
SUMMARY_NAME = "evidence_case_summary.json"
MANIFEST_COPY_NAME = "aletheia_manifest_copy.json"
REPLAY_REPORT_NAME = "aletheia_replay_report.txt"
CHECKSUMS_NAME = "evidence_case_checksums.txt"

SOURCE_COMPONENT = "aletheia_evidence_bundle"

# The Aletheia evidence_status the importer requires before importing.
ALETHEIA_VERIFIED_PRESENT = "VERIFIED_PRESENT"

# import_status values.
IMPORTED_VERIFIED_ALETHEIA = "IMPORTED_VERIFIED_ALETHEIA"
FAILED_ALETHEIA_VERIFY = "FAILED_ALETHEIA_VERIFY"
FAILED_STATUS_NOT_VERIFIED_PRESENT = "FAILED_STATUS_NOT_VERIFIED_PRESENT"
FAILED_MANIFEST_INVALID = "FAILED_MANIFEST_INVALID"
FAILED_CHECKSUMS_INVALID = "FAILED_CHECKSUMS_INVALID"

# Tokens that would imply a truth/authenticity claim -> forbidden anywhere in the
# case record (summary or replay report).
FORBIDDEN_TRUTH_TOKENS = (
    "contents_true", "contents.true", "file.authentic", "source.trusted",
    "statement.proven", "image.real", "authentic", "proven_true",
    "verified_true", "genuine",
)

# A required honest sentence that MUST appear in the replay report.
TRUTH_DISCLAIMER = (
    "This import verifies Aletheia evidence integrity metadata only. It does not "
    "prove the evidence contents are true."
)

KNOWN_LIMITATIONS = [
    "This importer records Aletheia evidence integrity metadata only.",
    "It does not copy the evidence file.",
    "It does not prove the evidence contents are true.",
    "It does not interpret the evidence contents.",
    "It does not import ODIN reasoning.",
    "It is not connected to Coordinator or Companion yet.",
    "It does not sign or externally anchor the case record.",
]
