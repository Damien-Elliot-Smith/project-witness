#!/usr/bin/env python3
"""In-process self-checks for Stack Verifier v0.1. Small, fast gates only -- does
NOT run the full unit suite. No bare asserts, no subprocesses."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stack_verifier_lib import (canonical, report as report_mod, steps as steps_mod,
                              checksums, verifier, versions)
from stack_verifier_lib.errors import CheckError
from tests.synthetic import (build_coordinator_source, build_companion_source,
                             build_unified_manifest_output)


class SelfCheckError(Exception):
    pass


def _expect(cond, msg):
    if not cond:
        raise SelfCheckError(msg)


def _write_out(report, work):
    out = os.path.join(work, "out_%d" % len(os.listdir(work)))
    os.makedirs(out, exist_ok=True)
    canonical.write_canonical(os.path.join(out, "stack_verification_report.json"), report)
    canonical.write_canonical(os.path.join(out, "stack_verification_steps.json"),
                              steps_mod.build_steps(steps_mod.all_completed()))
    canonical.atomic_write_bytes(
        os.path.join(out, "stack_verification_checksums.txt"),
        checksums.build_checksums_text(out))
    return out


def gate_imports():
    for mod in ("canonical", "errors", "versions", "validation", "checksums",
                "steps", "source_reader", "source_verifier", "manifest_reader",
                "atlas_checks", "artifact_checks", "report", "verifier"):
        __import__("stack_verifier_lib." + mod)


def gate_canonical_json():
    raw = canonical.canonical_bytes({"b": 1, "a": 2})
    _expect(raw == b'{"a":2,"b":1}', "canonical ordering wrong")
    _expect(canonical.is_canonical_bytes(raw), "is_canonical false negative")


def gate_valid_companion_source():
    with tempfile.TemporaryDirectory() as work:
        src = os.path.join(work, "comp"); build_companion_source(src)
        report, _ = report_mod.build_stack_report(versions.SOURCE_TYPE_COMPANION, src)
        _expect(report["stack_verification_status"] == "STACK_VERIFIED", "companion failed")
        _expect(report["manifest_status"] == "NOT_PROVIDED", "manifest should be NOT_PROVIDED")


def gate_valid_coordinator_source():
    with tempfile.TemporaryDirectory() as work:
        src = os.path.join(work, "coord"); build_coordinator_source(src)
        report, _ = report_mod.build_stack_report(versions.SOURCE_TYPE_COORDINATOR, src)
        _expect(report["stack_verification_status"] == "STACK_VERIFIED", "coord failed")
        _expect(report["companion_status"] == "NOT_APPLICABLE", "companion_status wrong")


def gate_valid_source_plus_manifest():
    with tempfile.TemporaryDirectory() as work:
        src = os.path.join(work, "comp"); build_companion_source(src)
        man = os.path.join(work, "man")
        build_unified_manifest_output(man, versions.SOURCE_TYPE_COMPANION, src)
        report, _ = report_mod.build_stack_report(
            versions.SOURCE_TYPE_COMPANION, src, man)
        _expect(report["manifest_status"] == "MANIFEST_VERIFIED", "manifest not verified")
        _expect(report["manifest_consistent"] is True, "manifest not consistent")


def gate_atlas_truth_refused():
    with tempfile.TemporaryDirectory() as work:
        src = os.path.join(work, "coord")
        build_coordinator_source(src, registry_opts={"truth_claim_status": True})
        try:
            report_mod.build_stack_report(versions.SOURCE_TYPE_COORDINATOR, src)
            raise SelfCheckError("atlas truth claim not refused")
        except CheckError:
            pass


def gate_manifest_mismatch_refused():
    with tempfile.TemporaryDirectory() as work:
        src = os.path.join(work, "comp"); build_companion_source(src)
        man = os.path.join(work, "man")
        build_unified_manifest_output(man, versions.SOURCE_TYPE_COMPANION, src,
                                      override_case_id="case_tampered00000")
        try:
            report_mod.build_stack_report(versions.SOURCE_TYPE_COMPANION, src, man)
            raise SelfCheckError("manifest mismatch not refused")
        except CheckError:
            pass


def gate_verify_valid_stack_report():
    with tempfile.TemporaryDirectory() as work:
        src = os.path.join(work, "coord"); build_coordinator_source(src)
        report, _ = report_mod.build_stack_report(versions.SOURCE_TYPE_COORDINATOR, src)
        out = _write_out(report, work)
        _expect(verifier.verify(out).ok, "verify of valid stack report failed")


GATES = (
    ("imports", gate_imports),
    ("canonical_json", gate_canonical_json),
    ("valid_companion_source", gate_valid_companion_source),
    ("valid_coordinator_source", gate_valid_coordinator_source),
    ("valid_source_plus_manifest", gate_valid_source_plus_manifest),
    ("atlas_truth_refused", gate_atlas_truth_refused),
    ("manifest_mismatch_refused", gate_manifest_mismatch_refused),
    ("verify_valid_stack_report", gate_verify_valid_stack_report),
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
