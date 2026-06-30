#!/usr/bin/env python3
"""In-process self-checks for Atlas Release Gate v0.1.

Runs small, fast gates only -- it does NOT run the full unit-test suite.
Uses no bare asserts and no subprocesses.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from atlas_release_gate_lib import (canonical, gate, verifier,
                                    documentation_checks, feature_checks)
from atlas_release_gate_lib.atlas_runner import FakeAtlasRunner
from atlas_release_gate_lib.fixtures import make_fake_atlas_root
from atlas_release_gate_lib.errors import VerifyError, RELEASE_GATE_PASSED


class SelfCheckError(Exception):
    pass


def _expect(condition, message):
    if not condition:
        raise SelfCheckError(message)


def gate_imports():
    for mod in ("canonical", "errors", "versions", "validation", "checksums",
                "feature_checks", "documentation_checks", "atlas_runner",
                "report", "steps", "gate", "verifier", "fixtures"):
        __import__("atlas_release_gate_lib." + mod)


def gate_canonical_json():
    raw = canonical.canonical_bytes({"b": 1, "a": 2})
    _expect(raw == b'{"a":2,"b":1}', "canonical ordering wrong")
    _expect(canonical.is_canonical_bytes(raw), "is_canonical false negative")
    _expect(not canonical.is_canonical_bytes(b'{"a":2, "b":1}'),
            "is_canonical false positive")


def _build_passed_run(workdir):
    atlas_root = os.path.join(workdir, "atlas")
    make_fake_atlas_root(atlas_root)
    out_dir = os.path.join(workdir, "out")
    outcome = gate.run_check(atlas_root, out_dir, FakeAtlasRunner())
    return out_dir, outcome


def gate_valid_fake_release_gate():
    with tempfile.TemporaryDirectory() as workdir:
        _, outcome = _build_passed_run(workdir)
        _expect(outcome.status == RELEASE_GATE_PASSED,
                "fake release gate did not pass")


def gate_documentation_checks():
    good = make_doc_good()
    _expect(documentation_checks.check_documentation(good) == [],
            "good docs flagged")
    _expect(documentation_checks.check_honesty(good) == [],
            "good honesty flagged")
    _expect(documentation_checks.check_documentation("nothing here") != [],
            "missing docs not flagged")


def make_doc_good():
    from atlas_release_gate_lib.fixtures import GOOD_README, GOOD_KNOWN_LIMITATIONS
    return GOOD_README + "\n" + GOOD_KNOWN_LIMITATIONS


def gate_forbidden_feature_checks():
    _expect(feature_checks.scan_forbidden_features(make_doc_good()) == [],
            "honest docs produced false positive")
    bad = "Atlas supports Coordinator integration and uses an LLM."
    _expect(feature_checks.scan_forbidden_features(bad) != [],
            "affirmative forbidden claim not detected")


def gate_verify_valid_output():
    with tempfile.TemporaryDirectory() as workdir:
        out_dir, _ = _build_passed_run(workdir)
        result = verifier.verify(out_dir)
        _expect(result.ok, "verify of valid output failed")


def gate_detect_tamper():
    with tempfile.TemporaryDirectory() as workdir:
        out_dir, _ = _build_passed_run(workdir)
        path = os.path.join(out_dir, "atlas_release_gate_report.json")
        data = canonical.read_bytes(path)
        canonical.atomic_write_bytes(path, data + b" ")
        try:
            verifier.verify(out_dir)
        except VerifyError:
            return
        raise SelfCheckError("tamper not detected")


def gate_no_truth_claims():
    with tempfile.TemporaryDirectory() as workdir:
        out_dir, _ = _build_passed_run(workdir)
        path = os.path.join(out_dir, "atlas_release_gate_report.json")
        report = canonical.load_json(path)
        report["known_limitations"].append("The evidence is true.")
        canonical.write_canonical(path, report)
        from atlas_release_gate_lib import checksums
        paths = checksums.present_canonical_paths(out_dir)
        canonical.atomic_write_bytes(
            os.path.join(out_dir, "atlas_release_gate_checksums.txt"),
            checksums.build_checksums_text(out_dir, paths))
        try:
            verifier.verify(out_dir)
        except VerifyError:
            return
        raise SelfCheckError("truth-like claim not rejected")


GATES = (
    ("imports", gate_imports),
    ("canonical_json", gate_canonical_json),
    ("valid_fake_release_gate", gate_valid_fake_release_gate),
    ("documentation_checks", gate_documentation_checks),
    ("forbidden_feature_checks", gate_forbidden_feature_checks),
    ("verify_valid_output", gate_verify_valid_output),
    ("detect_tamper", gate_detect_tamper),
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
