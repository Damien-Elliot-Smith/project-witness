# aletheia_evidence/evidence_type.py
# Move 63 — Additional Evidence Types.
#
# A narrow, deterministic classification/report layer for LOCAL evidence files.
# It inspects one local file and emits an evidence_type_report.json describing
# its structural type (LOCAL_TEXT_UTF8, LOCAL_JSON, or LOCAL_BINARY_FILE) and the
# exact-byte SHA-256. It reuses the existing Aletheia source/ID validation and
# size limit. It NEVER interprets meaning and NEVER claims the contents are true.
#
# This layer is additive: it does not touch the Aletheia v0.1 bundle manifest,
# builder, or verifier, so existing bundle verification is unaffected.

import datetime
import json
import os

from aletheia_evidence import versions, validation
from aletheia_evidence.canonical import canonical_bytes
from aletheia_evidence.errors import ValidationError
from aletheia_evidence.hashing import sha256_bytes

REPORT_SCHEMA_VERSION = "0.1.0"
REPORT_NAME = "evidence_type_report.json"

# ── Evidence types ───────────────────────────────────────────────────────────
LOCAL_TEXT_UTF8 = "LOCAL_TEXT_UTF8"
LOCAL_JSON = "LOCAL_JSON"
LOCAL_BINARY_FILE = "LOCAL_BINARY_FILE"
AUTO = "AUTO"
REQUESTABLE_TYPES = frozenset({LOCAL_TEXT_UTF8, LOCAL_JSON, LOCAL_BINARY_FILE, AUTO})

# ── classification_status vocabulary ─────────────────────────────────────────
CLASSIFIED = "CLASSIFIED"
REJECTED_UNSAFE_PATH = "REJECTED_UNSAFE_PATH"
REJECTED_MISSING_FILE = "REJECTED_MISSING_FILE"
REJECTED_DIRECTORY = "REJECTED_DIRECTORY"
REJECTED_SYMLINK = "REJECTED_SYMLINK"
REJECTED_TOO_LARGE = "REJECTED_TOO_LARGE"
REJECTED_INVALID_UTF8 = "REJECTED_INVALID_UTF8"
REJECTED_INVALID_JSON = "REJECTED_INVALID_JSON"
REJECTED_SCHEMA_INVALID = "REJECTED_SCHEMA_INVALID"

ALL_STATUSES = frozenset({
    CLASSIFIED, REJECTED_UNSAFE_PATH, REJECTED_MISSING_FILE, REJECTED_DIRECTORY,
    REJECTED_SYMLINK, REJECTED_TOO_LARGE, REJECTED_INVALID_UTF8,
    REJECTED_INVALID_JSON, REJECTED_SCHEMA_INVALID,
})

# Map the existing validate_source_file reasons onto classification statuses so
# source-file safety is byte-for-byte the same semantics as bundle-file.
_SOURCE_REASON_TO_STATUS = {
    "EMPTY_PATH": REJECTED_UNSAFE_PATH,
    "MISSING_FILE": REJECTED_MISSING_FILE,
    "SYMLINK_SOURCE": REJECTED_SYMLINK,
    "DIRECTORY_SOURCE": REJECTED_DIRECTORY,
    "FILE_TOO_LARGE": REJECTED_TOO_LARGE,
}

# Honest, negation-only limitations phrased with noun forms so no affirmative
# truth/authenticity claim substring appears anywhere in a generated report.
KNOWN_LIMITATIONS = [
    "This report proves local file classification and exact-byte SHA-256 preservation only.",
    "It makes no claim about the accuracy, authenticity, meaning, safety, or truthfulness of the file contents.",
    "Classification is structural: LOCAL_JSON means the bytes parse as JSON, and says nothing about the correctness of the data.",
    "It does not sign, authenticate origin, timestamp-authenticate, or externally anchor the file.",
    "It performs no web, sensor, OCR, screenshot, camera, network capture, cloud, or LLM interpretation.",
    "It is not a production evidence-custody system.",
]


class ClassifyResult:
    """Outcome of a classify_file call.

    status       - one of ALL_STATUSES.
    report       - the report dict (also written to disk) or None when the
                   request was refused before a report could be produced.
    report_path  - path the report was written to, or None.
    """
    __slots__ = ("status", "report", "report_path")

    def __init__(self, status, report=None, report_path=None):
        self.status = status
        self.report = report
        self.report_path = report_path

    @property
    def ok(self):
        return self.status == CLASSIFIED


def _now_utc_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_exact_bytes(path):
    """Read the whole file as bytes WITHOUT following a symlink at the leaf.

    Size is already bounded by validate_source_file before this is called.
    """
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        chunks = []
        while True:
            b = os.read(fd, 1024 * 1024)
            if not b:
                break
            chunks.append(b)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _looks_like_json_object_or_array(data_bytes):
    """(is_json_obj_or_array, detail). Proven by parsing bytes as UTF-8 JSON."""
    try:
        text = data_bytes.decode("utf-8", "strict")
    except UnicodeDecodeError:
        return False, "utf8_decode=fail"
    try:
        parsed = json.loads(text)
    except (ValueError, RecursionError):
        return False, "json_parse=fail"
    if isinstance(parsed, (dict, list)):
        return True, "json_top_level=" + ("object" if isinstance(parsed, dict) else "array")
    return False, "json_top_level=scalar"


def _is_utf8_text_no_nul(data_bytes):
    """(is_text, detail). Proven by strict UTF-8 decode and NUL rejection."""
    try:
        text = data_bytes.decode("utf-8", "strict")
    except UnicodeDecodeError:
        return False, "utf8_decode=fail"
    if "\x00" in text:
        return False, "no_nul_bytes=fail"
    return True, "no_nul_bytes=pass"


