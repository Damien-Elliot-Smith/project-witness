# evidence_reasoning_demo/validation.py
# Validate identifiers and the source evidence file; SHA-256 helpers.

import hashlib
import os
import re
import stat as _stat

from evidence_reasoning_demo.errors import require, ValidationError

_SAFE_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
_MAX_NAME = 128
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CHUNK = 1024 * 1024


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
            f"{label} must be a non-empty string", ValidationError,
            reason="EMPTY_ID")
    require(is_safe_id(value),
            f"unsafe {label} {value!r}: must be a simple name (no path "
            f"separators, no '..', no leading '-'/'.', no control characters)",
            ValidationError, reason="UNSAFE_ID")
    return value


def validate_source_file(path) -> None:
    """Refuse missing / directory / symlink evidence sources. (Size is left to
    frozen Aletheia, which enforces its own 10 MB limit.)"""
    require(isinstance(path, str) and path != "",
            "evidence file path must be a non-empty string", ValidationError,
            reason="EMPTY_PATH")
    require(os.path.lexists(path), f"evidence file does not exist: {path!r}",
            ValidationError, reason="MISSING_FILE")
    st = os.lstat(path)
    require(not _stat.S_ISLNK(st.st_mode),
            f"evidence file is a symlink (refused): {path!r}", ValidationError,
            reason="SYMLINK_SOURCE")
    require(os.path.isfile(path) and not os.path.isdir(path),
            f"evidence source must be a regular file, not a directory: {path!r}",
            ValidationError, reason="DIRECTORY_SOURCE")


def is_valid_sha256(value) -> bool:
    return isinstance(value, str) and bool(_SHA256_RE.match(value))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()
