#!/usr/bin/env python3
"""In-process self-checks for Coordinator Workflow v0.3.

Small, fast gates only -- does NOT run the full unit suite. No bare asserts, no
subprocesses.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coordinator_v03_lib import (canonical, atlas_validation, workflow,
                                 verifier, fixtures)
from coordinator_v03_lib.component_runners import FakeComponentRunner
from coordinator_v03_lib.errors import (
    ATLAS_VALIDATED, FAILED_ATLAS_TRUTH_CLAIM, FAILED_ATLAS_FORBIDDEN_ACTION,
    WORKFLOW_COMPLETED)


class SelfCheckError(Exception):
    pass


def _expect(cond, msg):
    if not cond:
        raise SelfCheckError(msg)


def gate_imports():
    for mod in ("canonical", "errors", "versions", "checksums", "steps",
                "atlas_validation", "component_runners", "report", "workflow",
                "verifier", "fixtures"):
        __import__("coordinator_v03_lib." + mod)


def gate_canonical_json():
    raw = canonical.canonical_bytes({"b": 1, "a": 2})
    _expect(raw == b'{"a":2,"b":1}', "canonical ordering wrong")
    _expect(canonical.is_canonical_bytes(raw), "is_canonical false negative")
    _expect(not canonical.is_canonical_bytes(b'{"a":2, "b":1}'),
            "is_canonical false positive")


def _atlas_root(workdir, **opts):
    root = os.path.join(workdir, "atlas")
    fixtures.make_fake_atlas_root(root, **opts)
    return root


def gate_valid_atlas_registry():
    with tempfile.TemporaryDirectory() as workdir:
        root = _atlas_root(workdir)
        reg_bytes = canonical.read_bytes(
            os.path.join(root, "registry", "atlas_registry.json"))
        import json
        obj = json.loads(reg_bytes.decode("utf-8"))
        _expect(atlas_validation.inprocess_verify(reg_bytes, obj),
                "valid registry failed in-process verify")


def gate_atlas_validation_pass():
    with tempfile.TemporaryDirectory() as workdir:
        root = _atlas_root(workdir)
        res = atlas_validation.validate(root)
        _expect(res.status == ATLAS_VALIDATED, "valid atlas not validated")


def gate_atlas_validation_refuses_truth():
    with tempfile.TemporaryDirectory() as workdir:
        root = _atlas_root(workdir, truth_claim_status=True)
        res = atlas_validation.validate(root)
        _expect(res.status == FAILED_ATLAS_TRUTH_CLAIM,
                "truth-claim registry not refused")


def gate_atlas_validation_refuses_forbidden_action():
    with tempfile.TemporaryDirectory() as workdir:
        root = _atlas_root(workdir, forbidden_action="WRITE_FILE")
        res = atlas_validation.validate(root)
        _expect(res.status == FAILED_ATLAS_FORBIDDEN_ACTION,
                "forbidden action not refused")


def _run_fake(workdir):
    root = _atlas_root(workdir)
    evidence = os.path.join(workdir, "evidence.txt")
    canonical.atomic_write_bytes(evidence, b"evidence")
    request = fixtures.build_request(workdir, root, evidence)
    out_dir = os.path.join(workdir, "out")
    outcome = workflow.run_workflow(request, out_dir, FakeComponentRunner())
    return out_dir, outcome


def gate_successful_fake_workflow():
    with tempfile.TemporaryDirectory() as workdir:
        _, outcome = _run_fake(workdir)
        _expect(outcome.workflow_status == WORKFLOW_COMPLETED,
                "fake workflow did not complete")


def gate_verify_valid_output():
    with tempfile.TemporaryDirectory() as workdir:
        out_dir, _ = _run_fake(workdir)
        result = verifier.verify(out_dir)
        _expect(result.ok, "verify of valid output failed")


GATES = (
    ("imports", gate_imports),
    ("canonical_json", gate_canonical_json),
    ("valid_atlas_registry", gate_valid_atlas_registry),
    ("atlas_validation_pass", gate_atlas_validation_pass),
    ("atlas_validation_refuses_truth", gate_atlas_validation_refuses_truth),
    ("atlas_validation_refuses_forbidden_action",
     gate_atlas_validation_refuses_forbidden_action),
    ("successful_fake_workflow", gate_successful_fake_workflow),
    ("verify_valid_output", gate_verify_valid_output),
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
