#!/usr/bin/env python3
"""In-process self-checks for Unified Case Manifest v0.1. Small, fast gates only
-- does NOT run the full unit suite. No bare asserts, no subprocesses."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unified_manifest_lib import canonical, manifest as manifest_mod, verifier, versions
from unified_manifest_lib.errors import BuildError
from tests.synthetic import build_coordinator_source, build_companion_source


class SelfCheckError(Exception):
    pass


def _expect(cond, msg):
    if not cond:
        raise SelfCheckError(msg)


def _build_out(source_type, source_run, work):
    out = os.path.join(work, "out")
    manifest, source_index = manifest_mod.build_manifest_data(source_type, source_run)
    os.makedirs(out, exist_ok=True)
    canonical.write_canonical(os.path.join(out, "unified_case_manifest.json"), manifest)
    canonical.write_canonical(os.path.join(out, "source_index.json"), source_index)
    from unified_manifest_lib import checksums
    canonical.atomic_write_bytes(
        os.path.join(out, "unified_manifest_checksums.txt"),
        checksums.build_checksums_text(out))
    return out, manifest


def gate_imports():
    for mod in ("canonical", "errors", "versions", "validation", "checksums",
                "source_reader", "atlas_checks", "artifact_index", "manifest",
                "verifier"):
        __import__("unified_manifest_lib." + mod)


def gate_canonical_json():
    raw = canonical.canonical_bytes({"b": 1, "a": 2})
    _expect(raw == b'{"a":2,"b":1}', "canonical ordering wrong")
    _expect(canonical.is_canonical_bytes(raw), "is_canonical false negative")


def gate_valid_coordinator_source():
    with tempfile.TemporaryDirectory() as work:
        src = os.path.join(work, "coord"); build_coordinator_source(src)
        manifest, _ = manifest_mod.build_manifest_data(
            versions.SOURCE_TYPE_COORDINATOR, src)
        _expect(manifest["source_status"] == "SOURCE_VERIFIED", "coord source failed")
        _expect(manifest["companion_status"] == "NOT_APPLICABLE",
                "coord companion_status should be NOT_APPLICABLE")


def gate_valid_companion_source():
    with tempfile.TemporaryDirectory() as work:
        src = os.path.join(work, "companion"); build_companion_source(src)
        manifest, _ = manifest_mod.build_manifest_data(
            versions.SOURCE_TYPE_COMPANION, src)
        _expect(manifest["source_status"] == "SOURCE_VERIFIED", "companion source failed")
        _expect(manifest["companion_status"] == "COMPANION_COMPLETED",
                "companion_status not mirrored")


def gate_atlas_truth_refused():
    with tempfile.TemporaryDirectory() as work:
        src = os.path.join(work, "coord")
        build_coordinator_source(src, registry_opts={"truth_claim_status": True})
        try:
            manifest_mod.build_manifest_data(versions.SOURCE_TYPE_COORDINATOR, src)
            raise SelfCheckError("atlas truth claim was not refused")
        except BuildError:
            pass


def gate_forbidden_action_refused():
    with tempfile.TemporaryDirectory() as work:
        src = os.path.join(work, "coord")
        build_coordinator_source(src, registry_opts={"forbidden_action": "WRITE_FILE"})
        try:
            manifest_mod.build_manifest_data(versions.SOURCE_TYPE_COORDINATOR, src)
            raise SelfCheckError("forbidden action was not refused")
        except BuildError:
            pass


def gate_verify_valid_manifest():
    with tempfile.TemporaryDirectory() as work:
        src = os.path.join(work, "companion"); build_companion_source(src)
        out, _ = _build_out(versions.SOURCE_TYPE_COMPANION, src, work)
        _expect(verifier.verify(out).ok, "verify of valid manifest failed")


def gate_no_truth_claims():
    with tempfile.TemporaryDirectory() as work:
        src = os.path.join(work, "coord"); build_coordinator_source(src)
        out, _ = _build_out(versions.SOURCE_TYPE_COORDINATOR, src, work)
        _expect(verifier.verify(out).ok, "truth scan failed on clean manifest")


GATES = (
    ("imports", gate_imports),
    ("canonical_json", gate_canonical_json),
    ("valid_coordinator_source", gate_valid_coordinator_source),
    ("valid_companion_source", gate_valid_companion_source),
    ("atlas_truth_refused", gate_atlas_truth_refused),
    ("forbidden_action_refused", gate_forbidden_action_refused),
    ("verify_valid_manifest", gate_verify_valid_manifest),
    ("no_truth_claims", gate_no_truth_claims),
)


def main():
    failures = []
    for name, func in GATES:
        try:
            func()
            print("PASS  " + name)
        except Exception as exc:
            failures.append((name, exc))
            print("FAIL  %s: %s" % (name, exc))
    if failures:
        print("selfcheck: %d gate(s) failed" % len(failures))
        return 1
    print("selfcheck: all %d gates passed" % len(GATES))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
