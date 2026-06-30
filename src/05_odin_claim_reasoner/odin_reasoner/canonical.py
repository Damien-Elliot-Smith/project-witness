# odin_reasoner/canonical.py
# Deterministic canonical JSON. Standard library only.

import json

from odin_reasoner.errors import OdinError


def canonical_json(obj) -> str:
    try:
        body = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as e:
        raise OdinError(f"Value is not canonical-JSON serialisable: {e}")
    return body + "\n"


def canonical_bytes(obj) -> bytes:
    return canonical_json(obj).encode("utf-8")
