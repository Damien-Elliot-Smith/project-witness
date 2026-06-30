# histor_odin_importer/verifier.py
# Verify an imported ODIN reasoning case's internal integrity. Returns success only
# if every check passes. Proves the import preserved ODIN's structural reasoning
# metadata — NOT truth of any claim. Both CONSISTENT and CONTRADICTION_DETECTED are
# valid; INVALID_INPUT is refused.

import json
import os

from histor_odin_importer.canonical import canonical_bytes
from histor_odin_importer.checksums import (
    parse_checksums, SUMMARY_KEY, REPORT_COPY_KEY, TRACE_COPY_KEY,
    CLAIMS_COPY_KEY, REPLAY_REPORT_KEY)
from histor_odin_importer.errors import require, VerifyError
from histor_odin_importer.validation import sha256_bytes
from histor_odin_importer import versions

_ALLOWED_FILES = {versions.SUMMARY_NAME, versions.REPORT_COPY_NAME,
                  versions.TRACE_COPY_NAME, versions.CLAIMS_COPY_NAME,
                  versions.REPLAY_REPORT_NAME, versions.CHECKSUMS_NAME}


class VerifyResult:
    __slots__ = ("case_dir", "import_status", "case_id", "source_reasoning_status",
                 "claim_count", "contradiction_count", "proof_step_count")

    def __init__(self, case_dir, import_status, case_id, source_reasoning_status,
                 claim_count, contradiction_count, proof_step_count):
        self.case_dir = case_dir
        self.import_status = import_status
        self.case_id = case_id
        self.source_reasoning_status = source_reasoning_status
        self.claim_count = claim_count
        self.contradiction_count = contradiction_count
        self.proof_step_count = proof_step_count


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


def _scan_truth(text, where):
    low = text.lower()
    for token in versions.FORBIDDEN_TRUTH_TOKENS:
        require(token not in low,
                f"truth-like claim detected in {where}: contains {token!r}",
                VerifyError, reason="TRUTH_CLAIM")


