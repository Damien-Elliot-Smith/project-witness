"""Move 81 structured-verdict schema constants and structural enums.

This module defines ONLY fixed structural constants and allowed-value
enums for the Move 81 structured-verdict contract. It deliberately does
NOT contain any reason-code or stage mappings: adopted reason and stage
resolution comes exclusively from the inherited frozen reason map
(verify/agreement_harness_v01/reason_map.json) supplied at run time via an
explicit --reason-map path (binding clarification 7). Nothing here is
derived from filenames, candidate numbers, timestamps, or input data.

Honesty boundary (owner clarification, Move 81): the structured output
contract SUPPORTS the full PASS / FAIL / INCONCLUSIVE vocabulary, but a
verdict is only ever emitted for a lane that has an adopted evidential
basis for it. No Rust PASS path exists; a Rust PASS observation is an
impossible verdict/exit pairing and becomes a measurement error.
"""

# --- fixed identity constants -------------------------------------------

SCHEMA_VERSION = "witness-verdict/1"
PRODUCER = "witness-structured-verdict-adapter"
# Fixed Move 81 v01 adapter version (binding clarification 2). Never
# derived from filenames, candidate numbers, timestamps, or input data.
PRODUCER_VERSION = "0.0.1-step81-structured-verdict"

# --- record types -------------------------------------------------------

RECORD_VERDICT = "verdict"
RECORD_COMPARISON = "comparison"
RECORD_MEASUREMENT_ERROR = "measurement_error"
RECORD_TYPES = (RECORD_VERDICT, RECORD_COMPARISON, RECORD_MEASUREMENT_ERROR)

# --- implementation lanes -----------------------------------------------

LANE_PYTHON = "python_bundle"
LANE_RUST = "rust_bundle"
LANE_ARCHIVE = "archive"
LANES = (LANE_PYTHON, LANE_RUST, LANE_ARCHIVE)

# --- verifier identities ------------------------------------------------

VERIFIER_PYTHON = "companion"
VERIFIER_RUST = "witness-verify"

# --- operations ---------------------------------------------------------

OP_VERIFY_BUNDLE = "verify_bundle"
OP_INSPECT_ARCHIVE = "inspect_archive"
OPERATIONS = (OP_VERIFY_BUNDLE, OP_INSPECT_ARCHIVE)

# --- input types --------------------------------------------------------

INPUT_BUNDLE_DIR = "bundle_dir"
INPUT_ARCHIVE_ZIP = "archive_zip"
INPUT_TYPES = (INPUT_BUNDLE_DIR, INPUT_ARCHIVE_ZIP)

# --- verdict vocabulary -------------------------------------------------

VERDICT_PASS = "PASS"
VERDICT_FAIL = "FAIL"
VERDICT_INCONCLUSIVE = "INCONCLUSIVE"
VERDICTS = (VERDICT_PASS, VERDICT_FAIL, VERDICT_INCONCLUSIVE)

# --- capability scope (fixed per lane; never from untrusted input) ------

SCOPE_PYTHON = "python_reference_pass_fail"
SCOPE_RUST = "rust_read_only_no_pass"
SCOPE_ARCHIVE = "archive_safety_only"
CAPABILITY_SCOPES = (SCOPE_PYTHON, SCOPE_RUST, SCOPE_ARCHIVE)

# --- comparison statuses (never PASS/FAIL/INCONCLUSIVE) -----------------

CMP_AGREEMENT = "AGREEMENT"
CMP_DECLARED_DIVERGENCE = "DECLARED_DIVERGENCE"
CMP_UNEXPECTED_DIVERGENCE = "UNEXPECTED_DIVERGENCE"
CMP_LANE_NOT_APPLICABLE = "LANE_NOT_APPLICABLE"
CMP_MEASUREMENT_ERROR = "MEASUREMENT_ERROR"
COMPARISON_STATUSES = (
    CMP_AGREEMENT,
    CMP_DECLARED_DIVERGENCE,
    CMP_UNEXPECTED_DIVERGENCE,
    CMP_LANE_NOT_APPLICABLE,
    CMP_MEASUREMENT_ERROR,
)

