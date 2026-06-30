# sentinel_core/canonical.py
# Strict canonical JSON for hashing.
# Rejects non-JSON-native values instead of stringifying them, so that two
# semantically different inputs can never collapse to the same hash through
# silent coercion. Normalises tuples to lists; rejects sets, non-finite
# floats, and non-string dict keys.

import json
import math
from typing import Any

from sentinel_core.errors import ReceiptError


def _normalise(obj: Any, path: str = "") -> Any:
    if obj is None or isinstance(obj, bool):
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            raise ReceiptError(
                f"Non-finite float at {path!r}: {obj!r} — not allowed in canonical JSON"
            )
        return obj
    if isinstance(obj, str):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_normalise(v, f"{path}[{i}]") for i, v in enumerate(obj)]
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if not isinstance(k, str):
                raise ReceiptError(
                    f"Non-string dict key at {path!r}: {k!r} — only str keys allowed"
                )
            out[k] = _normalise(v, f"{path}.{k}")
        return out
    if isinstance(obj, (set, frozenset)):
        raise ReceiptError(
            f"Set/frozenset at {path!r} — sets are not allowed in canonical data "
            f"(non-deterministic ordering). Convert to a sorted list first."
        )
    raise ReceiptError(
        f"Unsupported type {type(obj).__name__!r} at {path!r} — "
        f"only JSON-native types allowed in canonical data"
    )


def canonical_json(obj: Any) -> str:
    """Produce a deterministic canonical JSON string suitable for hashing."""
    normalised = _normalise(obj)
    return json.dumps(
        normalised,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