def _validate_out_dir(out_dir):
    """Return (ok, reason). Reject unsafe/unusable output directories.

    Mirrors the Aletheia bundle convention: the output directory must not be a
    symlink, must not be an existing non-directory, and must be empty if it
    already exists.
    """
    if not isinstance(out_dir, str) or out_dir == "":
        return False, "empty output path"
    if os.path.islink(out_dir):
        return False, "output path is a symlink"
    if os.path.lexists(out_dir):
        if not os.path.isdir(out_dir):
            return False, "output path exists and is not a directory"
        if os.listdir(out_dir):
            return False, "output directory is not empty"
    return True, ""


def _write_report(out_dir, report):
    os.makedirs(out_dir, exist_ok=True)
    report_path = os.path.join(out_dir, REPORT_NAME)
    # out_dir is validated empty/new above, so the report path cannot pre-exist
    # as a symlink; write canonical bytes deterministically.
    with open(report_path, "wb") as f:
        f.write(canonical_bytes(report))
    return report_path


def _base_report(case_id, evidence_id, source_file, size, sha256, evidence_type,
                 status, checks, now_utc):
    return {
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "case_id": case_id,
        "evidence_id": evidence_id,
        "source_file_name": os.path.basename(source_file) if isinstance(source_file, str) else None,
        "source_file_size_bytes": size,
        "source_file_sha256": sha256,
        "evidence_type": evidence_type,
        "classification_status": status,
        "checks_performed": checks,
        "created_at_utc": now_utc,
        "known_limitations": list(KNOWN_LIMITATIONS),
    }


def classify_file(*, source_file, case_id, evidence_id, evidence_type, out_dir,
                  now_utc=None):
    """Classify one local file and (when possible) write evidence_type_report.json.

    Returns a ClassifyResult. Never raises for expected rejections — the status
    carries the outcome. Truth is never inferred from contents.
    """
    now_utc = now_utc or _now_utc_iso()

    # ── Phase A: request-level validation (refuse without writing a report) ──
    if evidence_type not in REQUESTABLE_TYPES:
        return ClassifyResult(REJECTED_SCHEMA_INVALID)
    if not validation.is_safe_id(case_id) or not validation.is_safe_id(evidence_id):
        return ClassifyResult(REJECTED_SCHEMA_INVALID)
    ok, _reason = _validate_out_dir(out_dir)
    if not ok:
        return ClassifyResult(REJECTED_UNSAFE_PATH)

    # ── Phase B: source-file safety (reuses bundle-file semantics) ───────────
    try:
        size = validation.validate_source_file(source_file)
    except ValidationError as e:
        status = _SOURCE_REASON_TO_STATUS.get(e.reason, REJECTED_UNSAFE_PATH)
        checks = [f"source_validation={e.reason}"]
        report = _base_report(case_id, evidence_id, source_file, None, None,
                              None, status, checks, now_utc)
        path = _write_report(out_dir, report)
        return ClassifyResult(status, report, path)

    # ── Phase C: hash the EXACT bytes (no symlink follow at the leaf) ────────
    data = _read_exact_bytes(source_file)
    sha256 = sha256_bytes(data)
    checks = ["source_is_regular_file=pass", "source_not_symlink=pass",
              "within_size_limit=pass", "sha256_computed=pass"]

    # ── Phase D: classify ────────────────────────────────────────────────────
    if evidence_type == LOCAL_BINARY_FILE:
        checks.append("opaque_bytes=pass")
        report = _base_report(case_id, evidence_id, source_file, size, sha256,
                              LOCAL_BINARY_FILE, CLASSIFIED, checks, now_utc)
        return ClassifyResult(CLASSIFIED, report, _write_report(out_dir, report))

    if evidence_type == LOCAL_JSON:
        is_json, detail = _looks_like_json_object_or_array(data)
        checks.append("json_check=" + detail)
        if not is_json:
            report = _base_report(case_id, evidence_id, source_file, size, sha256,
                                  None, REJECTED_INVALID_JSON, checks, now_utc)
            return ClassifyResult(REJECTED_INVALID_JSON, report, _write_report(out_dir, report))
        report = _base_report(case_id, evidence_id, source_file, size, sha256,
                              LOCAL_JSON, CLASSIFIED, checks, now_utc)
        return ClassifyResult(CLASSIFIED, report, _write_report(out_dir, report))

    if evidence_type == LOCAL_TEXT_UTF8:
        is_text, detail = _is_utf8_text_no_nul(data)
        checks.append("text_check=" + detail)
        if not is_text:
            report = _base_report(case_id, evidence_id, source_file, size, sha256,
                                  None, REJECTED_INVALID_UTF8, checks, now_utc)
            return ClassifyResult(REJECTED_INVALID_UTF8, report, _write_report(out_dir, report))
        report = _base_report(case_id, evidence_id, source_file, size, sha256,
                              LOCAL_TEXT_UTF8, CLASSIFIED, checks, now_utc)
        return ClassifyResult(CLASSIFIED, report, _write_report(out_dir, report))

    # AUTO: JSON before text before binary. Never a truth claim — structure only.
    is_json, jdetail = _looks_like_json_object_or_array(data)
    checks.append("auto_json_check=" + jdetail)
    if is_json:
        resolved = LOCAL_JSON
    else:
        is_text, tdetail = _is_utf8_text_no_nul(data)
        checks.append("auto_text_check=" + tdetail)
        resolved = LOCAL_TEXT_UTF8 if is_text else LOCAL_BINARY_FILE
    report = _base_report(case_id, evidence_id, source_file, size, sha256,
                          resolved, CLASSIFIED, checks, now_utc)
    return ClassifyResult(CLASSIFIED, report, _write_report(out_dir, report))
