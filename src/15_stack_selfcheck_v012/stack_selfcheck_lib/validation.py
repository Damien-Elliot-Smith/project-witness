"""Input validation for Stack Selfcheck v0.1."""

import os
import re

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def is_safe_id(value):
    return bool(value) and isinstance(value, str) and bool(_SAFE_ID.match(value)) \
        and "/" not in value and "\\" not in value and ".." not in value


def is_version(value):
    return isinstance(value, str) and bool(_SEMVER.match(value))


def is_dir(path):
    return bool(path) and os.path.isdir(path)


def output_dir_ok(path):
    if not os.path.exists(path):
        return True
    if not os.path.isdir(path):
        return False
    return len(os.listdir(path)) == 0


def is_relative_path(path):
    return isinstance(path, str) and bool(path) and not os.path.isabs(path) \
        and not path.startswith("/") and ".." not in path.split("/")


def has_no_absolute_paths(obj):
    """Recursively confirm no string value looks like an absolute path."""
    if isinstance(obj, str):
        return not (obj.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", obj))
    if isinstance(obj, dict):
        return all(has_no_absolute_paths(v) for v in obj.values())
    if isinstance(obj, list):
        return all(has_no_absolute_paths(v) for v in obj)
    return True
