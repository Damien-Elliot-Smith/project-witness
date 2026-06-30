"""Input validation for Unified Case Manifest v0.1."""

import os
import re

from . import versions

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def is_safe_id(value):
    return bool(value) and isinstance(value, str) and bool(_SAFE_ID.match(value)) \
        and "/" not in value and "\\" not in value and ".." not in value


def is_valid_source_type(source_type):
    return source_type in versions.SOURCE_TYPES


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
