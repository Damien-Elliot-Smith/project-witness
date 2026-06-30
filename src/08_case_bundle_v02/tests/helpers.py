# tests/helpers.py
# Synthesize the three input case folders in their REAL producer formats, in
# process (no frozen dependency for the default suite). Also a fake input-verifier.

import hashlib
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from case_bundle_v02_lib import versions  # noqa: E402

CID = "case_001"
SHA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


def _sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _canon(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def _write(path, data):
    with open(path, "wb") as f:
        f.write(data)


# ---- Sentinel case (Histor-lite v0.1.2 format: <key>  <digest>  <name>) ----
def make_sentinel_case(case_id=CID, action_status="PASS_STRICT",
                       case_status="IMPORTED", truth_line=None):
    d = tempfile.mkdtemp(prefix="sent_case_")
    summary = {
        "histor_lite_version": "0.1.2", "case_id": case_id,
        "import_status": case_status, "source_component": "sentinel_core",
        "source_component_version": "0.2.2", "sentinel_replay_ok": True,
        "sentinel_replay_verdict": action_status,
        "source_run_path": "/tmp/run.json", "source_run_sha256": SHA,
        "verified_at_utc": "2026-01-01T00:00:00Z",
        "known_limitations": ["Records a verified Sentinel replay only."],
    }
    summary_bytes = _canon(summary)
    replay = "Sentinel replay report\nverdict: " + action_status + "\n"
    if truth_line:
        replay += truth_line + "\n"
    replay_bytes = replay.encode("utf-8")
    _write(os.path.join(d, versions.SENTINEL_SUMMARY), summary_bytes)
    _write(os.path.join(d, versions.SENTINEL_REPLAY), replay_bytes)
    # Sentinel 3-token checksums (key  digest  name), plus an external source line.
    lines = [
        f"source_run_sha256  {SHA}  run.json",
        f"case_summary_sha256  {_sha_bytes(summary_bytes)}  {versions.SENTINEL_SUMMARY}",
        f"sentinel_replay_report_sha256  {_sha_bytes(replay_bytes)}  "
        f"{versions.SENTINEL_REPLAY}",
    ]
    _write(os.path.join(d, versions.SENTINEL_CHECKSUMS),
           ("\n".join(lines) + "\n").encode("utf-8"))
    return d


# ---- Aletheia case (importer format: <digest>  <name>) ----
def make_aletheia_case(case_id=CID, evidence_status="VERIFIED_PRESENT",
                       truth_line=None):
    d = tempfile.mkdtemp(prefix="ale_case_")
    manifest_copy = _canon({
        "aletheia_evidence_bundle_version": "0.1.0", "case_id": case_id,
        "evidence_id": "evidence_001", "evidence_status": evidence_status,
        "source_file_name": "evidence.txt", "source_file_size_bytes": 15,
        "source_file_sha256": SHA, "bundled_file_sha256": SHA})
    summary = _canon({
        "histor_aletheia_importer_version": "0.1.0", "case_id": case_id,
        "evidence_id": "evidence_001",
        "import_status": "IMPORTED_VERIFIED_ALETHEIA",
        "source_component": "aletheia_evidence_bundle",
        "source_evidence_status": evidence_status,
        "source_file_name": "evidence.txt", "source_file_size_bytes": 15,
        "source_file_sha256": SHA, "bundled_file_sha256": SHA,
        "source_bundle_manifest_sha256": _sha_bytes(manifest_copy),
        "known_limitations": ["It does not prove the evidence contents are true."]})
    replay = ("Aletheia Evidence Bundle Import Report\ntruth_claim: none\n"
              "This import verifies Aletheia evidence integrity metadata only. "
              "It does not prove the evidence contents are true.\n")
    if truth_line:
        replay += truth_line + "\n"
    replay_bytes = replay.encode("utf-8")
    _write(os.path.join(d, versions.ALETHEIA_SUMMARY), summary)
    _write(os.path.join(d, versions.ALETHEIA_MANIFEST_COPY), manifest_copy)
    _write(os.path.join(d, versions.ALETHEIA_REPLAY), replay_bytes)
    lines = [
        f"{_sha_bytes(summary)}  {versions.ALETHEIA_SUMMARY}",
        f"{_sha_bytes(manifest_copy)}  {versions.ALETHEIA_MANIFEST_COPY}",
        f"{_sha_bytes(replay_bytes)}  {versions.ALETHEIA_REPLAY}",
    ]
    _write(os.path.join(d, versions.ALETHEIA_CHECKSUMS),
           ("\n".join(lines) + "\n").encode("utf-8"))
    return d


# ---- ODIN case (importer format: <digest>  <name>) ----
def make_odin_case(case_id=CID, reasoning_status="CONSISTENT", claim_count=1,
                   contradiction_count=0, truth_line=None):
    d = tempfile.mkdtemp(prefix="odin_case_")
    report_copy = _canon({
        "odin_reasoner_version": "0.1.0", "case_id": case_id,
        "reasoning_status": reasoning_status, "claim_count": claim_count,
        "contradiction_count": contradiction_count, "unsupported_claim_count": 0,
        "claims": [], "contradictions": [], "known_limitations": ["x"]})
    trace_copy = _canon({
        "proof_trace_version": "0.1.0", "case_id": case_id,
        "steps": [{"step_id": f"step_{i+1:03d}"} for i in range(claim_count)]})
    claims_copy = _canon({
        "odin_claim_set_version": "0.1.0", "case_id": case_id,
        "claims": [{"claim_id": f"claim_{i+1:03d}"} for i in range(claim_count)]})
    summary = _canon({
        "histor_odin_importer_version": "0.1.0", "case_id": case_id,
        "import_status": "IMPORTED_VERIFIED_ODIN",
        "source_component": "odin_claim_reasoner",
        "source_reasoning_status": reasoning_status, "claim_count": claim_count,
        "contradiction_count": contradiction_count, "proof_step_count": claim_count,
        "source_claims_sha256": _sha_bytes(claims_copy),
        "source_reasoning_report_sha256": _sha_bytes(report_copy),
        "source_proof_trace_sha256": _sha_bytes(trace_copy),
        "known_limitations": ["It does not prove claims are true."]})
    replay = ("ODIN Reasoning Import Report\ntruth_claim: none\n"
              "This import records ODIN structural reasoning metadata only. "
              "It does not prove that any claim is true.\n")
    if truth_line:
        replay += truth_line + "\n"
    replay_bytes = replay.encode("utf-8")
    _write(os.path.join(d, versions.ODIN_SUMMARY), summary)
    _write(os.path.join(d, versions.ODIN_REPORT_COPY), report_copy)
    _write(os.path.join(d, versions.ODIN_TRACE_COPY), trace_copy)
    _write(os.path.join(d, versions.ODIN_CLAIMS_COPY), claims_copy)
    _write(os.path.join(d, versions.ODIN_REPLAY), replay_bytes)
    lines = [
        f"{_sha_bytes(summary)}  {versions.ODIN_SUMMARY}",
        f"{_sha_bytes(report_copy)}  {versions.ODIN_REPORT_COPY}",
        f"{_sha_bytes(trace_copy)}  {versions.ODIN_TRACE_COPY}",
        f"{_sha_bytes(claims_copy)}  {versions.ODIN_CLAIMS_COPY}",
        f"{_sha_bytes(replay_bytes)}  {versions.ODIN_REPLAY}",
    ]
    _write(os.path.join(d, versions.ODIN_CHECKSUMS),
           ("\n".join(lines) + "\n").encode("utf-8"))
    return d


def make_three_cases(case_id=CID, **kw):
    return (make_sentinel_case(case_id=case_id),
            make_aletheia_case(case_id=case_id),
            make_odin_case(case_id=case_id, **kw))


def out_dir():
    return os.path.join(tempfile.mkdtemp(prefix="pw_bundle_"), "bundle")


def build_bundle(out=None, *, sentinel=None, aletheia=None, odin=None,
                 input_verifier=None):
    import case_bundle_v02_lib.builder as builder
    if out is None:
        out = out_dir()
    if sentinel is None:
        sentinel = make_sentinel_case()
    if aletheia is None:
        aletheia = make_aletheia_case()
    if odin is None:
        odin = make_odin_case()
    return builder.build_bundle(
        sentinel_case=sentinel, aletheia_case=aletheia, odin_case=odin,
        out_dir=out, input_verifier=input_verifier)


def good_bundle(out=None, **kw):
    return build_bundle(out, **kw).out_dir


class FailingInputVerifier:
    """Fake input-verifier that raises InputCaseError for one named case."""

    def __init__(self, fail):
        self.fail = fail

    def _facts_sentinel(self):
        return {"case_id": CID, "case_status": "IMPORTED",
                "action_status": "PASS_STRICT",
                "source_component": "histor_lite"}

    def verify_sentinel(self, case_dir):
        from case_bundle_v02_lib.errors import InputCaseError
        if self.fail == "sentinel":
            raise InputCaseError(versions.FAILED_SENTINEL_CASE_VERIFY,
                                 "INTERNAL_CHECKSUM_MISMATCH", "fake sentinel fail")
        return self._facts_sentinel()

    def verify_aletheia(self, case_dir):
        from case_bundle_v02_lib.errors import InputCaseError
        if self.fail == "aletheia":
            raise InputCaseError(versions.FAILED_ALETHEIA_CASE_VERIFY,
                                 "INTERNAL_CHECKSUM_MISMATCH", "fake aletheia fail")
        return {"case_id": CID, "import_status": "IMPORTED_VERIFIED_ALETHEIA",
                "source_evidence_status": "VERIFIED_PRESENT",
                "source_component": "histor_lite_aletheia_importer"}

    def verify_odin(self, case_dir):
        from case_bundle_v02_lib.errors import InputCaseError
        if self.fail == "odin":
            raise InputCaseError(versions.FAILED_ODIN_CASE_VERIFY,
                                 "INTERNAL_CHECKSUM_MISMATCH", "fake odin fail")
        return {"case_id": CID, "import_status": "IMPORTED_VERIFIED_ODIN",
                "source_reasoning_status": "CONSISTENT", "claim_count": 1,
                "contradiction_count": 0,
                "source_component": "histor_lite_odin_importer"}
