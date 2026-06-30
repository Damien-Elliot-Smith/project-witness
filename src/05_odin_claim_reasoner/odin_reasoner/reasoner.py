# odin_reasoner/reasoner.py
# Orchestrate: validate claim set -> detect contradictions -> build canonical
# claims, reasoning report, proof trace, and checksums. Deterministic.

import os

from odin_reasoner.canonical import canonical_bytes
from odin_reasoner.checksums import format_checksums
from odin_reasoner.claims import validate_claim_set
from odin_reasoner.contradictions import find_contradictions
from odin_reasoner.errors import require, ValidationError
from odin_reasoner.proof_trace import build_proof_trace
from odin_reasoner.validation import sha256_bytes
from odin_reasoner import versions


class ReasonResult:
    __slots__ = ("out_dir", "report", "proof_trace", "reasoning_status")

    def __init__(self, out_dir, report, proof_trace, reasoning_status):
        self.out_dir = out_dir
        self.report = report
        self.proof_trace = proof_trace
        self.reasoning_status = reasoning_status


def _write_bytes(path, data: bytes):
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def build_reasoning(claim_set):
    """Pure reasoning over a validated claim set. Returns
    (report, proof_trace, contradictions). Raises ValidationError if invalid."""
    validate_claim_set(claim_set)
    case_id = claim_set["case_id"]
    claims = claim_set["claims"]

    contradictions = find_contradictions(claims)
    contradicted_ids = set()
    for c in contradictions:
        contradicted_ids.update(c["claim_ids"])

    claim_rows = []
    for claim in claims:
        cid = claim["claim_id"]
        status = (versions.CLAIM_CONTRADICTED if cid in contradicted_ids
                  else versions.CLAIM_ACCEPTED)
        # Support presence is guaranteed by schema validation (non-empty list).
        claim_rows.append({
            "claim_id": cid,
            "claim_status": status,
            "support_status": versions.SUPPORT_SUPPORTED,
        })

    reasoning_status = (versions.REASONING_CONTRADICTION_DETECTED
                        if contradictions else versions.REASONING_CONSISTENT)

    report = {
        "odin_reasoner_version": versions.ODIN_REASONER_VERSION,
        "case_id": case_id,
        "reasoning_status": reasoning_status,
        "claim_count": len(claims),
        "contradiction_count": len(contradictions),
        "unsupported_claim_count": 0,
        "claims": claim_rows,
        "contradictions": [
            {"claim_ids": list(c["claim_ids"]), "rule": c["rule"]}
            for c in contradictions
        ],
        "known_limitations": list(versions.KNOWN_LIMITATIONS),
    }
    proof_trace = build_proof_trace(case_id=case_id, claims=claims,
                                    contradictions=contradictions)
    return report, proof_trace, contradictions


def reason_to_dir(claim_set, out_dir):
    """Validate + reason + write the four output files. Raises ValidationError on
    invalid input (no successful output written) or if out_dir is non-empty."""
    if os.path.isdir(out_dir):
        require(not os.listdir(out_dir),
                f"output directory is not empty: {out_dir!r}",
                ValidationError, reason="OUTPUT_DIR_NOT_EMPTY")

    report, proof_trace, _ = build_reasoning(claim_set)

    os.makedirs(out_dir, exist_ok=True)
    claims_bytes = canonical_bytes(claim_set)
    report_bytes = canonical_bytes(report)
    trace_bytes = canonical_bytes(proof_trace)

    _write_bytes(os.path.join(out_dir, versions.CLAIMS_CANONICAL_NAME),
                 claims_bytes)
    _write_bytes(os.path.join(out_dir, versions.REASONING_REPORT_NAME),
                 report_bytes)
    _write_bytes(os.path.join(out_dir, versions.PROOF_TRACE_NAME), trace_bytes)

    checksums = format_checksums(
        claims_sha256=sha256_bytes(claims_bytes),
        report_sha256=sha256_bytes(report_bytes),
        trace_sha256=sha256_bytes(trace_bytes))
    _write_bytes(os.path.join(out_dir, versions.CHECKSUMS_NAME), checksums)

    return ReasonResult(out_dir, report, proof_trace,
                        report["reasoning_status"])
