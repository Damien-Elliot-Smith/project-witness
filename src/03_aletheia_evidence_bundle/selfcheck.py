#!/usr/bin/env python3
# selfcheck.py
# Aletheia Evidence Bundle v0.1 self-check: in-process invariant gates only.
# Never launches the unit suite or any subprocess.

import ast
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from aletheia_evidence.canonical import canonical_json  # noqa: E402
from aletheia_evidence.errors import (  # noqa: E402
    require, AletheiaError, ValidationError, VerifyError)
from aletheia_evidence.validation import validate_id, is_safe_id  # noqa: E402
from aletheia_evidence.hashing import sha256_file, sha256_bytes  # noqa: E402
from aletheia_evidence.builder import build_bundle  # noqa: E402
from aletheia_evidence.verifier import verify_bundle  # noqa: E402
from aletheia_evidence import versions  # noqa: E402


def _ok(cond, msg):
    require(cond, msg, AletheiaError)


def gate_imports():
    import aletheia_evidence  # noqa: F401
    from aletheia_evidence import (canonical, errors, validation, hashing,  # noqa: F401,E501
                                   manifest, checksums, builder, verifier)
    _ok(versions.ALETHEIA_EVIDENCE_BUNDLE_VERSION == "0.1.0",
        "unexpected version")


def gate_canonical_json():
    a = canonical_json({"b": 1, "a": 2})
    _ok(a == canonical_json({"a": 2, "b": 1}), "canonical_json not deterministic")
    _ok(a.endswith("\n"), "canonical_json must end with newline")
    try:
        canonical_json({"x": float("nan")})
        _ok(False, "canonical_json must reject NaN")
    except AletheiaError:
        pass


def gate_safe_id_validation():
    _ok(is_safe_id("case_001"), "safe id rejected")
    for bad in ("../evil", "a/b", "..", ".", "-rf", "x\x00y", ".hidden", ""):
        _ok(not is_safe_id(bad), f"unsafe id accepted: {bad!r}")
    refused = False
    try:
        validate_id("../evil", label="case_id")
    except ValidationError:
        refused = True
    _ok(refused, "validate_id did not refuse traversal")


def gate_hash_file():
    d = tempfile.mkdtemp()
    p = os.path.join(d, "f.bin")
    with open(p, "wb") as f:
        f.write(b"abc")
    _ok(sha256_file(p) == sha256_bytes(b"abc"),
        "sha256_file != sha256_bytes for same content")


def _tmp_source(content=b"selfcheck evidence\n"):
    d = tempfile.mkdtemp()
    p = os.path.join(d, "src.txt")
    with open(p, "wb") as f:
        f.write(content)
    return p


def gate_build_valid_bundle():
    out = os.path.join(tempfile.mkdtemp(), "bundle")
    r = build_bundle(source_file=_tmp_source(), case_id="case_001",
                     evidence_id="evidence_001", out_dir=out)
    _ok(r.evidence_status == versions.EVIDENCE_VERIFIED_PRESENT,
        "build did not produce VERIFIED_PRESENT")
    _ok(os.path.isfile(os.path.join(out, "evidence", "evidence_001.bin")),
        "bundled evidence file missing")


def gate_verify_valid_bundle():
    out = os.path.join(tempfile.mkdtemp(), "bundle")
    build_bundle(source_file=_tmp_source(), case_id="c", evidence_id="e",
                 out_dir=out)
    r = verify_bundle(out)
    _ok(r.evidence_status == versions.EVIDENCE_VERIFIED_PRESENT,
        "verify of a fresh bundle did not pass")


def gate_detect_tamper():
    out = os.path.join(tempfile.mkdtemp(), "bundle")
    build_bundle(source_file=_tmp_source(), case_id="c", evidence_id="e",
                 out_dir=out)
    with open(os.path.join(out, "evidence", "evidence_001.bin"), "wb") as f:
        f.write(b"TAMPERED")
    tampered_caught = False
    try:
        verify_bundle(out)
    except VerifyError:
        tampered_caught = True
    _ok(tampered_caught, "verify failed to detect a mutated evidence file")


def gate_no_bare_asserts():
    pkg = os.path.join(HERE, "aletheia_evidence")
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
    _ok(offenders == [], f"bare asserts in aletheia_evidence/: {offenders}")


GATES = [
    ("imports", gate_imports),
    ("canonical_json", gate_canonical_json),
    ("safe_id_validation", gate_safe_id_validation),
    ("hash_file", gate_hash_file),
    ("build_valid_bundle", gate_build_valid_bundle),
    ("verify_valid_bundle", gate_verify_valid_bundle),
    ("detect_tamper", gate_detect_tamper),
    ("no_bare_asserts", gate_no_bare_asserts),
]


def main(argv=None):
    import argparse
    argparse.ArgumentParser(
        prog="selfcheck",
        description="Aletheia Evidence Bundle v0.1 in-process gates.").parse_args(
        argv)
    print("=" * 60)
    print("  Aletheia Evidence Bundle v0.1 — selfcheck (in-process gates)")
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
    print("  ALL PASS — Aletheia Evidence Bundle v0.1 selfcheck satisfied.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
