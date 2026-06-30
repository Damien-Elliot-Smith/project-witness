# histor_lite/canonical.py
# Deterministic canonical JSON and file hashing. Standard library only.
#
# Canonical form: keys sorted, compact separators, UTF-8, no NaN/Infinity, with
# a trailing newline. The same Python object always serialises to the same
# bytes, so a case summary's hash is reproducible.

import hashlib
import json

from histor_lite.errors import require, HistorLiteError


def canonical_json(obj) -> str:
    """Return the deterministic canonical JSON text for obj (with trailing \\n).

    Rejects NaN/Infinity (allow_nan=False) so a non-finite float cannot produce
    non-standard, non-portable JSON.
    """
    try:
        body = json.dumps(
            obj,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as e:
        raise HistorLiteError(f"Value is not canonical-JSON serialisable: {e}")
    return body + "\n"


def canonical_bytes(obj) -> bytes:
    return canonical_json(obj).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    require(isinstance(data, (bytes, bytearray)), "sha256_hex needs bytes")
    return hashlib.sha256(data).hexdigest()


def hash_file(path: str) -> str:
    """SHA-256 of a file's bytes, read in chunks (no whole-file load)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
