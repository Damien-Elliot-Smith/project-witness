# aletheia_odin_bridge/verifier.py
# Verify a bridge output folder's internal integrity. Returns success only if every
# check passes. Proves conversion consistency — NOT truth of contents.

import json
import os

from aletheia_odin_bridge.canonical import canonical_bytes
from aletheia_odin_bridge.checksums import (
    parse_checksums, CLAIMS_KEY, REPORT_KEY, MANIFEST_COPY_KEY)
from aletheia_odin_bridge.errors import require, VerifyError
from aletheia_odin_bridge.validation import sha256_bytes
from aletheia_odin_bridge import versions

_ALLOWED_FILES = {versions.ODIN_CLAIMS_NAME, versions.BRIDGE_REPORT_NAME,
                  versions.CHECKSUMS_NAME, versions.MANIFEST_COPY_NAME}


class VerifyResult:
    __slots__ = ("run_dir", "bridge_status", "case_id", "evidence_id",
                 "claim_count")

    def __init__(self, run_dir, bridge_status, case_id, evidence_id, claim_count):
        self.run_dir = run_dir
        self.bridge_status = bridge_status
        self.case_id = case_id
        self.evidence_id = evidence_id
        self.claim_count = claim_count


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
    """Verify a bridge output folder. Raises VerifyError on any failure."""
    require(os.path.isdir(run_dir), f"bridge run dir not found: {run_dir!r}",
            VerifyError, reason="RUN_MISSING")

    claims_path = os.path.join(run_dir, versions.ODIN_CLAIMS_NAME)
    report_path = os.path.join(run_dir, versions.BRIDGE_REPORT_NAME)
    manifest_path = os.path.join(run_dir, versions.MANIFEST_COPY_NAME)
    checksums_path = os.path.join(run_dir, versions.CHECKSUMS_NAME)

    # 1. Required files exist.
    for p in (claims_path, report_path, manifest_path, checksums_path):
        require(os.path.isfile(p), f"missing {os.path.basename(p)}",
                VerifyError, reason="RUN_FILE_MISSING")

    # 2. Refuse unknown extra files.
    present = {n for n in os.listdir(run_dir) if not n.endswith(".tmp")}
    unknown = present - _ALLOWED_FILES
    require(not unknown, f"unknown extra files in bridge output: {sorted(unknown)}",
            VerifyError, reason="UNKNOWN_FILE")

    # 3-6. Load + canonical-check the three JSON files.
    claim_set, claims_raw = _load_canonical(claims_path, "CLAIMS_NON_CANONICAL")
    report, report_raw = _load_canonical(report_path, "REPORT_NON_CANONICAL")
    manifest, manifest_raw = _load_canonical(manifest_path,
                                             "MANIFEST_COPY_NON_CANONICAL")

    # 7-10. Strict checksums parse.
    with open(checksums_path, encoding="utf-8") as f:
        checksums = parse_checksums(f.read())

    # 11. Recompute all hashes and match the checksums file.
    require(checksums[CLAIMS_KEY] == sha256_bytes(claims_raw),
            "odin_claims.json hash mismatch", VerifyError, reason="HASH_MISMATCH")
    require(checksums[REPORT_KEY] == sha256_bytes(report_raw),
            "bridge_report.json hash mismatch", VerifyError, reason="HASH_MISMATCH")
    require(checksums[MANIFEST_COPY_KEY] == sha256_bytes(manifest_raw),
            "aletheia_manifest_copy.json hash mismatch", VerifyError,
            reason="HASH_MISMATCH")

    # Basic structural expectations on the claim set.
    require(isinstance(claim_set, dict) and isinstance(claim_set.get("claims"),
            list) and claim_set["claims"],
            "odin_claims.json has no claims", VerifyError, reason="CLAIMS_INVALID")
    claims = claim_set["claims"]

    # 12. report case_id matches claims case_id.
    require(report.get("case_id") == claim_set.get("case_id"),
            f"report case_id {report.get('case_id')!r} != claims case_id "
            f"{claim_set.get('case_id')!r}", VerifyError, reason="CASE_ID_MISMATCH")

    # 13. report evidence_id matches the copied manifest.
    require(report.get("evidence_id") == manifest.get("evidence_id"),
            f"report evidence_id {report.get('evidence_id')!r} != manifest "
            f"evidence_id {manifest.get('evidence_id')!r}", VerifyError,
            reason="EVIDENCE_ID_MISMATCH")

    # 14/15. claims contain ONLY allowed predicates; no truth-like predicate.
    for c in claims:
        pred = c.get("predicate")
        require(pred in versions.ALLOWED_PREDICATES,
                f"claim predicate {pred!r} is not an allowed bridge predicate",
                VerifyError, reason="DISALLOWED_PREDICATE")
        low = (pred or "").lower()
        for token in versions.FORBIDDEN_PREDICATE_TOKENS:
            require(token not in low,
                    f"truth-like predicate detected: {pred!r} (contains "
                    f"{token!r})", VerifyError, reason="TRUTH_PREDICATE")

    # 16. support source_sha256 matches the manifest bundled_file_sha256.
    bundled_sha = manifest.get("bundled_file_sha256")
    for c in claims:
        for s in c.get("support", []):
            require(s.get("source_sha256") == bundled_sha,
                    f"support source_sha256 {s.get('source_sha256')!r} != "
                    f"manifest bundled_file_sha256 {bundled_sha!r}",
                    VerifyError, reason="SUPPORT_SHA_MISMATCH")

    # 17. report odin_claim_count equals actual claim count.
    require(report.get("odin_claim_count") == len(claims),
            f"report odin_claim_count {report.get('odin_claim_count')!r} != "
            f"actual {len(claims)}", VerifyError, reason="CLAIM_COUNT_MISMATCH")

    # 18. All checks passed.
    return VerifyResult(run_dir, report.get("bridge_status"),
                        claim_set.get("case_id"), report.get("evidence_id"),
                        len(claims))
