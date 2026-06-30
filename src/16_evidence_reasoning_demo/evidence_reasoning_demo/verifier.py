# evidence_reasoning_demo/verifier.py
# Verify a demo output folder's internal integrity. Returns success only if every
# check passes. Proves the chain executed and verifies — NOT truth of contents.

import json
import os

from evidence_reasoning_demo.canonical import canonical_bytes
from evidence_reasoning_demo.checksums import (
    parse_checksums, REPORT_KEY, STEPS_KEY, ALETHEIA_MANIFEST_KEY,
    BRIDGE_REPORT_KEY, ODIN_REPORT_KEY)
from evidence_reasoning_demo.errors import require, VerifyError
from evidence_reasoning_demo.validation import sha256_bytes, sha256_file
from evidence_reasoning_demo import versions

# Allowed top-level entries (files + subfolders).
_ALLOWED_TOP = ({versions.DEMO_REPORT_NAME, versions.DEMO_STEPS_NAME,
                 versions.CHECKSUMS_NAME} | set(versions.SUBFOLDERS))


class VerifyResult:
    __slots__ = ("run_dir", "demo_status", "case_id", "evidence_id",
                 "odin_reasoning_status")

    def __init__(self, run_dir, demo_status, case_id, evidence_id,
                 odin_reasoning_status):
        self.run_dir = run_dir
        self.demo_status = demo_status
        self.case_id = case_id
        self.evidence_id = evidence_id
        self.odin_reasoning_status = odin_reasoning_status


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


def _load_json(path, reason):
    require(os.path.isfile(path), f"missing {path}", VerifyError, reason=reason)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:  # noqa: BLE001
        raise VerifyError(reason, f"{os.path.basename(path)} not valid JSON: {e}")


