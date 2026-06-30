"""Input validation for Companion CLI v0.3 (read-only checks)."""

import os
import re

_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def is_safe_token(value):
    return bool(value) and isinstance(value, str) and bool(_SAFE_TOKEN.match(value)) \
        and "/" not in value and "\\" not in value and ".." not in value


def evidence_file_ok(path):
    """Evidence must be an existing regular file, not a directory or symlink."""
    if not path or os.path.islink(path):
        return False
    if not os.path.exists(path):
        return False
    if os.path.isdir(path):
        return False
    return os.path.isfile(path)


def is_dir(path):
    return bool(path) and os.path.isdir(path)


def output_dir_ok(path):
    """Output dir must be absent or empty."""
    if not os.path.exists(path):
        return True
    if not os.path.isdir(path):
        return False
    return len(os.listdir(path)) == 0
