"""Move 71 reason-code registry extractor.

Scans every component under src/ for module-level string constants of the
form NAME = "VALUE" where both sides are UPPER_SNAKE. These are the status
and reason codes the frozen Python stack emits; the registry freezes that
vocabulary so any future verifier (including the Part Two Rust verifier)
can align its reason codes to the reference and so silent vocabulary
drift becomes detectable.

Deterministic: sorted walk, sorted output. Stdlib only.
Regenerate and diff against the frozen copy to detect drift:

    python3 extract_reason_codes.py <src_root>
"""

import json
import os
import re
import sys

_CONST = re.compile(
    r'^([A-Z][A-Z0-9_]*)\s*=\s*"([A-Z][A-Z0-9_]*)"\s*(?:#.*)?$')


def extract(src_root):
    registry = {}
    for component in sorted(os.listdir(src_root)):
        comp_dir = os.path.join(src_root, component)
        if not os.path.isdir(comp_dir):
            continue
        codes = {}
        for root, dirs, files in os.walk(comp_dir):
            dirs.sort()
            dirs[:] = [d for d in dirs
                       if d not in ("__pycache__", "_frozen", "tests")]
            for name in sorted(files):
                if not name.endswith(".py"):
                    continue
                path = os.path.join(root, name)
                with open(path, "r", encoding="utf-8") as handle:
                    for line in handle:
                        match = _CONST.match(line.rstrip())
                        if match:
                            codes[match.group(1)] = match.group(2)
        if codes:
            registry[component] = dict(sorted(codes.items()))
    return registry


def main():
    src_root = sys.argv[1] if len(sys.argv) > 1 else "src"
    registry = extract(src_root)
    total = sum(len(v) for v in registry.values())
    payload = {
        "extraction_rule":
            'module-level NAME = "VALUE" where both sides are UPPER_SNAKE; '
            "__pycache__, _frozen and tests directories excluded",
        "total_codes": total,
        "components": registry,
    }
    print(json.dumps(payload, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
