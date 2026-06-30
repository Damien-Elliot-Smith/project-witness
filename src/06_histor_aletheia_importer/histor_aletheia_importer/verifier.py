# histor_aletheia_importer/verifier.py
# Verify an imported evidence case's internal integrity. Returns success only if
# every check passes. Proves the import preserved Aletheia's integrity metadata —
# NOT truth of contents.

import json
import os

from histor_aletheia_importer.canonical import canonical_bytes
from histor_aletheia_importer.checksums import (
    parse_checksums, SUMMARY_KEY, MANIFEST_COPY_KEY, REPLAY_REPORT_KEY)
from histor_aletheia_importer.errors import require, VerifyError
from histor_aletheia_importer.validation import sha256_bytes
from histor_aletheia_importer import versions

_ALLOWED_FILES = {versions.SUMMARY_NAME, versions.MANIFEST_COPY_NAME,
                  versions.REPLAY_REPORT_NAME, versions.CHECKSUMS_NAME}


class VerifyResult:
    __slots__ = ("case_dir", "import_status", "case_id", "evidence_id",
                 "source_evidence_status")

    def __init__(self, case_dir, import_status, case_id, evidence_id,
                 source_evidence_status):
        self.case_dir = case_dir
        self.import_status = import_status
        self.case_id = case_id
        self.evidence_id = evidence_id
        self.source_evidence_status = source_evidence_status


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
    """Verify an imported evidence case. Raises VerifyError on any failure."""
    require(os.path.isdir(case_dir), f"case dir not found: {case_dir!r}",
            VerifyError, reason="CASE_MISSING")

    summary_path = os.path.join(case_dir, versions.SUMMARY_NAME)
    manifest_path = os.path.join(case_dir, versions.MANIFEST_COPY_NAME)
    replay_path = os.path.join(case_dir, versions.REPLAY_REPORT_NAME)
    checksums_path = os.path.join(case_dir, versions.CHECKSUMS_NAME)

    # 1. Required files exist.
    for p in (summary_path, manifest_path, replay_path, checksums_path):
        require(os.path.isfile(p), f"missing {os.path.basename(p)}",
                VerifyError, reason="CASE_FILE_MISSING")

    # 2. Refuse unknown extra files.
    present = {n for n in os.listdir(case_dir) if not n.endswith(".tmp")}
    unknown = present - _ALLOWED_FILES
    require(not unknown, f"unknown extra files in case: {sorted(unknown)}",
            VerifyError, reason="UNKNOWN_FILE")

    # 3-5. Load + canonical-check the two JSON files.
    summary, summary_raw = _load_canonical(summary_path, "SUMMARY_NON_CANONICAL")
    manifest, manifest_raw = _load_canonical(manifest_path,
                                             "MANIFEST_COPY_NON_CANONICAL")

    # 6. Load the replay report.
    with open(replay_path, "rb") as f:
        replay_raw = f.read()
    replay_text = replay_raw.decode("utf-8", errors="replace")

    # 7-10. Strict checksums parse.
    with open(checksums_path, encoding="utf-8") as f:
        checksums = parse_checksums(f.read())

    # 11. Recompute all hashes.
    require(checksums[SUMMARY_KEY] == sha256_bytes(summary_raw),
            "evidence_case_summary.json hash mismatch", VerifyError,
            reason="HASH_MISMATCH")
    require(checksums[MANIFEST_COPY_KEY] == sha256_bytes(manifest_raw),
            "aletheia_manifest_copy.json hash mismatch", VerifyError,
            reason="HASH_MISMATCH")
    require(checksums[REPLAY_REPORT_KEY] == sha256_bytes(replay_raw),
            "aletheia_replay_report.txt hash mismatch", VerifyError,
            reason="HASH_MISMATCH")

    # 12. case_id matches summary and copied manifest.
    require(summary.get("case_id") == manifest.get("case_id"),
            f"case_id mismatch: summary {summary.get('case_id')!r} != manifest "
            f"{manifest.get('case_id')!r}", VerifyError, reason="CASE_ID_MISMATCH")

    # 13. evidence_id matches summary and copied manifest.
    require(summary.get("evidence_id") == manifest.get("evidence_id"),
            f"evidence_id mismatch: summary {summary.get('evidence_id')!r} != "
            f"manifest {manifest.get('evidence_id')!r}", VerifyError,
            reason="EVIDENCE_ID_MISMATCH")

    # 14. source_evidence_status == VERIFIED_PRESENT (and matches manifest).
    require(summary.get("source_evidence_status")
            == versions.ALETHEIA_VERIFIED_PRESENT,
            f"source_evidence_status {summary.get('source_evidence_status')!r} != "
            f"{versions.ALETHEIA_VERIFIED_PRESENT}", VerifyError,
            reason="SOURCE_STATUS_MISMATCH")
    require(manifest.get("evidence_status") == versions.ALETHEIA_VERIFIED_PRESENT,
            "copied manifest evidence_status != VERIFIED_PRESENT", VerifyError,
            reason="SOURCE_STATUS_MISMATCH")

    # 15. import_status == IMPORTED_VERIFIED_ALETHEIA.
    require(summary.get("import_status") == versions.IMPORTED_VERIFIED_ALETHEIA,
            f"import_status {summary.get('import_status')!r} != "
            f"{versions.IMPORTED_VERIFIED_ALETHEIA}", VerifyError,
            reason="IMPORT_STATUS_MISMATCH")

    # 16. source_file_sha256 equals copied manifest source_file_sha256.
    require(summary.get("source_file_sha256") == manifest.get("source_file_sha256"),
            "source_file_sha256 mismatch between summary and manifest",
            VerifyError, reason="SOURCE_FILE_SHA_MISMATCH")

    # 17. bundled_file_sha256 equals copied manifest bundled_file_sha256.
    require(summary.get("bundled_file_sha256")
            == manifest.get("bundled_file_sha256"),
            "bundled_file_sha256 mismatch between summary and manifest",
            VerifyError, reason="BUNDLED_FILE_SHA_MISMATCH")

    # 18. No truth-like claim in summary or replay report.
    _scan_truth(json.dumps(summary, ensure_ascii=False), "summary")
    _scan_truth(replay_text, "replay report")

    # 19. All checks passed.
    return VerifyResult(case_dir, summary.get("import_status"),
                        summary.get("case_id"), summary.get("evidence_id"),
                        summary.get("source_evidence_status"))
