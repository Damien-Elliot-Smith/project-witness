"""Canonical JSON and atomic writes (standard library only)."""

import json
import os
import tempfile

from .errors import CheckError


def require(condition, status, message):
    if not condition:
        raise CheckError(status, message)


def canonical_bytes(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def write_canonical(path, obj):
    atomic_write_bytes(path, canonical_bytes(obj))


def atomic_write_bytes(path, data):
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=directory)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)
