# aletheia_odin_bridge/validation.py
# Validate identifiers and SHA-256 digests. Strict by design.

import hashlib
import re

from aletheia_odin_bridge.errors import require, ManifestError

_SAFE_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
_MAX_NAME = 128
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def is_safe_id(value) -> bool:
    if not isinstance(value, str):
        return False
    if not value or len(value) > _MAX_NAME:
        return False
    if value in (".", ".."):
        return False
    if value[0] in "-.":
        return False
    if "/" in value or "\\" in value:
        return False
    if any(ord(c) < 0x20 or ord(c) == 0x7F for c in value):
        return False
    return all(c in _SAFE_CHARS for c in value)


def validate_id(value, *, label) -> str:
    require(isinstance(value, str) and value != "",
            f"{label} must be a non-empty string", ManifestError,
            reason="MANIFEST_ID_EMPTY")
    require(is_safe_id(value),
            f"unsafe {label} {value!r}: must be a simple name (no path "
            f"separators, no '..', no leading '-'/'.', no control characters)",
            ManifestError, reason="MANIFEST_ID_UNSAFE")
    return value


def is_valid_sha256(value) -> bool:
    return isinstance(value, str) and bool(_SHA256_RE.match(value))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
