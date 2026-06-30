# sentinel_core/manifest.py
# Versioned, self-contained run manifest with hash binding.
#
# The manifest pins the version vector, run_id, allowed_root and initial
# session state. Its hash is computed over every field except manifest_hash
# itself, so mutating any bound field without recomputing the hash is detected
# at load. load_run_file is the untrusted-file entry point and fails closed on
# hostile JSON (including deeply nested input that can raise RecursionError).

import copy
import hashlib
import json

from sentinel_core.canonical import canonical_json
from sentinel_core.errors import ManifestError, ReplayIncompatible, require
from sentinel_core.run_seal import RUN_SEAL_FIELD, OPEN_RUN_SEAL
from sentinel_core.session import SESSION_OPEN
from sentinel_core.versions import CURRENT_VERSION_VECTOR


def _manifest_payload(manifest: dict) -> dict:
    return {k: v for k, v in manifest.items() if k != "manifest_hash"}


def compute_manifest_hash(manifest: dict) -> str:
    payload = canonical_json(_manifest_payload(manifest))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_manifest(run_id: str, allowed_root: str) -> dict:
    manifest = {
        **CURRENT_VERSION_VECTOR,
        "run_id": run_id,
        "allowed_root": allowed_root,
        "initial_session_state": SESSION_OPEN,
    }
    manifest["manifest_hash"] = compute_manifest_hash(manifest)
    return {"manifest": manifest, "receipts": [], RUN_SEAL_FIELD: OPEN_RUN_SEAL}


def require_current_compatibility(manifest: dict) -> None:
    mismatches = {}
    for fieldname, expected in CURRENT_VERSION_VECTOR.items():
        actual = manifest.get(fieldname)
        if actual != expected:
            mismatches[fieldname] = {"expected": expected, "actual": actual}
    if mismatches:
        raise ReplayIncompatible(f"Version vector mismatch: {mismatches}")


def validate_manifest(data) -> dict:
    require(type(data) is dict, "Run file root must be an object", ManifestError)
    require("manifest" in data, "Run file missing 'manifest' key", ManifestError)
    require("receipts" in data, "Run file missing 'receipts' key", ManifestError)
    require(type(data["receipts"]) is list, "Run file 'receipts' must be an array", ManifestError)
    m = data["manifest"]
    require(type(m) is dict, "Manifest must be an object", ManifestError)

    required = set(CURRENT_VERSION_VECTOR.keys()) | {
        "run_id", "allowed_root", "initial_session_state", "manifest_hash",
    }
    keys = set(m.keys())
    require(keys == required,
            f"Manifest field mismatch: missing={sorted(required - keys)}, "
            f"extra={sorted(keys - required)}", ManifestError)

    saved_hash = m["manifest_hash"]
    require(type(saved_hash) is str and len(saved_hash) == 64,
            "Manifest hash must be a 64-character hex string", ManifestError)
    recomputed = compute_manifest_hash(m)
    require(saved_hash == recomputed,
            f"Manifest hash mismatch: saved={saved_hash} recomputed={recomputed}", ManifestError)

    for key in ("run_id", "allowed_root", "initial_session_state"):
        require(type(m[key]) is str and m[key] != "",
                f"Manifest {key} must be non-empty str", ManifestError)
    require(m["initial_session_state"] == SESSION_OPEN,
            "Manifest initial_session_state must be OPEN", ManifestError)

    try:
        require_current_compatibility(m)
    except ReplayIncompatible:
        raise
    except Exception as e:
        raise ManifestError(f"Compatibility check failed: {e}") from e
    return m


def clone_manifest_run_data(manifest: dict) -> dict:
    return {"manifest": copy.deepcopy(manifest), "receipts": [], RUN_SEAL_FIELD: OPEN_RUN_SEAL}


def load_run_file(path: str) -> dict:
    """Load a run file, converting hostile/malformed JSON into ManifestError.

    Replay is the public untrusted-file entry point, so every decoder failure
    mode is mapped to a controlled ManifestError. Deeply nested JSON can raise
    RecursionError inside the decoder before schema validation begins; that is
    caught here so the caller fails closed rather than crashing.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise ManifestError(f"Run file not found: {path!r}")
    except OSError as e:
        raise ManifestError(f"Failed to read run file {path!r}: {e}")
    except UnicodeDecodeError as e:
        raise ManifestError(f"Run file is not valid UTF-8 JSON: {e}")
    except json.JSONDecodeError as e:
        raise ManifestError(f"Run file is not valid JSON: {e}")
    except RecursionError as e:
        raise ManifestError(f"Run file JSON is too deeply nested: {e}")
    except ValueError as e:
        raise ManifestError(f"Run file JSON decoding failed: {e}")
