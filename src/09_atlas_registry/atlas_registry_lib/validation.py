# atlas_registry_lib/validation.py
# Validate identifiers and SHA-256 digests; SHA helpers.

import hashlib
import re

from atlas_registry_lib.errors import require, RegistryError
from atlas_registry_lib import versions

_SAFE_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
_MAX_NAME = 128
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def is_safe_id(value) -> bool:
    """A safe id: simple token, no path separators, no control chars. Dots are
    allowed (predicate names like evidence.present use them) but not leading."""
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


def validate_id(value, *, label, status=None):
    st = status or versions.FAILED_SCHEMA_INVALID
    require(isinstance(value, str) and value != "",
            f"{label} must be a non-empty string", RegistryError,
            registry_status=st, reason="EMPTY_ID")
    require(is_safe_id(value), f"unsafe {label}: {value!r}", RegistryError,
            registry_status=st, reason="UNSAFE_ID")
    return value


def is_valid_sha256(value) -> bool:
    return isinstance(value, str) and bool(_SHA256_RE.match(value))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
