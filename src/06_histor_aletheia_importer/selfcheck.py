#!/usr/bin/env python3
# selfcheck.py
# Histor-lite Aletheia Importer v0.1 self-check: in-process invariant gates only.
# Never launches the unit suite or any subprocess (uses an in-process fake).

import ast
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from histor_aletheia_importer.canonical import canonical_json  # noqa: E402
from histor_aletheia_importer.errors import (  # noqa: E402
    require, HistorImportError, ManifestError, AletheiaVerifyError, VerifyError)
from histor_aletheia_importer.aletheia_reader import (  # noqa: E402
    validate_manifest, require_verified_present)
from histor_aletheia_importer.verifier import verify_case  # noqa: E402
from histor_aletheia_importer import versions  # noqa: E402

_SHA = "fe482b5e524c67728f4f2b4f430cd10d9a25659641f995ae537b282ccd181e0b"


def _ok(cond, msg):
    require(cond, msg, HistorImportError)


def _manifest(evidence_status="VERIFIED_PRESENT"):
    return {
        "aletheia_evidence_bundle_version": "0.1.0", "case_id": "case_001",
        "evidence_id": "evidence_001", "source_file_name": "evidence.txt",
        "source_file_size_bytes": 15, "source_file_sha256": _SHA,
        "bundled_file_path": "evidence/evidence_001.bin",
        "bundled_file_sha256": _SHA, "bundle_status": "BUNDLED",
        "evidence_status": evidence_status,
        "created_at_utc": "2026-01-01T00:00:00Z", "known_limitations": ["x"]}


class _FakeVerifier:
    def verify(self, bundle_dir):
        return True


def _bundle_dir(manifest_dict=None):
    d = tempfile.mkdtemp(prefix="ale_sc_")
    with open(os.path.join(d, "evidence_manifest.json"), "w",
              encoding="utf-8") as f:
        json.dump(manifest_dict or _manifest(), f)
    return d


def _import(out_dir, manifest_dict=None):
    import histor_aletheia_importer.importer as importer
    return importer.import_evidence(
        aletheia_root=HERE, bundle_dir=_bundle_dir(manifest_dict),
        out_dir=out_dir, aletheia_verifier=_FakeVerifier())


def gate_imports():
    import histor_aletheia_importer  # noqa: F401
    from histor_aletheia_importer import (  # noqa: F401
        canonical, errors, validation, aletheia_reader, importer, report,
        checksums, verifier)
    _ok(versions.IMPORTER_VERSION == "0.1.0", "unexpected version")


def gate_canonical_json():
    a = canonical_json({"b": 1, "a": 2})
    _ok(a == canonical_json({"a": 2, "b": 1}), "canonical_json not deterministic")
    _ok(a.endswith("\n"), "canonical_json must end with newline")
    try:
        canonical_json({"x": float("nan")})
        _ok(False, "canonical_json must reject NaN")
    except HistorImportError:
        pass


def gate_valid_manifest():
    validate_manifest(_manifest())
    require_verified_present(validate_manifest(_manifest()))
    refused = False
    try:
        require_verified_present(validate_manifest(_manifest("BUNDLED")))
    except ManifestError:
        refused = True
    _ok(refused, "non-VERIFIED_PRESENT manifest not refused")


def gate_successful_fake_import():
    out = os.path.join(tempfile.mkdtemp(), "case")
    result = _import(out)
    _ok(result.summary["import_status"] == versions.IMPORTED_VERIFIED_ALETHEIA,
        "fake import did not complete")
    names = set(os.listdir(out))
    _ok(names == {versions.SUMMARY_NAME, versions.MANIFEST_COPY_NAME,
                  versions.REPLAY_REPORT_NAME, versions.CHECKSUMS_NAME},
        f"unexpected case files {names}")


def gate_verify_valid_case():
    out = os.path.join(tempfile.mkdtemp(), "case")
    _import(out)
    r = verify_case(out)
    _ok(r.import_status == versions.IMPORTED_VERIFIED_ALETHEIA,
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
    pkg = os.path.join(HERE, "histor_aletheia_importer")
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
    ("valid_manifest", gate_valid_manifest),
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
        description="Histor-lite Aletheia Importer v0.1 in-process gates."
        ).parse_args(argv)
    print("=" * 60)
    print("  Histor-lite Aletheia Importer v0.1 — selfcheck (in-process gates)")
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
    print("  ALL PASS — Histor-lite Aletheia Importer v0.1 selfcheck satisfied.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