def verify_case(case_dir) -> VerifyResult:
    """Verify an imported ODIN reasoning case. Raises VerifyError on any failure."""
    require(os.path.isdir(case_dir), f"case dir not found: {case_dir!r}",
            VerifyError, reason="CASE_MISSING")

    summary_path = os.path.join(case_dir, versions.SUMMARY_NAME)
    report_path = os.path.join(case_dir, versions.REPORT_COPY_NAME)
    trace_path = os.path.join(case_dir, versions.TRACE_COPY_NAME)
    claims_path = os.path.join(case_dir, versions.CLAIMS_COPY_NAME)
    replay_path = os.path.join(case_dir, versions.REPLAY_REPORT_NAME)
    checksums_path = os.path.join(case_dir, versions.CHECKSUMS_NAME)

    # 1. Required files exist.
    for p in (summary_path, report_path, trace_path, claims_path, replay_path,
              checksums_path):
        require(os.path.isfile(p), f"missing {os.path.basename(p)}",
                VerifyError, reason="CASE_FILE_MISSING")

    # 2. Refuse unknown extra files.
    present = {n for n in os.listdir(case_dir) if not n.endswith(".tmp")}
    unknown = present - _ALLOWED_FILES
    require(not unknown, f"unknown extra files in case: {sorted(unknown)}",
            VerifyError, reason="UNKNOWN_FILE")

    # 3-7. Load + canonical-check the four JSON files.
    summary, summary_raw = _load_canonical(summary_path, "SUMMARY_NON_CANONICAL")
    report, report_raw = _load_canonical(report_path, "REPORT_COPY_NON_CANONICAL")
    trace, trace_raw = _load_canonical(trace_path, "TRACE_COPY_NON_CANONICAL")
    claims, claims_raw = _load_canonical(claims_path, "CLAIMS_COPY_NON_CANONICAL")

    # 8. Load the replay report.
    with open(replay_path, "rb") as f:
        replay_raw = f.read()
    replay_text = replay_raw.decode("utf-8", errors="replace")

    # 9-13. Strict checksums parse (uppercase rejected inside parse_checksums).
    with open(checksums_path, encoding="utf-8") as f:
        checksums = parse_checksums(f.read())

    # 14. Recompute all hashes.
    require(checksums[SUMMARY_KEY] == sha256_bytes(summary_raw),
            "odin_case_summary.json hash mismatch", VerifyError,
            reason="HASH_MISMATCH")
    require(checksums[REPORT_COPY_KEY] == sha256_bytes(report_raw),
            "odin_reasoning_report_copy.json hash mismatch", VerifyError,
            reason="HASH_MISMATCH")
    require(checksums[TRACE_COPY_KEY] == sha256_bytes(trace_raw),
            "odin_proof_trace_copy.json hash mismatch", VerifyError,
            reason="HASH_MISMATCH")
    require(checksums[CLAIMS_COPY_KEY] == sha256_bytes(claims_raw),
            "odin_claims_copy.json hash mismatch", VerifyError,
            reason="HASH_MISMATCH")
    require(checksums[REPLAY_REPORT_KEY] == sha256_bytes(replay_raw),
            "odin_replay_report.txt hash mismatch", VerifyError,
            reason="HASH_MISMATCH")

    # 15. case_id matches across summary, report copy, trace copy, claims copy.
    cid = summary.get("case_id")
    require(report.get("case_id") == cid,
            "case_id mismatch: summary vs reasoning report copy", VerifyError,
            reason="CASE_ID_MISMATCH")
    require(trace.get("case_id") == cid,
            "case_id mismatch: summary vs proof trace copy", VerifyError,
            reason="CASE_ID_MISMATCH")
    require(claims.get("case_id") == cid,
            "case_id mismatch: summary vs claims copy", VerifyError,
            reason="CASE_ID_MISMATCH")

    # 16. source_reasoning_status matches the copied reasoning report.
    require(summary.get("source_reasoning_status") == report.get("reasoning_status"),
            f"source_reasoning_status {summary.get('source_reasoning_status')!r} != "
            f"report reasoning_status {report.get('reasoning_status')!r}",
            VerifyError, reason="SOURCE_STATUS_MISMATCH")

    # 17. claim_count matches the copied reasoning report AND copied claims (len).
    claim_count = summary.get("claim_count")
    require(report.get("claim_count") == claim_count,
            "claim_count mismatch: summary vs reasoning report copy", VerifyError,
            reason="CLAIM_COUNT_MISMATCH")
    claims_list = claims.get("claims")
    require(isinstance(claims_list, list) and len(claims_list) == claim_count,
            "claim_count mismatch: summary vs claims copy length", VerifyError,
            reason="CLAIM_COUNT_MISMATCH")

    # 18. contradiction_count matches the copied reasoning report.
    require(report.get("contradiction_count") == summary.get("contradiction_count"),
            "contradiction_count mismatch: summary vs reasoning report copy",
            VerifyError, reason="CONTRADICTION_COUNT_MISMATCH")

    # 19. proof_step_count matches the copied proof trace.
    steps = trace.get("steps")
    require(isinstance(steps, list)
            and len(steps) == summary.get("proof_step_count"),
            "proof_step_count mismatch: summary vs proof trace copy steps length",
            VerifyError, reason="PROOF_STEP_COUNT_MISMATCH")

    # 20. import_status == IMPORTED_VERIFIED_ODIN.
    require(summary.get("import_status") == versions.IMPORTED_VERIFIED_ODIN,
            f"import_status {summary.get('import_status')!r} != "
            f"{versions.IMPORTED_VERIFIED_ODIN}", VerifyError,
            reason="IMPORT_STATUS_MISMATCH")

    # 21-22. Source reasoning status is importable (CONSISTENT or
    # CONTRADICTION_DETECTED); INVALID_INPUT (and anything else) refused.
    status = summary.get("source_reasoning_status")
    require(status != versions.ODIN_INVALID_INPUT,
            "source_reasoning_status is INVALID_INPUT (refused)", VerifyError,
            reason="REASONING_STATUS_INVALID")
    require(status in versions.IMPORTABLE_REASONING_STATUSES,
            f"source_reasoning_status {status!r} is not importable", VerifyError,
            reason="REASONING_STATUS_INVALID")

    # 23. No truth-like claim in summary or replay report.
    _scan_truth(json.dumps(summary, ensure_ascii=False), "summary")
    _scan_truth(replay_text, "replay report")

    # 24. All checks passed.
    return VerifyResult(case_dir, summary.get("import_status"), cid, status,
                        claim_count, summary.get("contradiction_count"),
                        summary.get("proof_step_count"))
