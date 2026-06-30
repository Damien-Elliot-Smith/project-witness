# tests/helpers.py
# In-process fake component runner: it does NOT spawn subprocesses. Instead it
# writes realistic-shaped component outputs into the demo folder, so the demo
# orchestration, report/steps/checksums writing, and verify can be exercised
# without the real frozen components. A `fail_at` operation name makes that step
# raise StepError, to test short-circuiting.

import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from evidence_reasoning_demo.errors import StepError  # noqa: E402
from evidence_reasoning_demo import versions  # noqa: E402

SHA = "fe482b5e524c67728f4f2b4f430cd10d9a25659641f995ae537b282ccd181e0b"

_OP_TO_STATUS = {
    "aletheia_bundle": versions.FAILED_ALETHEIA_BUNDLE,
    "aletheia_verify": versions.FAILED_ALETHEIA_VERIFY,
    "bridge_convert": versions.FAILED_BRIDGE_CONVERT,
    "bridge_verify": versions.FAILED_BRIDGE_VERIFY,
    "odin_reason": versions.FAILED_ODIN_REASON,
    "odin_verify": versions.FAILED_ODIN_VERIFY,
}


def _dump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # Write canonical so verify's canonical-form check passes for the demo files;
    # component files are only hashed (not canonical-checked) but we keep them tidy.
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, sort_keys=True,
                  separators=(",", ":"))
        f.write("\n")


class FakeComponentRunner:
    """Writes fake component outputs; optionally fails at a named operation."""

    def __init__(self, *, case_id="case_001", evidence_id="evidence_001",
                 fail_at=None, sha=SHA, evidence_status="VERIFIED_PRESENT",
                 bridge_status="CONVERTED", reasoning_status="CONSISTENT",
                 generated_claims=None):
        self.case_id = case_id
        self.evidence_id = evidence_id
        self.fail_at = fail_at
        self.sha = sha
        self.evidence_status = evidence_status
        self.bridge_status = bridge_status
        self.reasoning_status = reasoning_status
        self.generated_claims = (generated_claims if generated_claims is not None
                                 else ["evidence.present",
                                       "evidence.integrity_verified"])
        self.calls = []

    def _maybe_fail(self, op):
        self.calls.append(op)
        if self.fail_at == op:
            raise StepError(_OP_TO_STATUS[op], f"fake failure at {op}")

    def aletheia_bundle(self, evidence_file, case_id, evidence_id, out_dir):
        self._maybe_fail("aletheia_bundle")
        _dump(os.path.join(out_dir, "evidence_manifest.json"), {
            "aletheia_evidence_bundle_version": "0.1.0", "case_id": case_id,
            "evidence_id": evidence_id, "source_file_name": "input.txt",
            "source_file_size_bytes": 15, "source_file_sha256": self.sha,
            "bundled_file_path": "evidence/evidence_001.bin",
            "bundled_file_sha256": self.sha, "bundle_status": "BUNDLED",
            "evidence_status": self.evidence_status,
            "created_at_utc": "2026-01-01T00:00:00Z", "known_limitations": ["x"]})
        return True

    def aletheia_verify(self, bundle_dir):
        self._maybe_fail("aletheia_verify")
        return True

    def bridge_convert(self, aletheia_root, odin_root, bundle_dir, out_dir):
        self._maybe_fail("bridge_convert")
        _dump(os.path.join(out_dir, "bridge_report.json"), {
            "bridge_version": "0.1.0", "case_id": self.case_id,
            "evidence_id": self.evidence_id, "bridge_status": self.bridge_status,
            "aletheia_evidence_status": self.evidence_status,
            "odin_claim_count": len(self.generated_claims),
            "odin_validation_status": "VALID",
            "generated_claims": list(self.generated_claims),
            "known_limitations": ["x"]})
        claims = {
            "odin_claim_set_version": "0.1.0", "case_id": self.case_id,
            "claims": [
                {"claim_id": f"claim_{i+1:03d}",
                 "subject": f"evidence:{self.evidence_id}", "predicate": pred,
                 "object": True, "polarity": "AFFIRMED",
                 "support": [{"support_id": f"support_{i+1:03d}",
                              "source_component": "aletheia_evidence_bundle",
                              "source_id": self.evidence_id,
                              "source_sha256": self.sha}]}
                for i, pred in enumerate(self.generated_claims)]}
        _dump(os.path.join(out_dir, "odin_claims.json"), claims)
        return True

    def bridge_verify(self, run_dir):
        self._maybe_fail("bridge_verify")
        return True

    def odin_reason(self, claims_path, out_dir):
        self._maybe_fail("odin_reason")
        _dump(os.path.join(out_dir, "reasoning_report.json"), {
            "odin_reasoner_version": "0.1.0", "case_id": self.case_id,
            "reasoning_status": self.reasoning_status,
            "claim_count": len(self.generated_claims), "contradiction_count": 0,
            "unsupported_claim_count": 0, "claims": [], "contradictions": [],
            "known_limitations": ["x"]})
        return True

    def odin_verify(self, run_dir):
        self._maybe_fail("odin_verify")
        return True


def make_evidence_file(content=b"hello evidence\n"):
    d = tempfile.mkdtemp(prefix="erd_src_")
    p = os.path.join(d, "evidence.txt")
    with open(p, "wb") as f:
        f.write(content)
    return p


def run_with_fake(out_dir=None, *, runner=None, evidence_file=None,
                  case_id="case_001", evidence_id="evidence_001",
                  aletheia_root="A", bridge_root="B", odin_root="O"):
    import demo
    if out_dir is None:
        out_dir = os.path.join(tempfile.mkdtemp(prefix="erd_out_"), "out")
    if evidence_file is None:
        evidence_file = make_evidence_file()
    if runner is None:
        runner = FakeComponentRunner(case_id=case_id, evidence_id=evidence_id)
    return demo.run_demo(
        evidence_file=evidence_file, case_id=case_id, evidence_id=evidence_id,
        aletheia_root=aletheia_root, bridge_root=bridge_root, odin_root=odin_root,
        out_dir=out_dir, runner=runner)


def good_output(out_dir=None, **kwargs):
    return run_with_fake(out_dir, **kwargs).out_dir
