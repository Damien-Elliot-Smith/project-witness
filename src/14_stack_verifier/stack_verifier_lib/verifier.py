"""Verify a Stack Verifier v0.1 output folder. Does not require the original
source or manifest folders to still exist."""

import os
import re

from . import canonical, checksums, validation, versions, steps as steps_mod
from .errors import (VerifyError, STACK_VERIFIED, SOURCE_VERIFIED,
                     MANIFEST_VERIFIED, MANIFEST_NOT_PROVIDED, NOT_APPLICABLE,
                     SENTINEL_OK, ALETHEIA_OK, BRIDGE_OK, ODIN_OK, CASE_BUNDLE_OK,
                     STEP_COMPLETED, STEP_FAILED, STEP_SKIPPED, ALL_STEP_STATUSES)

REPORT_FILE = "stack_verification_report.json"
STEPS_FILE = "stack_verification_steps.json"
CHECKSUMS_FILE = "stack_verification_checksums.txt"
REQUIRED_TOP = (REPORT_FILE, STEPS_FILE, CHECKSUMS_FILE)
ALLOWED_TOP = set(REQUIRED_TOP)

_BOOLEANS = ("case_id_consistent", "evidence_id_consistent", "checksums_valid",
             "atlas_vocabulary_valid", "truth_boundary_valid")

_TRUTH_PATTERNS = (
    re.compile(r"\b(?:is|are|was|were)\s+true\b"),
    re.compile(r"\b(?:is|are|was|were)\s+authentic\b"),
    re.compile(r"\b(?:is|are|was|were)\s+trusted\b"),
    re.compile(r"\bproves?\s+reality\b"),
    re.compile(r"\bproves?\s+truth\b"),
    re.compile(r"\bevidence\s+is\s+true\b"),
    re.compile(r"\bclaims?\s+are\s+true\b"),
)
_NEGATION = ("does not", "do not", "not ", "no ", "never", "without", "n't")
_SENT = re.compile(r"[.\n;:!?]+")


class VerifyResult:
    def __init__(self, ok, stack_status, reason=""):
        self.ok = bool(ok)
        self.stack_status = stack_status
        self.reason = reason


def _require(cond, msg):
    if not cond:
        raise VerifyError(msg)


