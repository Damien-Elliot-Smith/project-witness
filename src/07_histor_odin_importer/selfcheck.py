#!/usr/bin/env python3
# selfcheck.py
# Histor-lite ODIN Importer v0.1 self-check: in-process invariant gates only.
# Never launches the unit suite or any subprocess (uses an in-process fake).

import ast
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from histor_odin_importer.canonical import canonical_json  # noqa: E402
from histor_odin_importer.errors import (  # noqa: E402
    require, HistorOdinError, OdinRunError, VerifyError)
from histor_odin_importer.odin_reader import (  # noqa: E402
    validate_report, require_importable_status)
from histor_odin_importer.verifier import verify_case  # noqa: E402
from histor_odin_importer import versions  # noqa: E402


def _ok(cond, msg):
    require(cond, msg, HistorOdinError)


def _canon_bytes(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def _report(status="CONSISTENT", claim_count=1, contradiction_count=0):
    return {"odin_reasoner_version": "0.1.0", "case_id": "case_001",
            "reasoning_status": status, "claim_count": claim_count,
            "contradiction_count": contradiction_count,
            "unsupported_claim_count": 0, "claims": [], "contradictions": [],
            "known_limitations": ["x"]}


def _trace(step_count=1):
    return {"proof_trace_version": "0.1.0", "case_id": "case_001",
            "steps": [{"step_id": f"step_{i+1:03d}"} for i in range(step_count)]}


def _claims(claim_count=1):
    return {"odin_claim_set_version": "0.1.0", "case_id": "case_001",
            "claims": [{"claim_id": f"claim_{i+1:03d}"} for i in range(claim_count)]}


def _run_dir():
    d = tempfile.mkdtemp(prefix="odin_sc_")
    for name, obj in ((versions.ODIN_REPORT_NAME, _report()),
                      (versions.ODIN_TRACE_NAME, _trace()),
                      (versions.ODIN_CLAIMS_NAME, _claims())):
        with open(os.path.join(d, name), "wb") as f:
            f.write(_canon_bytes(obj))
    return d


class _FakeVerifier:
    def verify(self, run_dir):
        return True


def _import(out_dir, run_dir=None):
    import histor_odin_importer.importer as importer
    return importer.import_reasoning(
        odin_root=HERE, run_dir=run_dir or _run_dir(), out_dir=out_dir,
        odin_verifier=_FakeVerifier())


def gate_imports():
    import histor_odin_importer  # noqa: F401
    from histor_odin_importer import (  # noqa: F401
        canonical, errors, validation, odin_reader, importer, report, checksums,
        verifier)
    _ok(versions.IMPORTER_VERSION == "0.1.0", "unexpected version")


def gate_canonical_json():
    a = canonical_json({"b": 1, "a": 2})
    _ok(a == canonical_json({"a": 2, "b": 1}), "canonical_json not deterministic")
    _ok(a.endswith("\n"), "canonical_json must end with newline")
    try:
        canonical_json({"x": float("nan")})
        _ok(False, "canonical_json must reject NaN")
    except HistorOdinError:
        pass


def gate_valid_odin_run():
    require_importable_status(validate_report(_report("CONSISTENT")))
    require_importable_status(validate_report(_report("CONTRADICTION_DETECTED")))
    refused = False
    try:
        require_importable_status(validate_report(_report("INVALID_INPUT")))
    except OdinRunError:
        refused = True
    _ok(refused, "INVALID_INPUT not refused")


def gate_successful_fake_import():
    out = os.path.join(tempfile.mkdtemp(), "case")
    result = _import(out)
    _ok(result.summary["import_status"] == versions.IMPORTED_VERIFIED_ODIN,
        "fake import did not complete")
    names = set(os.listdir(out))
    _ok(names == {versions.SUMMARY_NAME, versions.REPORT_COPY_NAME,
                  versions.TRACE_COPY_NAME, versions.CLAIMS_COPY_NAME,
                  versions.REPLAY_REPORT_NAME, versions.CHECKSUMS_NAME},
        f"unexpected case files {names}")


def gate_verify_valid_case():
    out = os.path.join(tempfile.mkdtemp(), "case")
    _import(out)
    r = verify_case(out)
    _ok(r.import_status == versions.IMPORTED_VERIFIED_ODIN,
        "verify of fresh case failed")


def gate_detect_tamper():
    out = os.path.join(tempfile.mkdtemp(), "case")
    _import(out)
    with open(os.path.join(out, versions.SUMMARY_NAME), "ab") as f:
        f.write(b" ")
    caught = False
    try:
        verify_case(out)
    except VerifyError:
        caught = True
    _ok(caught, "verify failed to detect mutated summary")


def gate_no_truth_claims():
    out = os.path.join(tempfile.mkdtemp(), "case")
    _import(out)
    with open(os.path.join(out, versions.REPLAY_REPORT_NAME), encoding="utf-8") as f:
        report = f.read()
    _ok("truth_claim: none" in report, "replay report missing truth_claim: none")
    for token in versions.FORBIDDEN_TRUTH_TOKENS:
        _ok(token not in report.lower(),
            f"replay report contains forbidden token {token}")


def gate_no_bare_asserts():
    pkg = os.path.join(HERE, "histor_odin_importer")
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
    _ok(offenders == [], f"bare asserts in package: {offenders}")


GATES = [
    ("imports", gate_imports),
    ("canonical_json", gate_canonical_json),
    ("valid_odin_run", gate_valid_odin_run),
    ("successful_fake_import", gate_successful_fake_import),
    ("verify_valid_case", gate_verify_valid_case),
    ("detect_tamper", gate_detect_tamper),
    ("no_truth_claims", gate_no_truth_claims),
    ("no_bare_asserts", gate_no_bare_asserts),
]


def main(argv=None):
    import argparse
    argparse.ArgumentParser(
        prog="selfcheck",
        description="Histor-lite ODIN Importer v0.1 in-process gates."
        ).parse_args(argv)
    print("=" * 60)
    print("  Histor-lite ODIN Importer v0.1 — selfcheck (in-process gates)")
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
    print("  ALL PASS — Histor-lite ODIN Importer v0.1 selfcheck satisfied.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
