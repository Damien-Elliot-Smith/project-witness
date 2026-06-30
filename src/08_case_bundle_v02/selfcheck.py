#!/usr/bin/env python3
# selfcheck.py
# Case Bundle v0.2 self-check: in-process invariant gates only. Never launches the
# unit suite or any subprocess (synthesizes case folders in process).

import ast
import hashlib
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from case_bundle_v02_lib.canonical import canonical_json  # noqa: E402
from case_bundle_v02_lib.errors import (  # noqa: E402
    require, CaseBundleError, CaseIdMismatchError, VerifyError)
from case_bundle_v02_lib.verifier import verify_bundle  # noqa: E402
from case_bundle_v02_lib import versions  # noqa: E402

_SHA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


def _ok(cond, msg):
    require(cond, msg, CaseBundleError)


def _shab(data):
    return hashlib.sha256(data).hexdigest()


def _canon(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def _sentinel_case(case_id="case_001"):
    d = tempfile.mkdtemp()
    summary = _canon({"histor_lite_version": "0.1.2", "case_id": case_id,
                      "import_status": "IMPORTED", "source_component": "sentinel_core",
                      "sentinel_replay_verdict": "PASS_STRICT",
                      "known_limitations": ["x"]})
    replay = b"Sentinel replay report\nverdict: PASS_STRICT\n"
    with open(os.path.join(d, versions.SENTINEL_SUMMARY), "wb") as f:
        f.write(summary)
    with open(os.path.join(d, versions.SENTINEL_REPLAY), "wb") as f:
        f.write(replay)
    lines = [f"source_run_sha256  {_SHA}  run.json",
             f"case_summary_sha256  {_shab(summary)}  {versions.SENTINEL_SUMMARY}",
             f"sentinel_replay_report_sha256  {_shab(replay)}  "
             f"{versions.SENTINEL_REPLAY}"]
    with open(os.path.join(d, versions.SENTINEL_CHECKSUMS), "wb") as f:
        f.write(("\n".join(lines) + "\n").encode("utf-8"))
    return d


def _aletheia_case(case_id="case_001"):
    d = tempfile.mkdtemp()
    mc = _canon({"case_id": case_id, "evidence_id": "e1",
                 "evidence_status": "VERIFIED_PRESENT", "source_file_sha256": _SHA,
                 "bundled_file_sha256": _SHA})
    summary = _canon({"histor_aletheia_importer_version": "0.1.0",
                      "case_id": case_id, "import_status": "IMPORTED_VERIFIED_ALETHEIA",
                      "source_evidence_status": "VERIFIED_PRESENT",
                      "known_limitations": ["It does not prove the evidence "
                                            "contents are true."]})
    replay = (b"Aletheia Evidence Bundle Import Report\ntruth_claim: none\n"
              b"It does not prove the evidence contents are true.\n")
    for name, data in ((versions.ALETHEIA_SUMMARY, summary),
                       (versions.ALETHEIA_MANIFEST_COPY, mc),
                       (versions.ALETHEIA_REPLAY, replay)):
        with open(os.path.join(d, name), "wb") as f:
            f.write(data)
    lines = [f"{_shab(summary)}  {versions.ALETHEIA_SUMMARY}",
             f"{_shab(mc)}  {versions.ALETHEIA_MANIFEST_COPY}",
             f"{_shab(replay)}  {versions.ALETHEIA_REPLAY}"]
    with open(os.path.join(d, versions.ALETHEIA_CHECKSUMS), "wb") as f:
        f.write(("\n".join(lines) + "\n").encode("utf-8"))
    return d


def _odin_case(case_id="case_001", status="CONSISTENT"):
    d = tempfile.mkdtemp()
    rep = _canon({"case_id": case_id, "reasoning_status": status,
                  "claim_count": 1, "contradiction_count": 0})
    tr = _canon({"case_id": case_id, "steps": [{"step_id": "step_001"}]})
    cl = _canon({"case_id": case_id, "claims": [{"claim_id": "claim_001"}]})
    summary = _canon({"histor_odin_importer_version": "0.1.0", "case_id": case_id,
                      "import_status": "IMPORTED_VERIFIED_ODIN",
                      "source_reasoning_status": status, "claim_count": 1,
                      "contradiction_count": 0, "proof_step_count": 1,
                      "known_limitations": ["It does not prove claims are true."]})
    replay = (b"ODIN Reasoning Import Report\ntruth_claim: none\n"
              b"It does not prove that any claim is true.\n")
    for name, data in ((versions.ODIN_SUMMARY, summary),
                       (versions.ODIN_REPORT_COPY, rep),
                       (versions.ODIN_TRACE_COPY, tr),
                       (versions.ODIN_CLAIMS_COPY, cl),
                       (versions.ODIN_REPLAY, replay)):
        with open(os.path.join(d, name), "wb") as f:
            f.write(data)
    lines = [f"{_shab(summary)}  {versions.ODIN_SUMMARY}",
             f"{_shab(rep)}  {versions.ODIN_REPORT_COPY}",
             f"{_shab(tr)}  {versions.ODIN_TRACE_COPY}",
             f"{_shab(cl)}  {versions.ODIN_CLAIMS_COPY}",
             f"{_shab(replay)}  {versions.ODIN_REPLAY}"]
    with open(os.path.join(d, versions.ODIN_CHECKSUMS), "wb") as f:
        f.write(("\n".join(lines) + "\n").encode("utf-8"))
    return d


def _build(out, sentinel=None, aletheia=None, odin=None):
    import case_bundle_v02_lib.builder as builder
    return builder.build_bundle(
        sentinel_case=sentinel or _sentinel_case(),
        aletheia_case=aletheia or _aletheia_case(),
        odin_case=odin or _odin_case(), out_dir=out)


def gate_imports():
    import case_bundle_v02_lib  # noqa: F401
    from case_bundle_v02_lib import (  # noqa: F401
        canonical, errors, validation, input_verifiers, builder, manifest,
        checksums, verifier)
    _ok(versions.CASE_BUNDLE_VERSION == "0.2.0", "unexpected version")


def gate_canonical_json():
    a = canonical_json({"b": 1, "a": 2})
    _ok(a == canonical_json({"a": 2, "b": 1}), "canonical_json not deterministic")
    _ok(a.endswith("\n"), "canonical_json must end with newline")
    try:
        canonical_json({"x": float("nan")})
        _ok(False, "must reject NaN")
    except CaseBundleError:
        pass


def gate_valid_fake_bundle_build():
    out = os.path.join(tempfile.mkdtemp(), "bundle")
    result = _build(out)
    _ok(result.manifest["bundle_status"] == versions.BUNDLED_VERIFIED_CASE,
        "fake build did not complete")
    _ok(set(os.listdir(out)) == {versions.MANIFEST_NAME, versions.CHECKSUMS_NAME}
        | set(versions.SUBFOLDERS), "unexpected bundle layout")


def gate_verify_valid_bundle():
    out = os.path.join(tempfile.mkdtemp(), "bundle")
    _build(out)
    r = verify_bundle(out)
    _ok(r.bundle_status == versions.BUNDLED_VERIFIED_CASE, "verify failed")


def gate_detect_tamper():
    out = os.path.join(tempfile.mkdtemp(), "bundle")
    _build(out)
    with open(os.path.join(out, versions.MANIFEST_NAME), "ab") as f:
        f.write(b" ")
    caught = False
    try:
        verify_bundle(out)
    except VerifyError:
        caught = True
    _ok(caught, "verify failed to detect mutated manifest")


def gate_case_id_mismatch_refused():
    out = os.path.join(tempfile.mkdtemp(), "bundle")
    caught = False
    try:
        _build(out, odin=_odin_case(case_id="case_OTHER"))
    except CaseIdMismatchError:
        caught = True
    _ok(caught, "case_id mismatch not refused")


def gate_contradiction_status_allowed():
    out = os.path.join(tempfile.mkdtemp(), "bundle")
    result = _build(out, odin=_odin_case(status="CONTRADICTION_DETECTED"))
    _ok(result.manifest["odin"]["source_reasoning_status"]
        == "CONTRADICTION_DETECTED", "contradiction not allowed")
    verify_bundle(out)


def gate_no_truth_claims():
    out = os.path.join(tempfile.mkdtemp(), "bundle")
    _build(out)
    # verify includes the truth scan; a fresh valid bundle must pass it.
    verify_bundle(out)
    with open(os.path.join(out, versions.MANIFEST_NAME), encoding="utf-8") as f:
        manifest = f.read().lower()
    _ok("does not prove evidence contents are true" in manifest,
        "manifest missing evidence disclaimer")


GATES = [
    ("imports", gate_imports),
    ("canonical_json", gate_canonical_json),
    ("valid_fake_bundle_build", gate_valid_fake_bundle_build),
    ("verify_valid_bundle", gate_verify_valid_bundle),
    ("detect_tamper", gate_detect_tamper),
    ("case_id_mismatch_refused", gate_case_id_mismatch_refused),
    ("contradiction_status_allowed", gate_contradiction_status_allowed),
    ("no_truth_claims", gate_no_truth_claims),
]


def main(argv=None):
    import argparse
    argparse.ArgumentParser(
        prog="selfcheck",
        description="Case Bundle v0.2 in-process gates.").parse_args(argv)
    print("=" * 60)
    print("  Case Bundle v0.2 — selfcheck (in-process gates)")
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
    print("  ALL PASS — Case Bundle v0.2 selfcheck satisfied.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
