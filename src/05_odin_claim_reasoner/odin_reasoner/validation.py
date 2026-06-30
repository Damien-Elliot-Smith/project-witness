# odin_reasoner/validation.py
# Validate identifiers used in claim sets. Strict by design.

import hashlib
import re

from odin_reasoner.errors import require, ValidationError

_SAFE_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
_MAX_NAME = 128
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def is_safe_id(value) -> bool:
    """A safe single-segment identifier: non-empty str, <=128 chars, restricted
    charset, not '.'/'..', no path separators, no control chars, no leading
    '-'/'.'. """
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


def validate_id(value, *, label, reason="UNSAFE_ID") -> str:
    require(isinstance(value, str) and value != "",
            f"{label} must be a non-empty string",
            ValidationError, reason="EMPTY_ID")
    require(is_safe_id(value),
            f"Unsafe {label} {value!r}: must be a simple name (no path "
            f"separators, no '..', no leading '-'/'.', no control characters, "
            f"<= {_MAX_NAME} chars)",
            ValidationError, reason=reason)
    return value


def is_valid_sha256(value) -> bool:
    return isinstance(value, str) and bool(_SHA256_RE.match(value))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
