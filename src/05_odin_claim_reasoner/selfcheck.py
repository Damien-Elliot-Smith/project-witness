#!/usr/bin/env python3
# selfcheck.py
# ODIN Claim Reasoner v0.1 self-check: in-process invariant gates only.
# Never launches the unit suite or any subprocess.

import ast
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from odin_reasoner.canonical import canonical_json  # noqa: E402
from odin_reasoner.errors import (  # noqa: E402
    require, OdinError, ValidationError)
from odin_reasoner.claims import validate_claim_set  # noqa: E402
from odin_reasoner.contradictions import find_contradictions  # noqa: E402
from odin_reasoner.reasoner import build_reasoning, reason_to_dir  # noqa: E402
from odin_reasoner.verifier import verify_run  # noqa: E402
from odin_reasoner import versions  # noqa: E402


def _ok(cond, msg):
    require(cond, msg, OdinError)


def _support(sid="support_001", sha="a" * 64):
    return {"support_id": sid, "source_component": "c", "source_id": "e1",
            "source_sha256": sha}


def _claim(cid, subject="evidence:e1", predicate="p.v", obj=True,
           polarity="AFFIRMED", support=None):
    return {"claim_id": cid, "subject": subject, "predicate": predicate,
            "object": obj, "polarity": polarity,
            "support": [_support()] if support is None else support}


def _claim_set(claims):
    return {"odin_claim_set_version": "0.1.0", "case_id": "case_001",
            "claims": claims}


def gate_imports():
    import odin_reasoner  # noqa: F401
    from odin_reasoner import (canonical, errors, validation, claims,  # noqa: F401,E501
                               contradictions, proof_trace, checksums, reasoner,
                               verifier, aletheia_import)
    _ok(versions.ODIN_REASONER_VERSION == "0.1.0", "unexpected version")


def gate_canonical_json():
    a = canonical_json({"b": 1, "a": 2})
    _ok(a == canonical_json({"a": 2, "b": 1}), "canonical_json not deterministic")
    _ok(a.endswith("\n"), "canonical_json must end with newline")
    try:
        canonical_json({"x": float("nan")})
        _ok(False, "canonical_json must reject NaN")
    except OdinError:
        pass


def gate_valid_claim_validation():
    validate_claim_set(_claim_set([_claim("claim_001")]))
    refused = False
    try:
        validate_claim_set(_claim_set([_claim("claim_001", support=[])]))
    except ValidationError:
        refused = True
    _ok(refused, "empty support not refused")
    # float object refused
    refused = False
    try:
        validate_claim_set(_claim_set([_claim("claim_001", obj=1.5)]))
    except ValidationError:
        refused = True
    _ok(refused, "float object not refused")


def gate_consistent_reasoning():
    report, _, contradictions = build_reasoning(_claim_set([_claim("claim_001")]))
    _ok(report["reasoning_status"] == versions.REASONING_CONSISTENT,
        "consistent set not CONSISTENT")
    _ok(contradictions == [], "spurious contradiction")


def gate_contradiction_detection():
    cs = _claim_set([
        _claim("c1", obj=True),
        _claim("c2", obj=False, support=[_support("support_002", "b" * 64)]),
    ])
    report, _, contradictions = build_reasoning(cs)
    _ok(report["reasoning_status"] == versions.REASONING_CONTRADICTION_DETECTED,
        "contradiction not detected")
    _ok(len(contradictions) == 1, "wrong contradiction count")
    _ok(contradictions[0]["rule"] == versions.RULE_DIFFERENT_OBJECT,
        "wrong contradiction rule")
    # bool vs int distinguished
    c2 = find_contradictions([
        {"claim_id": "c1", "subject": "s", "predicate": "p", "object": True,
         "polarity": "AFFIRMED"},
        {"claim_id": "c2", "subject": "s", "predicate": "p", "object": 1,
         "polarity": "AFFIRMED"}])
    _ok(len(c2) == 1, "bool/int not distinguished")


def gate_proof_trace():
    _, trace, _ = build_reasoning(_claim_set([_claim("claim_001")]))
    _ok(trace["steps"][0]["step_type"] == versions.STEP_CLAIM_ACCEPTED,
        "first step not CLAIM_ACCEPTED")
    _ok(trace["steps"][0]["reason"] == versions.REASON_SCHEMA_VALID,
        "wrong accept reason")


def gate_verify_output():
    out = os.path.join(tempfile.mkdtemp(), "odin")
    reason_to_dir(_claim_set([_claim("claim_001")]), out)
    r = verify_run(out)
    _ok(r.reasoning_status == versions.REASONING_CONSISTENT,
        "verify of fresh output failed")


def gate_no_bare_asserts():
    pkg = os.path.join(HERE, "odin_reasoner")
    offenders = []
    for dirpath, _, names in os.walk(pkg):
        for n in names:
            if n.endswith(".py"):
                p = os.path.join(dirpath, n)
                with open(p, encoding="utf-8") as fh:
                    tree = ast.parse(fh.read(), filename=p)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assert):
                        offenders.append(f"{n}:{node.lineno}")
    _ok(offenders == [], f"bare asserts in odin_reasoner/: {offenders}")


GATES = [
    ("imports", gate_imports),
    ("canonical_json", gate_canonical_json),
    ("valid_claim_validation", gate_valid_claim_validation),
    ("consistent_reasoning", gate_consistent_reasoning),
    ("contradiction_detection", gate_contradiction_detection),
    ("proof_trace", gate_proof_trace),
    ("verify_output", gate_verify_output),
    ("no_bare_asserts", gate_no_bare_asserts),
]


def main(argv=None):
    import argparse
    argparse.ArgumentParser(
        prog="selfcheck",
        description="ODIN Claim Reasoner v0.1 in-process gates.").parse_args(argv)
    print("=" * 60)
    print("  ODIN Claim Reasoner v0.1 — selfcheck (in-process gates)")
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
    print("  ALL PASS — ODIN Claim Reasoner v0.1 selfcheck satisfied.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
