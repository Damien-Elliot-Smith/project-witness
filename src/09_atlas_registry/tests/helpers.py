# tests/helpers.py
# Helpers for Atlas Registry v0.1 tests. Builds in-memory registries (valid and
# mutated) and writes temporary registry files / exports in process.

import copy
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from atlas_registry_lib.canonical import canonical_bytes  # noqa: E402
from atlas_registry_lib.registry_model import build_registry  # noqa: E402
from atlas_registry_lib import versions  # noqa: E402

# The real registry shipped in the package.
REGISTRY_PATH = os.path.join(HERE, "registry", "atlas_registry.json")


def good_registry():
    return build_registry()


def write_registry(reg, tmp=None):
    tmp = tmp or tempfile.mkdtemp(prefix="atlas_")
    path = os.path.join(tmp, "atlas_registry.json")
    with open(path, "wb") as f:
        f.write(canonical_bytes(reg))
    return path


def write_registry_raw(raw_bytes, tmp=None):
    tmp = tmp or tempfile.mkdtemp(prefix="atlas_")
    path = os.path.join(tmp, "atlas_registry.json")
    with open(path, "wb") as f:
        f.write(raw_bytes)
    return path


def mutate(fn):
    """Return a deep-copied registry mutated by fn(reg)."""
    reg = copy.deepcopy(build_registry())
    fn(reg)
    return reg


def export_dir():
    return os.path.join(tempfile.mkdtemp(prefix="atlas_exp_"), "export")


def good_export():
    from atlas_registry_lib.exporter import export_registry
    out = export_dir()
    path = write_registry(build_registry())
    export_registry(path, out)
    return out


def shaf(path):
    import hashlib
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()
