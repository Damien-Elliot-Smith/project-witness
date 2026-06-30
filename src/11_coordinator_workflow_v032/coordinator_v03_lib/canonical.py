"""Canonical JSON helpers and atomic writes (standard library only).

Coordinator canonical JSON has NO trailing newline. The Atlas registry copy keeps
the Atlas canonical form, which DOES end with a trailing newline; helpers for both
are provided so each file is checked against the right form.
"""

import json
import os
import tempfile


def canonical_bytes(obj):
    """Coordinator canonical JSON (no trailing newline)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def canonical_str(obj):
    return canonical_bytes(obj).decode("utf-8")


def atlas_canonical_bytes(obj):
    """Atlas Registry canonical JSON (trailing newline), matching Atlas v0.1."""
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False) + "\n").encode("utf-8")


def is_canonical_bytes(raw):
    if not isinstance(raw, (bytes, bytearray)):
        return False
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return False
    return canonical_bytes(obj) == bytes(raw)


def is_atlas_canonical_bytes(raw):
    if not isinstance(raw, (bytes, bytearray)):
        return False
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return False
    return atlas_canonical_bytes(obj) == bytes(raw)


def atomic_write_bytes(path, data):
    directory = os.path.dirname(os.path.abspath(path))
    if directory and not os.path.isdir(directory):
        os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".cwv3_", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def write_canonical(path, obj):
    atomic_write_bytes(path, canonical_bytes(obj))


def read_bytes(path):
    with open(path, "rb") as handle:
        return handle.read()


def load_json(path):
    return json.loads(read_bytes(path).decode("utf-8"))
