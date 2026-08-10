"""Deterministic hash of the BEHAVIOUR-DETERMINING Rust source (Move 79 v11).

WHAT IS PINNED, AND WHY THIS SCOPE
----------------------------------
Only files that determine COMPILED BEHAVIOUR:
    *.rs      — the implementation
    Cargo.toml — dependency and crate configuration

EXCLUDED, DELIBERATELY:
    rust/README.md and any other documentation. Documentation MUST advance
    every Rust move (tools/check_rust_workspace.sh REQUIRES the README status
    line to name the current step). A v10 pin that covered README.md created a
    self-referential deadlock: one rule mandated the change another rule
    forbade, so the gate would fail the moment Move 80 rolled the status line.
    Documentation correctness is enforced by check_rust_workspace.sh, which is
    the right instrument for it. The pin's job is to prove the COMPILED
    ARTEFACT comes from reviewed code — nothing else.
    rust/target/ — build output, not source.

The set of pinned paths is written into the pin file itself, so the SCOPE is
auditable and cannot drift silently: if a new .rs file appears (or one
vanishes), the recorded path list changes and the pin no longer matches.
"""

import hashlib
import json
import os
import sys

BEHAVIOUR_SUFFIXES = (".rs",)
BEHAVIOUR_NAMES = ("Cargo.toml",)


def behaviour_paths(root="rust"):
    paths = []
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs
                         if d not in ("target", "__pycache__"))
        for name in sorted(files):
            if name.endswith(BEHAVIOUR_SUFFIXES) or name in BEHAVIOUR_NAMES:
                paths.append(os.path.join(base, name))
    return sorted(p.replace(os.sep, "/") for p in paths)


def rust_source_hash(root="rust"):
    """Hash of the behaviour-determining source. The relative path is folded
    in, so renaming a file changes the hash."""
    digest = hashlib.sha256()
    for rel in behaviour_paths(root):
        with open(rel, "rb") as handle:
            body = handle.read()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(body).hexdigest().encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def pin_payload(root="rust"):
    paths = behaviour_paths(root)
    return {
        "scope": "behaviour-determining Rust source only (*.rs, Cargo.toml)",
        "excluded": ["rust/README.md and all documentation (it MUST change "
                     "each Rust move; enforced instead by "
                     "tools/check_rust_workspace.sh)",
                     "rust/target/ (build output)"],
        "pinned_paths": paths,
        "pinned_path_count": len(paths),
        "rust_source_sha256": rust_source_hash(root),
    }


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--payload":
        print(json.dumps(pin_payload(), indent=1, sort_keys=True))
    else:
        print(rust_source_hash())
