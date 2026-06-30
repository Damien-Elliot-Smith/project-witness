# case_bundle_v02_lib/versions.py
# Version constants and the honest status vocabulary for Case Bundle v0.2. It
# packages three already-verified Histor-lite case records (Sentinel action,
# Aletheia evidence, ODIN reasoning) into one portable Project Witness bundle. It
# preserves the records exactly and NEVER claims the evidence or any claim is true.

CASE_BUNDLE_VERSION = "0.2.0"

# Top-level bundle file names.
MANIFEST_NAME = "case_manifest.json"
CHECKSUMS_NAME = "bundle_checksums.txt"

# Bundle subfolders.
SENTINEL_DIR = "sentinel_case"
ALETHEIA_DIR = "aletheia_case"
ODIN_DIR = "odin_case"
SUBFOLDERS = (SENTINEL_DIR, ALETHEIA_DIR, ODIN_DIR)
INCLUDED_RECORDS = ["sentinel_case", "aletheia_case", "odin_case"]

# --- Real subcase file names (preserved exactly from the frozen producers) ---
# Sentinel case (Histor-lite v0.1.2 `import-sentinel` output):
SENTINEL_SUMMARY = "case_summary.json"
SENTINEL_REPLAY = "sentinel_replay_report.txt"
SENTINEL_CHECKSUMS = "checksums.txt"
SENTINEL_FILES = (SENTINEL_SUMMARY, SENTINEL_REPLAY, SENTINEL_CHECKSUMS)

# Aletheia evidence case (Histor-lite Aletheia Importer v0.1 output):
ALETHEIA_SUMMARY = "evidence_case_summary.json"
ALETHEIA_MANIFEST_COPY = "aletheia_manifest_copy.json"
ALETHEIA_REPLAY = "aletheia_replay_report.txt"
ALETHEIA_CHECKSUMS = "evidence_case_checksums.txt"
ALETHEIA_FILES = (ALETHEIA_SUMMARY, ALETHEIA_MANIFEST_COPY, ALETHEIA_REPLAY,
                  ALETHEIA_CHECKSUMS)

# ODIN reasoning case (Histor-lite ODIN Importer v0.1 output):
ODIN_SUMMARY = "odin_case_summary.json"
ODIN_REPORT_COPY = "odin_reasoning_report_copy.json"
ODIN_TRACE_COPY = "odin_proof_trace_copy.json"
ODIN_CLAIMS_COPY = "odin_claims_copy.json"
ODIN_REPLAY = "odin_replay_report.txt"
ODIN_CHECKSUMS = "odin_case_checksums.txt"
ODIN_FILES = (ODIN_SUMMARY, ODIN_REPORT_COPY, ODIN_TRACE_COPY, ODIN_CLAIMS_COPY,
              ODIN_REPLAY, ODIN_CHECKSUMS)

# --- Source component names (real values; see field-mapping note below) ---
SENTINEL_SOURCE_COMPONENT = "histor_lite"
ALETHEIA_SOURCE_COMPONENT = "histor_lite_aletheia_importer"
ODIN_SOURCE_COMPONENT = "histor_lite_odin_importer"

# --- Expected sub-status values ---
ALETHEIA_VERIFIED_PRESENT = "VERIFIED_PRESENT"
ALETHEIA_IMPORTED = "IMPORTED_VERIFIED_ALETHEIA"
ODIN_IMPORTED = "IMPORTED_VERIFIED_ODIN"
ODIN_CONSISTENT = "CONSISTENT"
ODIN_CONTRADICTION_DETECTED = "CONTRADICTION_DETECTED"
ODIN_INVALID_INPUT = "INVALID_INPUT"
ODIN_IMPORTABLE_STATUSES = frozenset({ODIN_CONSISTENT, ODIN_CONTRADICTION_DETECTED})

# bundle_status values.
BUNDLED_VERIFIED_CASE = "BUNDLED_VERIFIED_CASE"
FAILED_SENTINEL_CASE_VERIFY = "FAILED_SENTINEL_CASE_VERIFY"
FAILED_ALETHEIA_CASE_VERIFY = "FAILED_ALETHEIA_CASE_VERIFY"
FAILED_ODIN_CASE_VERIFY = "FAILED_ODIN_CASE_VERIFY"
FAILED_CASE_ID_MISMATCH = "FAILED_CASE_ID_MISMATCH"
FAILED_CHECKSUMS_INVALID = "FAILED_CHECKSUMS_INVALID"

# Tokens that would imply a truth/authenticity claim -> forbidden anywhere in the
# bundle manifest or the packaged replay reports.
#
# IMPORTANT: these must catch AFFIRMATIVE truth claims without colliding with the
# honest negative disclaimers the records legitimately contain (e.g. "does not
# prove evidence contents are true", "does not prove ODIN claims are true"). So we
# deliberately avoid bare substrings like "are true"/"is authentic" that appear
# inside those disclaimers, and instead match affirmative predicate-style forms and
# unambiguous assertions. The verifier additionally strips known disclaimer
# sentences before scanning (see verifier._strip_disclaimers).
FORBIDDEN_TRUTH_TOKENS = (
    "contents_true", "contents.true", "claim.true", "claims_are_true",
    "evidence_is_true", "evidence.is_true", "evidence_is_authentic",
    "file.authentic", "source.trusted", "statement.proven", "contents_proven",
    "proves_reality", "proves reality", "is proven true", "are proven true",
    "proven_true", "verified_true",
)

# Disclaimer sentence fragments that legitimately contain truth words in a NEGATED
# context. The verifier removes these before scanning so the honest disclaimers do
# not trip the affirmative-claim scan.
DISCLAIMER_FRAGMENTS = (
    "does not prove evidence contents are true",
    "does not prove odin claims are true",
    "it does not prove the evidence contents are true",
    "does not prove that any claim is true",
    "does not prove the evidence contents are true",
    "it does not prove claims are true",
    "does not prove claims are true",
)

TRUTH_DISCLAIMER_HINT = (
    "Case Bundle v0.2 packages verified case records only. It does not prove "
    "evidence contents are true and does not prove ODIN claims are true."
)

KNOWN_LIMITATIONS = [
    "Case Bundle v0.2 packages verified case records only.",
    "It does not prove evidence contents are true.",
    "It does not prove ODIN claims are true.",
    "It does not execute actions.",
    "It does not run evidence interpretation.",
    "It does not sign or externally anchor the bundle.",
    "Whole-folder fabrication remains possible without signing.",
]

# Field-mapping note (frozen producers use slightly different field names than the
# spec's idealised example; we preserve the REAL fields and map them):
#   Sentinel case_summary.json:
#       import_status      (real value: "IMPORTED")  -> manifest sentinel.case_status
#       sentinel_replay_verdict (e.g. "PASS_STRICT") -> manifest sentinel.action_status
#       source_component   (real value: "sentinel_core" via histor_lite)
#   Aletheia evidence_case_summary.json: import_status, source_evidence_status.
#   ODIN odin_case_summary.json: import_status, source_reasoning_status,
#       claim_count, contradiction_count.