# --- adapter-layer measurement error vocabulary -------------------------
# These are ADAPTER failures, never verifier corruption reason codes, and
# are never stored in reason_code.

ERR_MALFORMED_JSON = "ADAPTER_MALFORMED_JSON"
ERR_STDOUT_CONTAMINATION = "ADAPTER_STDOUT_CONTAMINATION"
ERR_MULTIPLE_OBJECTS = "ADAPTER_MULTIPLE_OBJECTS"
ERR_UNEXPECTED_STDERR = "ADAPTER_UNEXPECTED_STDERR"
ERR_IMPOSSIBLE_VERDICT_EXIT_PAIR = "ADAPTER_IMPOSSIBLE_VERDICT_EXIT_PAIR"
ERR_UNKNOWN_REASON = "ADAPTER_UNKNOWN_REASON"
ERR_MISSING_STAGE_MAPPING = "ADAPTER_MISSING_STAGE_MAPPING"
ERR_TIMEOUT = "ADAPTER_TIMEOUT"
ERR_SIGNAL_TERMINATION = "ADAPTER_SIGNAL_TERMINATION"
ERR_INCOMPLETE_RESULT = "ADAPTER_INCOMPLETE_RESULT"
ERR_INVOCATION_ERROR = "ADAPTER_INVOCATION_ERROR"
ERR_VERIFIER_IDENTITY_MISMATCH = "ADAPTER_VERIFIER_IDENTITY_MISMATCH"
ERR_COMPARISON_CONTRACT_INVALID = "ADAPTER_COMPARISON_CONTRACT_INVALID"
ERR_UNKNOWN_CASE_ID = "ADAPTER_UNKNOWN_CASE_ID"
MEASUREMENT_ERROR_CODES = (
    ERR_MALFORMED_JSON,
    ERR_STDOUT_CONTAMINATION,
    ERR_MULTIPLE_OBJECTS,
    ERR_UNEXPECTED_STDERR,
    ERR_IMPOSSIBLE_VERDICT_EXIT_PAIR,
    ERR_UNKNOWN_REASON,
    ERR_MISSING_STAGE_MAPPING,
    ERR_TIMEOUT,
    ERR_SIGNAL_TERMINATION,
    ERR_INCOMPLETE_RESULT,
    ERR_INVOCATION_ERROR,
    ERR_VERIFIER_IDENTITY_MISMATCH,
    ERR_COMPARISON_CONTRACT_INVALID,
    ERR_UNKNOWN_CASE_ID,
)

# The compare operation identifier, used on comparison records and on
# measurement errors raised by the comparison authority itself.
OP_COMPARE = "compare"

# Frozen comparison-contract vocabularies (structural enums only; the
# case data itself is never copied here).
CATEGORY_AGREEMENT = "AGREEMENT_CASE"
CATEGORY_KNOWN_DIVERGENCE = "KNOWN_DIVERGENCE_CASE"
CATEGORY_SINGLE_IMPLEMENTATION = "SINGLE_IMPLEMENTATION_CASE"
CONTRACT_CATEGORIES = (
    CATEGORY_AGREEMENT,
    CATEGORY_KNOWN_DIVERGENCE,
    CATEGORY_SINGLE_IMPLEMENTATION,
)
SCOPE_IN = "in_scope"
SCOPE_OUT = "out_of_scope"
CONTRACT_SCOPES = (SCOPE_IN, SCOPE_OUT)
# The lane identifier the bundle corpus must declare, so a bundle
# comparison cannot silently use the archive corpus.
CONTRACT_BUNDLE_LANE = "bundle"

# Adopted normalized-outcome vocabulary used by the frozen corpus.
OUTCOME_ACCEPTED = "ACCEPTED"
OUTCOME_REJECTED = "REJECTED"
NORMALIZED_OUTCOMES = (OUTCOME_ACCEPTED, OUTCOME_REJECTED)

