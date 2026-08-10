"""Context-managed hash verification for pinned artifacts (Move 79 v8).

Extracted from the shell checker so the reads are context-managed AND
directly testable. Leaking file handles here produced ResourceWarnings
that a zero exit code hid — a false-green in the warning check itself.
"""

import hashlib
import json
import os


def sha256_file(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def load_pins(pins_path):
    with open(pins_path, "r", encoding="utf-8") as handle:
        return json.load(handle)["pins"]


def verify_pins(pins_path, root="."):
    """Return a list of (relpath, problem). Empty list means all match."""
    problems = []
    for rel, want in sorted(load_pins(pins_path).items()):
        full = os.path.join(root, rel)
        if not os.path.isfile(full):
            problems.append((rel, "MISSING"))
            continue
        got = sha256_file(full)
        if got != want:
            problems.append((rel, "MUTATED %s -> %s" % (want[:12], got[:12])))
    return problems
