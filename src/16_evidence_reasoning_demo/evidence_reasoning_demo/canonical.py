# evidence_reasoning_demo/canonical.py
# Deterministic canonical JSON. Standard library only.

import json

from evidence_reasoning_demo.errors import DemoError


def canonical_json(obj) -> str:
    try:
        body = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as e:
        raise DemoError(f"Value is not canonical-JSON serialisable: {e}")
    return body + "\n"


def canonical_bytes(obj) -> bytes:
    return canonical_json(obj).encode("utf-8")
