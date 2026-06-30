# sentinel_core/versions.py
# Single source of truth for all version constants.
# The version vector is bound into the manifest hash and every receipt, so a
# replay performed by a different implementation version fails closed rather
# than silently producing a different result.

PACKAGE_VERSION = "0.2.2"
# v0.2.0 introduced two-stage INTENT/RESULT receipts. v0.2.1 (CLI tests in-process)
# and v0.2.2 (replay-verdict honesty/reporting) are non-core repairs: the
# deterministic receipt/run protocol is byte-for-byte the v0.2.0 protocol, so
# IMPL_VERSION stays 0.2.0 and v0.2.0 run files remain replayable. Only the
# cosmetic PACKAGE_VERSION advanced.
IMPL_VERSION = "0.2.0"

# Schema / component versions. Each is embedded in every receipt and checked
# during replay against the current implementation's expected vector.
RECEIPT_SCHEMA_VERSION = "0.2.0"
ACTION_SCHEMA_VERSION = "1.1.0"
POLICY_VERSION = "0.1.1"
REASON_REGISTRY_VERSION = "0.1.0"
SESSION_VERSION = "0.1.0"
RUN_SEAL_VERSION = "0.1.0"
MANIFEST_VERSION = "0.1.0"

# The authoritative version vector. Replay requires an exact match.
CURRENT_VERSION_VECTOR = {
    "impl_version": IMPL_VERSION,
    "receipt_schema_version": RECEIPT_SCHEMA_VERSION,
    "action_schema_version": ACTION_SCHEMA_VERSION,
    "policy_version": POLICY_VERSION,
    "reason_registry_version": REASON_REGISTRY_VERSION,
    "session_version": SESSION_VERSION,
    "manifest_version": MANIFEST_VERSION,
}
