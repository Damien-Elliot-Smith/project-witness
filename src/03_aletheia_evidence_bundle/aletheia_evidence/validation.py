# aletheia_evidence/validation.py
# Validate case_id / evidence_id and the source evidence file. Strict by design.

import os

from aletheia_evidence.errors import require, ValidationError
from aletheia_evidence import versions

_SAFE_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
_MAX_NAME = 128


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


def validate_id(value, *, label) -> str:
    require(isinstance(value, str) and value != "",
            f"{label} must be a non-empty string",
            ValidationError, reason="EMPTY_ID")
    require(is_safe_id(value),
            f"Unsafe {label} {value!r}: must be a simple name (no path "
            f"separators, no '..', no leading '-'/'.', no control characters, "
            f"<= {_MAX_NAME} chars)",
            ValidationError, reason="UNSAFE_ID")
    return value


def validate_source_file(path) -> int:
    """Validate the source evidence file. Returns its size in bytes.

    Refuses: missing, directory, symlink, and oversized files. Uses lstat so a
    symlink is detected before following it.
    """
    require(isinstance(path, str) and path != "",
            "source file path must be a non-empty string",
            ValidationError, reason="EMPTY_PATH")
    require(os.path.lexists(path),
            f"source file does not exist: {path!r}",
            ValidationError, reason="MISSING_FILE")
    # lstat: do not follow symlinks for the type check.
    st = os.lstat(path)
    import stat as _stat
    require(not _stat.S_ISLNK(st.st_mode),
            f"source file is a symlink (refused): {path!r}",
            ValidationError, reason="SYMLINK_SOURCE")
    require(os.path.isfile(path) and not os.path.isdir(path),
            f"source must be a regular file, not a directory: {path!r}",
            ValidationError, reason="DIRECTORY_SOURCE")
    size = os.path.getsize(path)
    require(size <= versions.MAX_EVIDENCE_BYTES,
            f"source file is too large for v0.1 "
            f"({size} > {versions.MAX_EVIDENCE_BYTES} bytes)",
            ValidationError, reason="FILE_TOO_LARGE")
    return size
