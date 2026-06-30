# odin_reasoner/verifier.py
# Verify an ODIN output folder's internal integrity. Returns success only if every
# check passes. Proves structural consistency of the reasoning output — NOT truth.

import json
import os

from odin_reasoner.canonical import canonical_bytes
from odin_reasoner.checksums import (
    parse_checksums, CLAIMS_KEY, REPORT_KEY, TRACE_KEY)
from odin_reasoner.claims import validate_claim_set
from odin_reasoner.contradictions import find_contradictions
from odin_reasoner.errors import require, VerifyError
from odin_reasoner.validation import sha256_bytes
from odin_reasoner import versions

_ALLOWED_FILES = {versions.CLAIMS_CANONICAL_NAME, versions.REASONING_REPORT_NAME,
                  versions.PROOF_TRACE_NAME, versions.CHECKSUMS_NAME}


class VerifyResult:
    __slots__ = ("run_dir", "reasoning_status", "case_id", "contradiction_count")

    def __init__(self, run_dir, reasoning_status, case_id, contradiction_count):
        self.run_dir = run_dir
        self.reasoning_status = reasoning_status
        self.case_id = case_id
        self.contradiction_count = contradiction_count


def _load_canonical(path, reason):
    with open(path, "rb") as f:
        raw = f.read()
    try:
        obj = json.loads(raw.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        raise VerifyError(reason, f"{os.path.basename(path)} is not valid JSON: {e}")
    require(canonical_bytes(obj) == raw,
            f"{os.path.basename(path)} is not in canonical form (possible tamper)",
            VerifyError, reason=reason)
    return obj, raw


def verify_run(run_dir) -> VerifyResult:
    """Verify an ODIN output folder. Raises VerifyError on any failure."""
    require(os.path.isdir(run_dir), f"run directory not found: {run_dir!r}",
            VerifyError, reason="RUN_MISSING")

    claims_path = os.path.join(run_dir, versions.CLAIMS_CANONICAL_NAME)
    report_path = os.path.join(run_dir, versions.REASONING_REPORT_NAME)
    trace_path = os.path.join(run_dir, versions.PROOF_TRACE_NAME)
    checksums_path = os.path.join(run_dir, versions.CHECKSUMS_NAME)

    # 1. Required files exist.
    for p in (claims_path, report_path, trace_path, checksums_path):
        require(os.path.isfile(p), f"missing {os.path.basename(p)}",
                VerifyError, reason="RUN_FILE_MISSING")

    # 2. Refuse unknown extra files.
    present = {n for n in os.listdir(run_dir) if not n.endswith(".tmp")}
    unknown = present - _ALLOWED_FILES
    require(not unknown, f"unknown extra files in ODIN output: {sorted(unknown)}",
            VerifyError, reason="UNKNOWN_FILE")

    # 3/4/5. Load canonical claims, report, trace.
    claim_set, claims_raw = _load_canonical(claims_path, "CLAIMS_NON_CANONICAL")
    report, report_raw = _load_canonical(report_path, "REPORT_NON_CANONICAL")
    trace, trace_raw = _load_canonical(trace_path, "TRACE_NON_CANONICAL")

    # 6-9. Strict checksums parse.
    with open(checksums_path, encoding="utf-8") as f:
        checksums = parse_checksums(f.read())

    # 10. Recompute all hashes and confirm they match the checksums file.
    require(checksums[CLAIMS_KEY] == sha256_bytes(claims_raw),
            "claims_canonical.json hash mismatch", VerifyError,
            reason="HASH_MISMATCH")
    require(checksums[REPORT_KEY] == sha256_bytes(report_raw),
            "reasoning_report.json hash mismatch", VerifyError,
            reason="HASH_MISMATCH")
    require(checksums[TRACE_KEY] == sha256_bytes(trace_raw),
            "proof_trace.json hash mismatch", VerifyError, reason="HASH_MISMATCH")

    # The claim set must itself still be schema-valid.
    try:
        validate_claim_set(claim_set)
    except Exception as e:  # noqa: BLE001
        raise VerifyError("CLAIMS_INVALID",
                          f"claims_canonical.json failed schema validation: {e}")

    # 11. Report status must match the detected contradiction count (recomputed
    #     independently from the claims — the report cannot lie about this).
    recomputed = find_contradictions(claim_set["claims"])
    require(report.get("contradiction_count") == len(recomputed),
            f"report contradiction_count {report.get('contradiction_count')!r} "
            f"!= recomputed {len(recomputed)}",
            VerifyError, reason="CONTRADICTION_COUNT_MISMATCH")
    expected_status = (versions.REASONING_CONTRADICTION_DETECTED if recomputed
                       else versions.REASONING_CONSISTENT)
    require(report.get("reasoning_status") == expected_status,
            f"report reasoning_status {report.get('reasoning_status')!r} does "
            f"not match recomputed status {expected_status!r}",
            VerifyError, reason="STATUS_MISMATCH")
    require(report.get("claim_count") == len(claim_set["claims"]),
            "report claim_count does not match claims",
            VerifyError, reason="CLAIM_COUNT_MISMATCH")

    # 12. Proof trace must reference only valid claim IDs.
    valid_ids = {c["claim_id"] for c in claim_set["claims"]}
    require(isinstance(trace.get("steps"), list),
            "proof_trace steps must be a list", VerifyError,
            reason="TRACE_INVALID")
    for step in trace["steps"]:
        ids = []
        if "claim_id" in step:
            ids.append(step["claim_id"])
        ids.extend(step.get("claim_ids", []))
        for cid in ids:
            require(cid in valid_ids,
                    f"proof_trace references unknown claim_id {cid!r}",
                    VerifyError, reason="TRACE_UNKNOWN_CLAIM_ID")

    # 13. All checks passed.
    return VerifyResult(run_dir, report["reasoning_status"],
                        claim_set["case_id"], report["contradiction_count"])
