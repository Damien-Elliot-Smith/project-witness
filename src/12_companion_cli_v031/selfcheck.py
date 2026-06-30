#!/usr/bin/env python3
"""In-process self-checks for Companion CLI v0.3. Small, fast gates only -- does
NOT run the full unit suite. No bare asserts, no subprocesses."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from companion_lib import (canonical, validation, request_builder, engine,
                          verifier, versions)
from companion_lib.coordinator_runner import FakeCoordinatorRunner
from companion_lib.errors import COMPANION_COMPLETED, ATLAS_VALIDATED


class SelfCheckError(Exception):
    pass


def _expect(cond, msg):
    if not cond:
        raise SelfCheckError(msg)


def gate_imports():
    for mod in ("canonical", "errors", "versions", "checksums", "steps",
                "validation", "fixtures", "coordinator_output",
                "coordinator_runner", "request_builder", "report", "engine",
                "verifier"):
        __import__("companion_lib." + mod)


def gate_canonical_json():
    raw = canonical.canonical_bytes({"b": 1, "a": 2})
    _expect(raw == b'{"a":2,"b":1}', "canonical ordering wrong")
    _expect(canonical.is_canonical_bytes(raw), "is_canonical false negative")


def gate_valid_cli_validation():
    _expect(validation.is_safe_token("case_001"), "safe token rejected")
    _expect(not validation.is_safe_token("../etc"), "unsafe token accepted")
    _expect(not validation.is_safe_token("a/b"), "slash token accepted")


def gate_request_builder_v03():
    roots = {k: "/tmp/%s" % k for k in versions.COMPONENT_ROOT_KEYS}
    req = request_builder.build_request("case_001", "evidence_001", "/tmp/e.txt",
                                        "/tmp/cases", "case_001", roots)
    _expect(req["coordinator_workflow_request_version"] == "0.3.0", "bad version")
    _expect("atlas_registry_root" in req["component_roots"], "no atlas root")
    _expect(canonical.is_canonical_bytes(canonical.canonical_bytes(req)),
            "request not canonical")


def _build_params(workdir):
    for k in versions.COMPONENT_ROOT_KEYS:
        os.makedirs(os.path.join(workdir, k), exist_ok=True)
    os.makedirs(os.path.join(workdir, "cases"), exist_ok=True)
    os.makedirs(os.path.join(workdir, "coordinator"), exist_ok=True)
    evidence = os.path.join(workdir, "evidence.txt")
    canonical.atomic_write_bytes(evidence, b"evidence")
    roots = {k: os.path.join(workdir, k) for k in versions.COMPONENT_ROOT_KEYS}
    return {
        "case_id": "case_001", "evidence_id": "evidence_001",
        "evidence_file": evidence, "allowed_root": os.path.join(workdir, "cases"),
        "case_directory_name": "case_001",
        "coordinator_root": os.path.join(workdir, "coordinator"),
        "out": os.path.join(workdir, "out"), "component_roots": roots,
    }


def gate_successful_fake_atlas_connected_companion_run():
    with tempfile.TemporaryDirectory() as workdir:
        params = _build_params(workdir)
        outcome = engine.create_evidence_case(params, FakeCoordinatorRunner())
        _expect(outcome.companion_status == COMPANION_COMPLETED,
                "fake companion run did not complete")


def gate_atlas_validation_status_mirrored():
    with tempfile.TemporaryDirectory() as workdir:
        params = _build_params(workdir)
        engine.create_evidence_case(params, FakeCoordinatorRunner())
        report = canonical.load_json(
            os.path.join(params["out"], "companion_report.json"))
        _expect(report["atlas_validation_status"] == ATLAS_VALIDATED,
                "atlas_validation_status not mirrored")


def gate_verify_valid_output():
    with tempfile.TemporaryDirectory() as workdir:
        params = _build_params(workdir)
        engine.create_evidence_case(params, FakeCoordinatorRunner())
        _expect(verifier.verify(params["out"]).ok, "verify of valid output failed")


def gate_no_truth_claims():
    with tempfile.TemporaryDirectory() as workdir:
        params = _build_params(workdir)
        engine.create_evidence_case(params, FakeCoordinatorRunner())
        # verify includes the truth scan; a clean run must pass it
        _expect(verifier.verify(params["out"]).ok, "truth scan failed on clean run")


GATES = (
    ("imports", gate_imports),
    ("canonical_json", gate_canonical_json),
    ("valid_cli_validation", gate_valid_cli_validation),
    ("request_builder_v03", gate_request_builder_v03),
    ("successful_fake_atlas_connected_companion_run",
     gate_successful_fake_atlas_connected_companion_run),
    ("atlas_validation_status_mirrored", gate_atlas_validation_status_mirrored),
    ("verify_valid_output", gate_verify_valid_output),
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