def verify_run(run_dir) -> VerifyResult:
    """Verify a demo output folder. Raises VerifyError on any failure."""
    require(os.path.isdir(run_dir), f"demo run dir not found: {run_dir!r}",
            VerifyError, reason="RUN_MISSING")

    report_path = os.path.join(run_dir, versions.DEMO_REPORT_NAME)
    steps_path = os.path.join(run_dir, versions.DEMO_STEPS_NAME)
    checksums_path = os.path.join(run_dir, versions.CHECKSUMS_NAME)

    # 1. Required files exist.
    for p in (report_path, steps_path, checksums_path):
        require(os.path.isfile(p), f"missing {os.path.basename(p)}",
                VerifyError, reason="RUN_FILE_MISSING")

    # 2. Required subfolders exist.
    for sub in versions.SUBFOLDERS:
        require(os.path.isdir(os.path.join(run_dir, sub)),
                f"missing subfolder {sub}/", VerifyError, reason="SUBFOLDER_MISSING")

    # 3. Refuse unknown extra top-level files.
    present = {n for n in os.listdir(run_dir) if not n.endswith(".tmp")}
    unknown = present - _ALLOWED_TOP
    require(not unknown, f"unknown extra top-level entries: {sorted(unknown)}",
            VerifyError, reason="UNKNOWN_FILE")

    # 4-6. Load + canonical-check demo_report and demo_steps.
    report, report_raw = _load_canonical(report_path, "REPORT_NON_CANONICAL")
    steps, steps_raw = _load_canonical(steps_path, "STEPS_NON_CANONICAL")

    # Component output files referenced by hash.
    aletheia_manifest_path = os.path.join(run_dir, versions.ALETHEIA_MANIFEST_REL)
    bridge_report_path = os.path.join(run_dir, versions.BRIDGE_REPORT_REL)
    odin_report_path = os.path.join(run_dir, versions.ODIN_REASONING_REPORT_REL)
    for p, name in ((aletheia_manifest_path, versions.ALETHEIA_MANIFEST_REL),
                    (bridge_report_path, versions.BRIDGE_REPORT_REL),
                    (odin_report_path, versions.ODIN_REASONING_REPORT_REL)):
        require(os.path.isfile(p), f"missing component file {name}",
                VerifyError, reason="COMPONENT_FILE_MISSING")

    # 7-10. Strict checksums parse.
    with open(checksums_path, encoding="utf-8") as f:
        checksums = parse_checksums(f.read())

    # 11. Recompute all listed hashes.
    require(checksums[REPORT_KEY] == sha256_bytes(report_raw),
            "demo_report.json hash mismatch", VerifyError, reason="HASH_MISMATCH")
    require(checksums[STEPS_KEY] == sha256_bytes(steps_raw),
            "demo_steps.json hash mismatch", VerifyError, reason="HASH_MISMATCH")
    require(checksums[ALETHEIA_MANIFEST_KEY] == sha256_file(aletheia_manifest_path),
            "aletheia_bundle manifest hash mismatch", VerifyError,
            reason="HASH_MISMATCH")
    require(checksums[BRIDGE_REPORT_KEY] == sha256_file(bridge_report_path),
            "bridge_output report hash mismatch", VerifyError,
            reason="HASH_MISMATCH")
    require(checksums[ODIN_REPORT_KEY] == sha256_file(odin_report_path),
            "odin_output reasoning_report hash mismatch", VerifyError,
            reason="HASH_MISMATCH")

    # Load the component reports/manifests for cross-checks.
    aletheia_manifest = _load_json(aletheia_manifest_path, "COMPONENT_FILE_MISSING")
    bridge_report = _load_json(bridge_report_path, "COMPONENT_FILE_MISSING")
    odin_report = _load_json(odin_report_path, "COMPONENT_FILE_MISSING")

    # 12. case_id matches across demo report, demo steps, bridge report, ODIN report.
    case_id = report.get("case_id")
    require(steps.get("case_id") == case_id,
            "demo_steps case_id mismatch", VerifyError, reason="CASE_ID_MISMATCH")
    require(bridge_report.get("case_id") == case_id,
            "bridge_report case_id mismatch", VerifyError, reason="CASE_ID_MISMATCH")
    require(odin_report.get("case_id") == case_id,
            "odin reasoning_report case_id mismatch", VerifyError,
            reason="CASE_ID_MISMATCH")

    # 13. evidence_id matches Aletheia manifest and bridge output.
    evidence_id = report.get("evidence_id")
    require(aletheia_manifest.get("evidence_id") == evidence_id,
            "aletheia manifest evidence_id mismatch", VerifyError,
            reason="EVIDENCE_ID_MISMATCH")
    require(bridge_report.get("evidence_id") == evidence_id,
            "bridge_report evidence_id mismatch", VerifyError,
            reason="EVIDENCE_ID_MISMATCH")

    # 14/15. generated_claims contains ONLY allowed predicates; no truth-like one.
    generated = report.get("generated_claims")
    require(isinstance(generated, list) and generated,
            "generated_claims must be a non-empty list", VerifyError,
            reason="GENERATED_CLAIMS_INVALID")
    for pred in generated:
        require(pred in versions.ALLOWED_PREDICATES,
                f"generated claim {pred!r} is not an allowed predicate",
                VerifyError, reason="DISALLOWED_PREDICATE")
        low = str(pred).lower()
        for token in versions.FORBIDDEN_PREDICATE_TOKENS:
            require(token not in low,
                    f"truth-like predicate detected: {pred!r} (contains "
                    f"{token!r})", VerifyError, reason="TRUTH_PREDICATE")
    # Also scan the ODIN claims surfaced in the bridge report, if present.
    for pred in bridge_report.get("generated_claims", []):
        low = str(pred).lower()
        for token in versions.FORBIDDEN_PREDICATE_TOKENS:
            require(token not in low,
                    f"truth-like predicate in bridge report: {pred!r}",
                    VerifyError, reason="TRUTH_PREDICATE")

    # 16. odin_reasoning_status == CONSISTENT.
    require(report.get("odin_reasoning_status") == versions.ODIN_CONSISTENT,
            f"odin_reasoning_status {report.get('odin_reasoning_status')!r} != "
            f"{versions.ODIN_CONSISTENT}", VerifyError, reason="ODIN_STATUS_NOT_CONSISTENT")
    require(odin_report.get("reasoning_status") == versions.ODIN_CONSISTENT,
            "odin reasoning_report status != CONSISTENT", VerifyError,
            reason="ODIN_STATUS_NOT_CONSISTENT")

    # 17. demo_status == DEMO_COMPLETED.
    require(report.get("demo_status") == versions.DEMO_COMPLETED,
            f"demo_status {report.get('demo_status')!r} != "
            f"{versions.DEMO_COMPLETED}", VerifyError,
            reason="DEMO_STATUS_NOT_COMPLETED")

    # Consistency: aletheia_status / bridge_status echo the component outputs.
    require(report.get("aletheia_status") == aletheia_manifest.get("evidence_status"),
            "demo aletheia_status != manifest evidence_status", VerifyError,
            reason="ALETHEIA_STATUS_MISMATCH")
    require(report.get("bridge_status") == bridge_report.get("bridge_status"),
            "demo bridge_status != bridge_report bridge_status", VerifyError,
            reason="BRIDGE_STATUS_MISMATCH")

    # 18. All checks passed.
    return VerifyResult(run_dir, report.get("demo_status"), case_id, evidence_id,
                        report.get("odin_reasoning_status"))
