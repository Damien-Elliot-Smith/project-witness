# tests/helpers.py
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from histor_odin_importer.errors import OdinVerifyError  # noqa: E402
from histor_odin_importer import versions  # noqa: E402

SHA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


def _canon_bytes(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def report_obj(case_id="case_001", reasoning_status="CONSISTENT", claim_count=1,
               contradiction_count=0, drop=None):
    r = {
        "odin_reasoner_version": "0.1.0",
        "case_id": case_id,
        "reasoning_status": reasoning_status,
        "claim_count": claim_count,
        "contradiction_count": contradiction_count,
        "unsupported_claim_count": 0,
        "claims": [],
        "contradictions": [],
        "known_limitations": ["..."],
    }
    if drop:
        for k in drop:
            r.pop(k, None)
    return r


def trace_obj(case_id="case_001", step_count=1):
    return {
        "proof_trace_version": "0.1.0",
        "case_id": case_id,
        "steps": [{"step_id": f"step_{i+1:03d}", "rule": "support_present"}
                  for i in range(step_count)],
    }


def claims_obj(case_id="case_001", claim_count=1):
    return {
        "odin_claim_set_version": "0.1.0",
        "case_id": case_id,
        "claims": [{"claim_id": f"claim_{i+1:03d}",
                    "subject": "evidence:evidence_001",
                    "predicate": "evidence.present", "object": True,
                    "polarity": "AFFIRMED",
                    "support": [{"support_id": f"support_{i+1:03d}",
                                 "source_component": "aletheia_evidence_bundle",
                                 "source_id": "evidence_001",
                                 "source_sha256": SHA}]}
                   for i in range(claim_count)],
    }


def make_run_dir(report=None, trace=None, claims=None, *, omit=None):
    """Create a temp ODIN run dir with the three files written canonically (ODIN
    output is canonical, so this matches real ODIN bytes). `omit` drops a file."""
    d = tempfile.mkdtemp(prefix="odin_run_")
    omit = omit or set()
    files = {
        versions.ODIN_REPORT_NAME: report if report is not None else report_obj(),
        versions.ODIN_TRACE_NAME: trace if trace is not None else trace_obj(),
        versions.ODIN_CLAIMS_NAME: claims if claims is not None else claims_obj(),
    }
    for name, obj in files.items():
        if name in omit:
            continue
        with open(os.path.join(d, name), "wb") as f:
            f.write(_canon_bytes(obj))
    return d


def consistent_run():
    return make_run_dir(report_obj("case_001", "CONSISTENT", 1, 0),
                        trace_obj("case_001", 1), claims_obj("case_001", 1))


def contradiction_run():
    return make_run_dir(report_obj("case_002", "CONTRADICTION_DETECTED", 2, 1),
                        trace_obj("case_002", 2), claims_obj("case_002", 2))


class FakeOdinVerifier:
    """In-process ODIN verifier double. verify() returns True, or raises
    OdinVerifyError if constructed with ok=False."""

    def __init__(self, ok=True):
        self._ok = ok
        self.calls = []

    def verify(self, run_dir):
        self.calls.append(run_dir)
        if not self._ok:
            raise OdinVerifyError("ODIN_VERIFY_FAILED", "fake ODIN verify failure")
        return True


def import_with_fake(out_dir, *, run_dir=None, odin_root=None, ok=True):
    import histor_odin_importer.importer as importer
    if odin_root is None:
        odin_root = HERE
    if run_dir is None:
        run_dir = consistent_run()
    return importer.import_reasoning(
        odin_root=odin_root, run_dir=run_dir, out_dir=out_dir,
        odin_verifier=FakeOdinVerifier(ok=ok))


def good_case(out_dir=None, **kwargs):
    if out_dir is None:
        out_dir = os.path.join(tempfile.mkdtemp(prefix="odin_case_"), "case")
    import_with_fake(out_dir, **kwargs)
    return out_dir
