#!/usr/bin/env python3
# selfcheck.py
# Evidence Reasoning Demo v0.1 self-check: in-process invariant gates only.
# Never launches the unit suite or any subprocess (uses an in-process fake runner).

import ast
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from evidence_reasoning_demo.canonical import canonical_json  # noqa: E402
from evidence_reasoning_demo.errors import (  # noqa: E402
    require, DemoError, ValidationError, StepError, VerifyError)
from evidence_reasoning_demo.validation import validate_id, is_safe_id  # noqa: E402
from evidence_reasoning_demo.verifier import verify_run  # noqa: E402
from evidence_reasoning_demo import versions  # noqa: E402

_SHA = "fe482b5e524c67728f4f2b4f430cd10d9a25659641f995ae537b282ccd181e0b"


def _ok(cond, msg):
    require(cond, msg, DemoError)


def _dump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, sort_keys=True,
                  separators=(",", ":"))
        f.write("\n")


class _FakeRunner:
    """Minimal in-process fake: writes component outputs, optional fail_at."""

    def __init__(self, fail_at=None):
        self.fail_at = fail_at
        self.calls = []

    def _f(self, op, status):
        self.calls.append(op)
        if self.fail_at == op:
            raise StepError(status, f"fake failure at {op}")

    def aletheia_bundle(self, evidence_file, case_id, evidence_id, out_dir):
        self._f("aletheia_bundle", versions.FAILED_ALETHEIA_BUNDLE)
        _dump(os.path.join(out_dir, "evidence_manifest.json"), {
            "evidence_id": evidence_id, "case_id": case_id,
            "evidence_status": "VERIFIED_PRESENT", "bundled_file_sha256": _SHA})
        return True

    def aletheia_verify(self, bundle_dir):
        self._f("aletheia_verify", versions.FAILED_ALETHEIA_VERIFY)
        return True

    def bridge_convert(self, aletheia_root, odin_root, bundle_dir, out_dir):
        self._f("bridge_convert", versions.FAILED_BRIDGE_CONVERT)
        _dump(os.path.join(out_dir, "bridge_report.json"), {
            "case_id": "case_001", "evidence_id": "evidence_001",
            "bridge_status": "CONVERTED", "odin_claim_count": 2,
            "generated_claims": ["evidence.present",
                                 "evidence.integrity_verified"]})
        _dump(os.path.join(out_dir, "odin_claims.json"), {
            "odin_claim_set_version": "0.1.0", "case_id": "case_001",
            "claims": []})
        return True

    def bridge_verify(self, run_dir):
        self._f("bridge_verify", versions.FAILED_BRIDGE_VERIFY)
        return True

    def odin_reason(self, claims_path, out_dir):
        self._f("odin_reason", versions.FAILED_ODIN_REASON)
        _dump(os.path.join(out_dir, "reasoning_report.json"), {
            "case_id": "case_001", "reasoning_status": "CONSISTENT"})
        return True

    def odin_verify(self, run_dir):
        self._f("odin_verify", versions.FAILED_ODIN_VERIFY)
        return True


def _evidence_file():
    d = tempfile.mkdtemp()
    p = os.path.join(d, "e.txt")
    with open(p, "wb") as f:
        f.write(b"hello evidence\n")
    return p


def _run(out_dir, runner):
    import demo
    return demo.run_demo(
        evidence_file=_evidence_file(), case_id="case_001",
        evidence_id="evidence_001", aletheia_root="A", bridge_root="B",
        odin_root="O", out_dir=out_dir, runner=runner)


def gate_imports():
    import evidence_reasoning_demo  # noqa: F401
    from evidence_reasoning_demo import (  # noqa: F401
        canonical, errors, validation, component_runner, report, steps,
        checksums, verifier)
    _ok(versions.DEMO_VERSION == "0.1.0", "unexpected version")


def gate_canonical_json():
    a = canonical_json({"b": 1, "a": 2})
    _ok(a == canonical_json({"a": 2, "b": 1}), "canonical_json not deterministic")
    _ok(a.endswith("\n"), "canonical_json must end with newline")
    try:
        canonical_json({"x": float("nan")})
        _ok(False, "canonical_json must reject NaN")
    except DemoError:
        pass


def gate_validation():
    _ok(is_safe_id("case_001"), "safe id rejected")
    refused = False
    try:
        validate_id("../evil", label="case_id")
    except ValidationError:
        refused = True
    _ok(refused, "unsafe id not refused")


def gate_successful_fake_demo():
    out = os.path.join(tempfile.mkdtemp(), "out")
    result = _run(out, _FakeRunner())
    _ok(result.report["demo_status"] == versions.DEMO_COMPLETED,
        "fake demo did not complete")
    for name in (versions.DEMO_REPORT_NAME, versions.DEMO_STEPS_NAME,
                 versions.CHECKSUMS_NAME):
        _ok(os.path.isfile(os.path.join(out, name)), f"missing {name}")


def gate_failure_short_circuit():
    runner = _FakeRunner(fail_at="bridge_convert")
    caught = False
    try:
        _run(os.path.join(tempfile.mkdtemp(), "out"), runner)
    except StepError as e:
        caught = e.demo_status == versions.FAILED_BRIDGE_CONVERT
    _ok(caught, "bridge_convert failure not short-circuited")
    _ok("odin_reason" not in runner.calls, "odin ran after bridge failure")


def gate_verify_valid_output():
    out = os.path.join(tempfile.mkdtemp(), "out")
    _run(out, _FakeRunner())
    r = verify_run(out)
    _ok(r.demo_status == versions.DEMO_COMPLETED, "verify of fresh demo failed")


def gate_detect_tamper():
    out = os.path.join(tempfile.mkdtemp(), "out")
    _run(out, _FakeRunner())
    with open(os.path.join(out, versions.DEMO_REPORT_NAME), "ab") as f:
        f.write(b" ")
    caught = False
    try:
        verify_run(out)
    except VerifyError:
        caught = True
    _ok(caught, "verify failed to detect mutated demo_report.json")


def gate_no_truth_claims():
    out = os.path.join(tempfile.mkdtemp(), "out")
    result = _run(out, _FakeRunner())
    for pred in result.report["generated_claims"]:
        _ok(pred in versions.ALLOWED_PREDICATES, f"unexpected predicate {pred}")
        for token in versions.FORBIDDEN_PREDICATE_TOKENS:
            _ok(token not in pred.lower(),
                f"predicate {pred} contains forbidden {token}")


GATES = [
    ("imports", gate_imports),
    ("canonical_json", gate_canonical_json),
    ("validation", gate_validation),
    ("successful_fake_demo", gate_successful_fake_demo),
    ("failure_short_circuit", gate_failure_short_circuit),
    ("verify_valid_output", gate_verify_valid_output),
    ("detect_tamper", gate_detect_tamper),
    ("no_truth_claims", gate_no_truth_claims),
]


def main(argv=None):
    import argparse
    argparse.ArgumentParser(
        prog="selfcheck",
        description="Evidence Reasoning Demo v0.1 in-process gates.").parse_args(
        argv)
    print("=" * 60)
    print("  Evidence Reasoning Demo v0.1 — selfcheck (in-process gates)")
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
    print("  ALL PASS — Evidence Reasoning Demo v0.1 selfcheck satisfied.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
