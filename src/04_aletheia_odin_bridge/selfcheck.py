#!/usr/bin/env python3
# selfcheck.py
# Aletheia -> ODIN Bridge v0.1 self-check: in-process invariant gates only.
# Never launches the unit suite or any subprocess.

import ast
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from aletheia_odin_bridge.canonical import canonical_json  # noqa: E402
from aletheia_odin_bridge.errors import (  # noqa: E402
    require, BridgeError, ManifestError, AletheiaVerifyError, OdinValidateError,
    VerifyError)
from aletheia_odin_bridge.aletheia_reader import (  # noqa: E402
    validate_manifest, require_verified_present)
from aletheia_odin_bridge.claim_builder import (  # noqa: E402
    build_claims, _assert_allowed_predicate)
from aletheia_odin_bridge.verifier import verify_run  # noqa: E402
from aletheia_odin_bridge import versions  # noqa: E402


def _ok(cond, msg):
    require(cond, msg, BridgeError)


_SHA = "fe482b5e524c67728f4f2b4f430cd10d9a25659641f995ae537b282ccd181e0b"


def _manifest(evidence_status="VERIFIED_PRESENT"):
    return {
        "aletheia_evidence_bundle_version": "0.1.0", "case_id": "case_001",
        "evidence_id": "evidence_001", "source_file_name": "input.txt",
        "source_file_size_bytes": 15, "source_file_sha256": _SHA,
        "bundled_file_path": "evidence/evidence_001.bin",
        "bundled_file_sha256": _SHA, "bundle_status": "BUNDLED",
        "evidence_status": evidence_status,
        "created_at_utc": "2026-01-01T00:00:00Z", "known_limitations": ["x"]}


class _FakeAletheia:
    def verify(self, bundle_dir):
        return True


class _FakeOdin:
    def validate(self, claim_set):
        return True


def gate_imports():
    import aletheia_odin_bridge  # noqa: F401
    from aletheia_odin_bridge import (  # noqa: F401
        canonical, errors, validation, aletheia_reader, claim_builder,
        odin_validator, report, checksums, verifier)
    _ok(versions.BRIDGE_VERSION == "0.1.0", "unexpected version")


def gate_canonical_json():
    a = canonical_json({"b": 1, "a": 2})
    _ok(a == canonical_json({"a": 2, "b": 1}), "canonical_json not deterministic")
    _ok(a.endswith("\n"), "canonical_json must end with newline")
    try:
        canonical_json({"x": float("nan")})
        _ok(False, "canonical_json must reject NaN")
    except BridgeError:
        pass


def gate_manifest_validation():
    validate_manifest(_manifest())
    require_verified_present(validate_manifest(_manifest()))
    refused = False
    try:
        require_verified_present(validate_manifest(_manifest("BUNDLED")))
    except ManifestError:
        refused = True
    _ok(refused, "non-VERIFIED_PRESENT manifest not refused")


def gate_claim_generation():
    cs = build_claims(_manifest())
    _ok(len(cs["claims"]) == 2, "expected exactly two claims")
    preds = [c["predicate"] for c in cs["claims"]]
    _ok(preds == ["evidence.present", "evidence.integrity_verified"],
        f"unexpected predicates {preds}")
    for c in cs["claims"]:
        _ok(c["support"][0]["source_sha256"] == _SHA, "support sha mismatch")


def gate_no_truth_predicates():
    for bad in ("contents.true", "file.authentic", "source.trusted"):
        refused = False
        try:
            _assert_allowed_predicate(bad)
        except BridgeError:
            refused = True
        _ok(refused, f"forbidden predicate not rejected: {bad}")
    for pred in versions.ALLOWED_PREDICATES:
        for token in versions.FORBIDDEN_PREDICATE_TOKENS:
            _ok(token not in pred.lower(),
                f"allowed predicate {pred} contains forbidden {token}")


def _make_valid_output():
    import bridge
    out = os.path.join(tempfile.mkdtemp(prefix="bridge_sc_"), "out")
    bundle = tempfile.mkdtemp(prefix="ale_sc_")
    import json
    with open(os.path.join(bundle, "evidence_manifest.json"), "w",
              encoding="utf-8") as f:
        json.dump(_manifest(), f)
    bridge.convert(aletheia_root=HERE, odin_root=HERE, bundle_dir=bundle,
                   out_dir=out, aletheia_verifier=_FakeAletheia(),
                   odin_validator=_FakeOdin())
    return out


def gate_verify_valid_output():
    out = _make_valid_output()
    r = verify_run(out)
    _ok(r.bridge_status == versions.BRIDGE_CONVERTED,
        "verify of fresh bridge output failed")


def gate_detect_tamper():
    out = _make_valid_output()
    with open(os.path.join(out, versions.ODIN_CLAIMS_NAME), "ab") as f:
        f.write(b" ")
    caught = False
    try:
        verify_run(out)
    except VerifyError:
        caught = True
    _ok(caught, "verify failed to detect mutated odin_claims.json")


def gate_no_bare_asserts():
    pkg = os.path.join(HERE, "aletheia_odin_bridge")
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
    _ok(offenders == [], f"bare asserts in aletheia_odin_bridge/: {offenders}")


GATES = [
    ("imports", gate_imports),
    ("canonical_json", gate_canonical_json),
    ("manifest_validation", gate_manifest_validation),
    ("claim_generation", gate_claim_generation),
    ("no_truth_predicates", gate_no_truth_predicates),
    ("verify_valid_output", gate_verify_valid_output),
    ("detect_tamper", gate_detect_tamper),
    ("no_bare_asserts", gate_no_bare_asserts),
]


def main(argv=None):
    import argparse
    argparse.ArgumentParser(
        prog="selfcheck",
        description="Aletheia -> ODIN Bridge v0.1 in-process gates.").parse_args(
        argv)
    print("=" * 60)
    print("  Aletheia -> ODIN Bridge v0.1 — selfcheck (in-process gates)")
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
    print("  ALL PASS — Aletheia -> ODIN Bridge v0.1 selfcheck satisfied.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
