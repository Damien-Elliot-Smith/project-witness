"""Verification of a release-gate output folder.

verify(out_dir) returns a VerifyResult. It raises VerifyError on any structural
problem, tamper, malformed checksum, wrong step order, non-canonical JSON, or a
truth-like claim. For a structurally sound output, ok is True only when the gate
status is RELEASE_GATE_PASSED and all passed-invariants hold.
"""

import os
import re

from . import canonical, checksums, feature_checks, steps as steps_mod
from .errors import (
    VerifyError, RELEASE_GATE_PASSED, REGISTRY_VERIFIED, EXPORT_VERIFIED,
    STEP_COMPLETED, STEP_FAILED, STEP_SKIPPED, ALL_GATE_STATUSES, ALL_STEP_STATUSES,
)

OUTPUT_REPORT = "atlas_release_gate_report.json"
OUTPUT_STEPS = "atlas_release_gate_steps.json"
OUTPUT_CHECKSUMS = "atlas_release_gate_checksums.txt"
EXPORT_DIR = "atlas_export"
EXPORT_FILES = ("atlas_registry_copy.json", "atlas_summary.json", "atlas_checksums.txt")
TOP_LEVEL_ALLOWED = {OUTPUT_REPORT, OUTPUT_STEPS, OUTPUT_CHECKSUMS, EXPORT_DIR}

_TRUTH_PATTERNS = (
    re.compile(r"\b(?:is|are|was|were)\s+true\b"),
    re.compile(r"\b(?:is|are|was|were)\s+authentic\b"),
    re.compile(r"\b(?:is|are|was|were)\s+trusted\b"),
    re.compile(r"\bproves?\s+reality\b"),
    re.compile(r"\bproves?\s+truth\b"),
    re.compile(r"\bterms?\s+are\s+true\b"),
    re.compile(r"\bevidence\s+is\s+true\b"),
    re.compile(r"\bclaims?\s+are\s+true\b"),
    re.compile(r"\bfiles?\s+are\s+authentic\b"),
    re.compile(r"\bsources?\s+are\s+trusted\b"),
    re.compile(r"\bcase\s+proves\b"),
)


class VerifyResult:
    def __init__(self, ok, status, reason=""):
        self.ok = bool(ok)
        self.status = status
        self.reason = reason


def _require(cond, msg):
    if not cond:
        raise VerifyError(msg)


def _collect_strings(obj, out):
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for key, val in obj.items():
            out.append(key)
            _collect_strings(val, out)
    elif isinstance(obj, list):
        for val in obj:
            _collect_strings(val, out)


def _scan_truth(report, steps_obj):
    strings = []
    _collect_strings(report, strings)
    _collect_strings(steps_obj, strings)
    for text in strings:
        for sentence in feature_checks._sentences(text):
            low = sentence.lower()
            if feature_checks._is_negated(low):
                continue
            for pattern in _TRUTH_PATTERNS:
                if pattern.search(low):
                    raise VerifyError("truth-like claim detected: %r" % sentence)


def _check_step_order_and_short_circuit(steps_obj):
    plan_ids = [sid for sid, _ in steps_mod.STEP_PLAN]
    plan_ops = [op for _, op in steps_mod.STEP_PLAN]
    got = steps_obj.get("steps")
    _require(isinstance(got, list) and len(got) == len(steps_mod.STEP_PLAN),
             "steps list has wrong shape")
    statuses = []
    for i, st in enumerate(got):
        _require(isinstance(st, dict), "step is not an object")
        _require(st.get("step_id") == plan_ids[i],
                 "wrong step order at position %d" % i)
        _require(st.get("operation") == plan_ops[i],
                 "wrong operation at position %d" % i)
        status = st.get("status")
        _require(status in ALL_STEP_STATUSES, "bad step status: %r" % status)
        statuses.append(status)

    if STEP_FAILED in statuses:
        _require(statuses.count(STEP_FAILED) == 1, "more than one FAILED step")
        idx = statuses.index(STEP_FAILED)
        for i, status in enumerate(statuses):
            if i < idx:
                _require(status == STEP_COMPLETED,
                         "step before failure not COMPLETED")
            elif i > idx:
                _require(status == STEP_SKIPPED,
                         "step after failure not SKIPPED_AFTER_FAILURE")
    else:
        _require(STEP_SKIPPED not in statuses,
                 "SKIPPED_AFTER_FAILURE present without a failed step")
    return statuses


def verify(out_dir):
    top = set(os.listdir(out_dir))
    _require(OUTPUT_REPORT in top, "missing atlas_release_gate_report.json")
    _require(OUTPUT_STEPS in top, "missing atlas_release_gate_steps.json")
    _require(OUTPUT_CHECKSUMS in top, "missing atlas_release_gate_checksums.txt")
    unknown = top - TOP_LEVEL_ALLOWED
    _require(not unknown, "unknown top-level files: %s" % sorted(unknown))

    report_bytes = canonical.read_bytes(os.path.join(out_dir, OUTPUT_REPORT))
    steps_bytes = canonical.read_bytes(os.path.join(out_dir, OUTPUT_STEPS))
    _require(canonical.is_canonical_bytes(report_bytes), "report is not canonical")
    _require(canonical.is_canonical_bytes(steps_bytes), "steps is not canonical")

    report = canonical.load_json(os.path.join(out_dir, OUTPUT_REPORT))
    steps_obj = canonical.load_json(os.path.join(out_dir, OUTPUT_STEPS))

    gate_status = report.get("release_gate_status")
    _require(gate_status in ALL_GATE_STATUSES, "unknown gate status: %r" % gate_status)

    statuses = _check_step_order_and_short_circuit(steps_obj)

    # Export folder hygiene
    export_path = os.path.join(out_dir, EXPORT_DIR)
    export_exists = os.path.isdir(export_path)
    export_complete = False
    if export_exists:
        ex_files = set(os.listdir(export_path))
        unknown_ex = ex_files - set(EXPORT_FILES)
        _require(not unknown_ex, "unknown export files: %s" % sorted(unknown_ex))
        export_complete = set(EXPORT_FILES) <= ex_files

    expected_paths = [checksums.REPORT_PATH, checksums.STEPS_PATH]
    if export_complete:
        expected_paths += [checksums.EXPORT_REGISTRY_COPY,
                           checksums.EXPORT_SUMMARY,
                           checksums.EXPORT_CHECKSUMS]
    checksums.verify_checksums(out_dir, expected_paths)

    _scan_truth(report, steps_obj)

    if gate_status == RELEASE_GATE_PASSED:
        _require(export_complete, "passed gate is missing the atlas_export files")
        _require(all(s == STEP_COMPLETED for s in statuses),
                 "passed gate has a non-COMPLETED step")
        _require(report.get("registry_status") == REGISTRY_VERIFIED,
                 "registry_status is not REGISTRY_VERIFIED")
        _require(report.get("export_status") == EXPORT_VERIFIED,
                 "export_status is not EXPORT_VERIFIED")
        _require(report.get("required_files_present") is True,
                 "required_files_present is not true")
        _require(report.get("documentation_present") is True,
                 "documentation_present is not true")
        _require(report.get("honesty_boundary_present") is True,
                 "honesty_boundary_present is not true")
        _require(report.get("forbidden_features_absent") is True,
                 "forbidden_features_absent is not true")
        return VerifyResult(True, gate_status, "release gate passed")

    return VerifyResult(False, gate_status, "release gate did not pass")
