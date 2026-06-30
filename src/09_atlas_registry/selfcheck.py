#!/usr/bin/env python3
# selfcheck.py
# Atlas Registry v0.1 self-check: in-process invariant gates only. Never launches
# the unit suite or any subprocess.

import copy
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from atlas_registry_lib.canonical import canonical_json, canonical_bytes  # noqa: E402
from atlas_registry_lib.errors import (  # noqa: E402
    require, AtlasError, RegistryError, ExportError)
from atlas_registry_lib.registry_model import build_registry  # noqa: E402
from atlas_registry_lib.verifier import verify_registry, verify_registry_obj  # noqa: E402
from atlas_registry_lib.exporter import export_registry, verify_export  # noqa: E402
from atlas_registry_lib import versions  # noqa: E402

REGISTRY_PATH = os.path.join(HERE, "registry", "atlas_registry.json")


def _ok(cond, msg):
    require(cond, msg, AtlasError)


def _write(reg):
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "atlas_registry.json")
    with open(path, "wb") as f:
        f.write(canonical_bytes(reg))
    return path


def gate_imports():
    from atlas_registry_lib import (  # noqa: F401
        canonical, errors, validation, registry_model, verifier, exporter,
        checksums)
    _ok(versions.ATLAS_REGISTRY_VERSION == "0.1.0", "unexpected version")


def gate_canonical_json():
    a = canonical_json({"b": 1, "a": 2})
    _ok(a == canonical_json({"a": 2, "b": 1}), "canonical_json not deterministic")
    _ok(a.endswith("\n"), "canonical_json must end with newline")


def gate_registry_load():
    if os.path.isfile(REGISTRY_PATH):
        verify_registry(REGISTRY_PATH)
    else:
        verify_registry_obj(build_registry())


def gate_registry_verify():
    r = verify_registry_obj(build_registry())
    _ok(r.registry_status == versions.REGISTRY_VERIFIED, "built registry invalid")


def gate_required_components_present():
    reg = build_registry()
    ids = {c["component_id"] for c in reg["components"]}
    for cid in versions.REQUIRED_COMPONENT_IDS:
        _ok(cid in ids, f"required component missing: {cid}")


def gate_truth_status_refused():
    reg = copy.deepcopy(build_registry())
    reg["statuses"][0]["truth_claim"] = True
    caught = False
    try:
        verify_registry_obj(reg)
    except RegistryError as e:
        caught = e.registry_status == versions.FAILED_TRUTH_CLAIM
    _ok(caught, "truth-claiming status not refused")


def gate_truth_predicate_refused():
    reg = copy.deepcopy(build_registry())
    reg["claim_predicates"].append({
        "predicate": "contents.true", "meaning": "x",
        "allowed_object_types": ["boolean"], "truth_claim": False,
        "introduced_by_component": "odin_claim_reasoner"})
    caught = False
    try:
        verify_registry_obj(reg)
    except RegistryError as e:
        caught = e.registry_status == versions.FAILED_TRUTH_CLAIM
    _ok(caught, "truth-like predicate not refused")


def gate_export_verify():
    out = os.path.join(tempfile.mkdtemp(), "export")
    export_registry(_write(build_registry()), out)
    summary = verify_export(out)
    _ok(summary["registry_status"] == versions.REGISTRY_VERIFIED,
        "export verify failed")


GATES = [
    ("imports", gate_imports),
    ("canonical_json", gate_canonical_json),
    ("registry_load", gate_registry_load),
    ("registry_verify", gate_registry_verify),
    ("required_components_present", gate_required_components_present),
    ("truth_status_refused", gate_truth_status_refused),
    ("truth_predicate_refused", gate_truth_predicate_refused),
    ("export_verify", gate_export_verify),
]


def main(argv=None):
    import argparse
    argparse.ArgumentParser(
        prog="selfcheck",
        description="Atlas Registry v0.1 in-process gates.").parse_args(argv)
    print("=" * 60)
    print("  Atlas Registry v0.1 — selfcheck (in-process gates)")
    print("=" * 60)
    passed = 0
    failed = []
    for name, fn in GATES:
        try:
            fn()
            print(f"  [PASS] {name}")
            passed += 1
        except Exception as e:  # noqa: BLE001
            print(f"  [FAIL] {name}: {e}")
            failed.append(name)
    print("=" * 60)
    print(f"  {passed}/{len(GATES)} gates passed")
    if failed:
        print(f"  FAILED: {failed}")
        return 1
    print("  ALL PASS — Atlas Registry v0.1 selfcheck satisfied.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