def _collect(obj, out):
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            out.append(k)
            _collect(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _collect(v, out)


def _scan_truth(*objs):
    strings = []
    for obj in objs:
        _collect(obj, strings)
    for text in strings:
        for sentence in (s.strip() for s in _SENT.split(text) if s.strip()):
            low = sentence.lower()
            if any(m in low for m in _NEGATION):
                continue
            for pat in _TRUTH_PATTERNS:
                if pat.search(low):
                    raise VerifyError("truth-like claim detected: %r" % sentence)


def _check_steps(steps_obj):
    plan = steps_mod.STEP_PLAN
    got = steps_obj.get("steps")
    _require(isinstance(got, list) and len(got) == len(plan), "steps malformed")
    statuses = []
    for i, st in enumerate(got):
        _require(st.get("step_id") == plan[i][0], "wrong step order at %d" % i)
        _require(st.get("operation") == plan[i][1], "wrong operation at %d" % i)
        s = st.get("status")
        _require(s in ALL_STEP_STATUSES, "bad step status: %r" % s)
        statuses.append(s)
    if STEP_FAILED in statuses:
        idx = statuses.index(STEP_FAILED)
        for i, s in enumerate(statuses):
            if i < idx:
                _require(s == STEP_COMPLETED, "step before failure not COMPLETED")
            elif i > idx:
                _require(s == STEP_SKIPPED, "step after failure not SKIPPED")
    else:
        _require(STEP_SKIPPED not in statuses, "SKIPPED without FAILED")
    return statuses


def _check_statuses(m):
    _require(m.get("companion_status") in ("COMPANION_COMPLETED", NOT_APPLICABLE),
             "invalid companion_status")
    _require(m.get("coordinator_workflow_status") == "WORKFLOW_COMPLETED",
             "invalid coordinator_workflow_status")
    _require(m.get("atlas_validation_status") == "ATLAS_VALIDATED",
             "invalid atlas_validation_status")
    _require(m.get("atlas_registry_status") == "REGISTRY_VERIFIED",
             "invalid atlas_registry_status")
    _require(m.get("sentinel_status") in SENTINEL_OK, "invalid sentinel_status")
    _require(m.get("aletheia_status") in ALETHEIA_OK, "invalid aletheia_status")
    _require(m.get("bridge_status") in BRIDGE_OK, "invalid bridge_status")
    _require(m.get("odin_reasoning_status") in ODIN_OK, "invalid odin_reasoning_status")
    _require(m.get("case_bundle_status") in CASE_BUNDLE_OK, "invalid case_bundle_status")


def _check_artifacts(m):
    arts = m.get("checked_artifacts")
    _require(isinstance(arts, list) and arts, "no checked_artifacts")
    seen_ids, seen_paths = set(), set()
    for art in arts:
        label = art.get("source_label")
        aid = art.get("artifact_id")
        rel = art.get("relative_path")
        digest = art.get("sha256")
        _require(label in (versions.LABEL_SOURCE, versions.LABEL_MANIFEST),
                 "bad source_label: %r" % label)
        _require(aid and (label, aid) not in seen_ids,
                 "duplicate artifact_id: %s/%s" % (label, aid))
        _require(rel and (label, rel) not in seen_paths,
                 "duplicate path: %s/%s" % (label, rel))
        _require(validation.is_relative_path(rel), "absolute artifact path: %r" % rel)
        _require(isinstance(digest, str) and re.match(r"^[0-9a-f]{64}$", digest),
                 "bad artifact sha256: %r" % digest)
        seen_ids.add((label, aid))
        seen_paths.add((label, rel))


def verify(out_dir):
    top = set(os.listdir(out_dir))
    for f in REQUIRED_TOP:
        _require(f in top, "missing required file: %s" % f)
    unknown = top - ALLOWED_TOP
    _require(not unknown, "unknown top-level entries: %s" % sorted(unknown))

    rep_bytes = canonical.read_bytes(os.path.join(out_dir, REPORT_FILE))
    steps_bytes = canonical.read_bytes(os.path.join(out_dir, STEPS_FILE))
    _require(canonical.is_canonical_bytes(rep_bytes), "report not canonical")
    _require(canonical.is_canonical_bytes(steps_bytes), "steps not canonical")

    report = canonical.load_json(os.path.join(out_dir, REPORT_FILE))
    steps_obj = canonical.load_json(os.path.join(out_dir, STEPS_FILE))

    checksums.verify_checksums(out_dir)
    step_statuses = _check_steps(steps_obj)
    _scan_truth(report, steps_obj)

    _require(validation.is_valid_source_type(report.get("source_type")),
             "invalid source_type")
    _require(report.get("stack_verification_status") == STACK_VERIFIED,
             "stack_verification_status is not STACK_VERIFIED")
    _require(report.get("source_status") == SOURCE_VERIFIED,
             "source_status is not SOURCE_VERIFIED")
    _require(report.get("manifest_status") in (MANIFEST_VERIFIED, MANIFEST_NOT_PROVIDED),
             "invalid manifest_status")
    _require(validation.is_safe_id(report.get("case_id")), "invalid case_id")
    _require(validation.is_safe_id(report.get("evidence_id")), "invalid evidence_id")
    _require(report.get("workflow_type") == versions.WORKFLOW_TYPE, "invalid workflow_type")
    _require(report.get("action_type") == versions.ACTION_TYPE, "invalid action_type")
    _check_statuses(report)
    for b in _BOOLEANS:
        _require(report.get(b) is True, "boolean %s is not true" % b)
    if report.get("manifest_status") == MANIFEST_VERIFIED:
        _require(report.get("manifest_consistent") is True,
                 "manifest_consistent is not true")
    _check_artifacts(report)
    _require(all(s == STEP_COMPLETED for s in step_statuses),
             "verified output has a non-COMPLETED step")

    return VerifyResult(True, report.get("stack_verification_status"), "stack verified")