# Adopted agreement semantics: a lane verdict normalizes to an outcome.
# Rust success-within-scope (INCONCLUSIVE) and Python PASS both normalize
# to ACCEPTED; any FAIL normalizes to REJECTED. This is what makes
# clean_control an AGREEMENT_CASE despite the two lanes carrying different
# verdicts, without creating false consensus.
VERDICT_TO_OUTCOME = {
    VERDICT_PASS: OUTCOME_ACCEPTED,
    VERDICT_INCONCLUSIVE: OUTCOME_ACCEPTED,
    VERDICT_FAIL: OUTCOME_REJECTED,
}

# Expected-lane keys in the frozen corpus, per lane.
CONTRACT_LANE_KEY = {LANE_PYTHON: "python", LANE_RUST: "rust"}
CONTRACT_OBSERVED_KEY = {
    LANE_PYTHON: "python_observed", LANE_RUST: "rust_observed"}
CONTRACT_SCOPE_KEY = {
    LANE_PYTHON: "python_scope", LANE_RUST: "rust_scope"}

# --- exit-code contract -------------------------------------------------
# Verdict -> adapter exit (binding clarification 4).
VERDICT_EXIT = {
    VERDICT_PASS: 0,
    VERDICT_FAIL: 1,
    VERDICT_INCONCLUSIVE: 3,
}
# Comparison status -> adapter exit (binding clarification 4). This
# reports whether the comparison operation completed within its declared
# expected contract; it is NOT a merged verifier verdict.
COMPARISON_EXIT = {
    CMP_AGREEMENT: 0,
    CMP_DECLARED_DIVERGENCE: 0,
    CMP_LANE_NOT_APPLICABLE: 0,
    CMP_UNEXPECTED_DIVERGENCE: 1,
    CMP_MEASUREMENT_ERROR: 1,
}
# Adapter exit on any underlying measurement failure.
MEASUREMENT_ERROR_EXIT = 1
# Adapter exit on the adapter's OWN command-line usage error.
USAGE_EXIT = 2

# --- per-lane fixed capability scope ------------------------------------
LANE_CAPABILITY_SCOPE = {
    LANE_PYTHON: SCOPE_PYTHON,
    LANE_RUST: SCOPE_RUST,
    LANE_ARCHIVE: SCOPE_ARCHIVE,
}

# --- per-lane verifier identity -----------------------------------------
LANE_VERIFIER = {
    LANE_PYTHON: VERIFIER_PYTHON,
    LANE_RUST: VERIFIER_RUST,
    LANE_ARCHIVE: VERIFIER_RUST,
}

# --- per-lane reachable verdicts (honesty contract) ---------------------
# The set of verdicts a lane may HONESTLY emit given adopted capability.
# A verdict outside a lane's set (notably Rust PASS) is an impossible
# verdict/exit pairing -> measurement error.
LANE_REACHABLE_VERDICTS = {
    LANE_PYTHON: (VERDICT_PASS, VERDICT_FAIL),
    LANE_RUST: (VERDICT_FAIL, VERDICT_INCONCLUSIVE),
    LANE_ARCHIVE: (VERDICT_FAIL, VERDICT_INCONCLUSIVE),
}

# --- adopted (verdict, exit) pairings per lane --------------------------
# Used to detect impossible verdict/exit pairings from underlying output.
LANE_VERDICT_EXIT = {
    LANE_PYTHON: {VERDICT_PASS: 0, VERDICT_FAIL: 1},
    LANE_RUST: {VERDICT_FAIL: 1, VERDICT_INCONCLUSIVE: 3},
    LANE_ARCHIVE: {VERDICT_FAIL: 1, VERDICT_INCONCLUSIVE: 3},
}


def envelope(record_type):
    """Return the common mandatory envelope for every record. Callers add
    the record-type-specific fields. Keys are emitted in canonical sorted
    order at serialization time, so ordering here is irrelevant."""
    if record_type not in RECORD_TYPES:
        raise ValueError("invalid record_type: %r" % (record_type,))
    return {
        "record_type": record_type,
        "schema_version": SCHEMA_VERSION,
        "producer": PRODUCER,
        "producer_version": PRODUCER_VERSION,
    }
