# histor_lite/versions.py
# Version constants for Histor-lite v0.1.2 and the Sentinel milestone it imports.

HISTOR_LITE_VERSION = "0.1.2"

# The Sentinel component Histor-lite v0.1.2 imports from. Histor-lite trusts the
# frozen Sentinel verifier for Sentinel semantics; it does not reimplement them.
SOURCE_COMPONENT = "sentinel_core"
SOURCE_COMPONENT_VERSION = "0.2.2"

# Sentinel replay verdicts (mirrored here only to MAP them to import statuses;
# the authoritative verdict always comes from the frozen Sentinel verifier).
VERDICT_PASS_STRICT = "PASS_STRICT"
VERDICT_PASS_WITH_ENVIRONMENTAL_EXCEPTIONS = "PASS_WITH_ENVIRONMENTAL_EXCEPTIONS"
VERDICT_FAIL = "FAIL"
VERDICT_REPLAY_INCOMPATIBLE = "REPLAY_INCOMPATIBLE"

# Only these two verdicts are accepted for import.
ACCEPTED_VERDICTS = frozenset({
    VERDICT_PASS_STRICT,
    VERDICT_PASS_WITH_ENVIRONMENTAL_EXCEPTIONS,
})

# Import statuses Histor-lite assigns.
STATUS_IMPORTED = "IMPORTED"
STATUS_IMPORTED_WITH_ENVIRONMENTAL_EXCEPTIONS = "IMPORTED_WITH_ENVIRONMENTAL_EXCEPTIONS"
STATUS_REFUSED = "REFUSED"

# Verdict -> (import_status) for the two accepted verdicts.
_ACCEPTED_STATUS = {
    VERDICT_PASS_STRICT: STATUS_IMPORTED,
    VERDICT_PASS_WITH_ENVIRONMENTAL_EXCEPTIONS:
        STATUS_IMPORTED_WITH_ENVIRONMENTAL_EXCEPTIONS,
}

# Disclosed Sentinel limitations carried into every case summary, verbatim, so a
# downstream reader is never misled about what a Sentinel PASS does and does not
# prove.
KNOWN_LIMITATIONS = [
    "Sentinel hashes are unkeyed; whole-file fabrication requires signing or "
    "anchoring to detect.",
    "Environmental ERROR receipts may be structurally verified rather than "
    "strictly reproduced.",
]


def status_for_verdict(verdict):
    """Return the import status for an ACCEPTED verdict, or None if not accepted."""
    return _ACCEPTED_STATUS.get(verdict)
