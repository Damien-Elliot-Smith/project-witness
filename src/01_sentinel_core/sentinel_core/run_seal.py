# sentinel_core/run_seal.py
# Final closed-run seal for suffix-truncation detection.
#
# When a session closes, a run_seal is written binding the manifest hash, the
# receipt count, and the final receipt's id/hash/session-state. Deleting the
# final receipt (clean suffix truncation) then makes the seal inconsistent and
# closed/audit replay rejects the file. The seal is an unkeyed SHA-256 digest,
# NOT a signature: it is tamper-evident within the file, not tamper-proof
# against a local actor who can rewrite the whole file and re-seal it.

import hashlib

from sentinel_core.canonical import canonical_json
from sentinel_core.errors import ManifestError, require
from sentinel_core.session import SESSION_CLOSED
from sentinel_core.versions import RUN_SEAL_VERSION

RUN_SEAL_FIELD = "run_seal"
OPEN_RUN_SEAL = None

_REQUIRED_SEAL_FIELDS = frozenset({
    "seal_version",
    "run_id",
    "manifest_hash",
    "receipt_count",
    "final_receipt_id",
    "final_receipt_hash",
    "final_session_state",
    "seal_hash",
})


def _sha256_json(value) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _seal_payload(seal: dict) -> dict:
    return {k: v for k, v in seal.items() if k != "seal_hash"}


def compute_run_seal_hash(seal: dict) -> str:
    return _sha256_json(_seal_payload(seal))


def build_run_seal(manifest: dict, receipts: list) -> dict:
    """Build the authoritative final seal for a closed run."""
    require(type(manifest) is dict, "Manifest must be an object", ManifestError)
    require(type(receipts) is list, "Receipts must be an array", ManifestError)
    require(len(receipts) > 0, "Cannot seal an empty run", ManifestError)

    final = receipts[-1]
    require(type(final) is dict, "Final receipt must be an object", ManifestError)
    require(final.get("post_session_state") == SESSION_CLOSED,
            "Only CLOSED runs may be sealed", ManifestError)
    # v0.1.3: the final receipt must be a genuine ALLOW_SESSION_CLOSE, not a
    # CREATE/BLOCK/DRY_RUN/ERROR receipt whose post_session_state was forged.
    from sentinel_core.reason_codes import is_session_close_shape
    require(is_session_close_shape(final.get("decision"), final.get("reason_code"),
                                   final.get("request"), final.get("executed")),
            "Final receipt is CLOSED but is not a valid ALLOW_SESSION_CLOSE receipt",
            ManifestError)
    require(type(final.get("canonical_hash")) is str and len(final.get("canonical_hash")) == 64,
            "Final receipt canonical_hash must be 64-char hex", ManifestError)

    seal = {
        "seal_version": RUN_SEAL_VERSION,
        "run_id": manifest["run_id"],
        "manifest_hash": manifest["manifest_hash"],
        "receipt_count": len(receipts),
        "final_receipt_id": final["receipt_id"],
        "final_receipt_hash": final["canonical_hash"],
        "final_session_state": final["post_session_state"],
    }
    seal["seal_hash"] = compute_run_seal_hash(seal)
    return seal


def validate_run_seal(data: dict, require_closed: bool = True):
    """Validate the root run_seal field.

    Closed/audit mode (default) requires a valid seal and therefore rejects
    clean suffix truncation. Open/debug mode (require_closed=False) accepts the
    absence of a seal, but a present seal must still validate exactly.
    """
    require(type(data) is dict, "Run file root must be an object", ManifestError)
    seal = data.get(RUN_SEAL_FIELD, OPEN_RUN_SEAL)
    if seal is OPEN_RUN_SEAL:
        if require_closed:
            raise ManifestError(
                "Closed audit replay requires run_seal; use allow_open for unsealed prefixes")
        return None

    require(type(seal) is dict, "run_seal must be an object or null", ManifestError)
    keys = set(seal.keys())
    require(keys == _REQUIRED_SEAL_FIELDS,
            f"run_seal field mismatch: missing={sorted(_REQUIRED_SEAL_FIELDS - keys)}, "
            f"extra={sorted(keys - _REQUIRED_SEAL_FIELDS)}", ManifestError)

    manifest = data.get("manifest")
    receipts = data.get("receipts")
    require(type(manifest) is dict, "Manifest must be an object for seal validation", ManifestError)
    require(type(receipts) is list, "Receipts must be an array for seal validation", ManifestError)
    require(len(receipts) > 0, "Sealed run must contain at least one receipt", ManifestError)

    require(seal["seal_version"] == RUN_SEAL_VERSION,
            f"Unsupported run_seal version: {seal['seal_version']!r}", ManifestError)
    require(seal["run_id"] == manifest.get("run_id"), "run_seal run_id mismatch", ManifestError)
    require(seal["manifest_hash"] == manifest.get("manifest_hash"),
            "run_seal manifest_hash mismatch", ManifestError)
    require(type(seal["receipt_count"]) is int and seal["receipt_count"] == len(receipts),
            "run_seal receipt_count mismatch", ManifestError)

    final = receipts[-1]
    require(type(final) is dict, "Final receipt must be an object", ManifestError)
    require(seal["final_receipt_id"] == final.get("receipt_id") == len(receipts) - 1,
            "run_seal final_receipt_id mismatch", ManifestError)
    require(seal["final_receipt_hash"] == final.get("canonical_hash"),
            "run_seal final_receipt_hash mismatch", ManifestError)
    require(seal["final_session_state"] == final.get("post_session_state") == SESSION_CLOSED,
            "run_seal final_session_state mismatch or run is not closed", ManifestError)
    # v0.1.3: a sealed run's final receipt must be a real ALLOW_SESSION_CLOSE.
    from sentinel_core.reason_codes import is_session_close_shape
    require(is_session_close_shape(final.get("decision"), final.get("reason_code"),
                                   final.get("request"), final.get("executed")),
            "Sealed run's final receipt is not a valid ALLOW_SESSION_CLOSE receipt",
            ManifestError)

    saved_hash = seal["seal_hash"]
    require(type(saved_hash) is str and len(saved_hash) == 64,
            "run_seal seal_hash must be a 64-character hex string", ManifestError)
    recomputed = compute_run_seal_hash(seal)
    require(saved_hash == recomputed,
            f"run_seal hash mismatch: saved={saved_hash} recomputed={recomputed}", ManifestError)
    return seal
