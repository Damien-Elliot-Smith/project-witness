"""Shared helpers for Project Witness Connected Demo v0.1.

Standard library only. Canonical JSON, atomic writes, status reading. No frozen
component is imported; the orchestrator only reads the JSON reports the frozen
CLIs already write.
"""

import json
import os
import tempfile

CONNECTED_DEMO_VERSION = "0.1.0"

# Required terminal statuses the demo must observe, by stage.
REQUIRED = {
    "companion_status": "COMPANION_COMPLETED",
    "coordinator_workflow_status": "WORKFLOW_COMPLETED",
    "atlas_validation_status": "ATLAS_VALIDATED",
    "source_status": "SOURCE_VERIFIED",
    "stack_verification_status": "STACK_VERIFIED",
    "stack_selfcheck_status": "STACK_SELFCHECK_PASSED",
}
DEMO_COMPLETED = "DEMO_COMPLETED"
DEMO_FAILED = "DEMO_FAILED"


def require(condition, message):
    if not condition:
        raise DemoError(message)


class DemoError(Exception):
    pass


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
