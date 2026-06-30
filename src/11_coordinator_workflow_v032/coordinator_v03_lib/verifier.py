"""Verification of a Coordinator v0.3 output folder."""

import os
import re

from . import canonical, checksums, steps as steps_mod, versions
from .errors import (
    VerifyError, WORKFLOW_COMPLETED, ATLAS_VALIDATED, REGISTRY_VERIFIED,
    ODIN_CONSISTENT, ODIN_CONTRADICTION, CASE_BUNDLE_VERIFIED,
    STEP_COMPLETED, STEP_FAILED, STEP_SKIPPED, ALL_STEP_STATUSES,
    ALL_WORKFLOW_STATUSES, ALL_ATLAS_STATUSES,
)

OUT_REQUEST_COPY = "workflow_request_copy.json"
OUT_REPORT = "workflow_report.json"
OUT_STEPS = "workflow_steps.json"
OUT_CHECKSUMS = "workflow_checksums.txt"
OUT_ATLAS_VALIDATION = "atlas_validation_report.json"
OUT_ATLAS_COPY = "atlas_registry_copy.json"

REQUIRED_TOP_FILES = (OUT_REQUEST_COPY, OUT_REPORT, OUT_STEPS, OUT_CHECKSUMS,
                      OUT_ATLAS_VALIDATION, OUT_ATLAS_COPY)
REQUIRED_DIRS = (
    "sentinel_run", "histor_sentinel_case", "aletheia_bundle",
    "histor_aletheia_case", "bridge_output", "odin_output",
    "histor_odin_case", "case_bundle_v02",
)
ALLOWED_TOP_LEVEL = set(REQUIRED_TOP_FILES) | set(REQUIRED_DIRS)

_TRUTH_PATTERNS = (
    re.compile(r"\b(?:is|are|was|were)\s+true\b"),
    re.compile(r"\b(?:is|are|was|were)\s+authentic\b"),
    re.compile(r"\b(?:is|are|was|were)\s+trusted\b"),
    re.compile(r"\bproves?\s+reality\b"),
    re.compile(r"\bproves?\s+truth\b"),
    re.compile(r"\bevidence\s+is\s+true\b"),
    re.compile(r"\bclaims?\s+are\s+true\b"),
    re.compile(r"\bfiles?\s+are\s+authentic\b"),
    re.compile(r"\bsources?\s+are\s+trusted\b"),
)
_NEGATION = ("does not", "do not", "not ", "no ", "never", "without", "n't")
_SENT = re.compile(r"[.\n;:!?]+")


class VerifyResult:
    def __init__(self, ok, workflow_status, reason=""):
        self.ok = bool(ok)
        self.workflow_status = workflow_status
        self.reason = reason


def _require(cond, msg):
    if not cond:
        raise VerifyError(msg)


def _collect_strings(obj, out):
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            out.append(k)
            _collect_strings(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _collect_strings(v, out)


def _scan_truth(*objs):
    strings = []
    for obj in objs:
        _collect_strings(obj, strings)
    for text in strings:
        for sentence in (s.strip() for s in _SENT.split(text) if s.strip()):
            low = sentence.lower()
            if any(m in low for m in _NEGATION):
                continue
            for pat in _TRUTH_PATTERNS:
                if pat.search(low):
                    raise VerifyError("truth-like claim detected: %r" % sentence)


def _names(items, key):
    return [it[key] for it in (items if isinstance(items, list) else [])
            if isinstance(it, dict) and key in it]


def _check_steps(steps_obj):
    plan_ids = [sid for sid, _ in steps_mod.STEP_PLAN]
    plan_ops = [op for _, op in steps_mod.STEP_PLAN]
    got = steps_obj.get("steps")
    _require(isinstance(got, list) and len(got) == len(steps_mod.STEP_PLAN),
             "steps list has wrong shape")
    statuses = []
    for i, st in enumerate(got):
        _require(isinstance(st, dict), "step is not an object")
        _require(st.get("step_id") == plan_ids[i], "wrong step order at %d" % i)
        _require(st.get("operation") == plan_ops[i], "wrong operation at %d" % i)
        status = st.get("status")
        _require(status in ALL_STEP_STATUSES, "bad step status: %r" % status)
        statuses.append(status)
    if STEP_FAILED in statuses:
        _require(statuses.count(STEP_FAILED) == 1, "more than one FAILED step")
        idx = statuses.index(STEP_FAILED)
        for i, s in enumerate(statuses):
            if i < idx:
                _require(s == STEP_COMPLETED, "step before failure not COMPLETED")
            elif i > idx:
                _require(s == STEP_SKIPPED, "step after failure not SKIPPED")
    else:
        _require(STEP_SKIPPED not in statuses, "SKIPPED without a FAILED step")
    return statuses


def verify(out_dir):
    top = set(os.listdir(out_dir))
    for f in (OUT_REQUEST_COPY, OUT_REPORT, OUT_STEPS, OUT_CHECKSUMS,
              OUT_ATLAS_VALIDATION):
        _require(f in top, "missing required file: %s" % f)
    unknown = top - ALLOWED_TOP_LEVEL
    _require(not unknown, "unknown top-level entries: %s" % sorted(unknown))

    # canonical checks
    report_bytes = canonical.read_bytes(os.path.join(out_dir, OUT_REPORT))
    steps_bytes = canonical.read_bytes(os.path.join(out_dir, OUT_STEPS))
    request_bytes = canonical.read_bytes(os.path.join(out_dir, OUT_REQUEST_COPY))
    av_bytes = canonical.read_bytes(os.path.join(out_dir, OUT_ATLAS_VALIDATION))
    _require(canonical.is_canonical_bytes(report_bytes), "report not canonical")
    _require(canonical.is_canonical_bytes(steps_bytes), "steps not canonical")
    _require(canonical.is_canonical_bytes(request_bytes), "request copy not canonical")
    _require(canonical.is_canonical_bytes(av_bytes),
             "atlas validation report not canonical")

    report = canonical.load_json(os.path.join(out_dir, OUT_REPORT))
    steps_obj = canonical.load_json(os.path.join(out_dir, OUT_STEPS))
    request = canonical.load_json(os.path.join(out_dir, OUT_REQUEST_COPY))
    atlas_validation = canonical.load_json(os.path.join(out_dir, OUT_ATLAS_VALIDATION))

    workflow_status = report.get("workflow_status")
    _require(workflow_status in ALL_WORKFLOW_STATUSES,
             "unknown workflow status: %r" % workflow_status)

    step_statuses = _check_steps(steps_obj)

    # checksums over present required paths
    present = checksums.present_paths(out_dir)
    checksums.verify_checksums(out_dir, present)

    # truth scan over report, steps, and atlas validation report
    _scan_truth(report, steps_obj, atlas_validation)

    if workflow_status != WORKFLOW_COMPLETED:
        return VerifyResult(False, workflow_status, "workflow did not complete")

    # ---- completed-workflow invariants ----
    _require(all(s == STEP_COMPLETED for s in step_statuses),
             "completed workflow has a non-COMPLETED step")
    for f in REQUIRED_TOP_FILES:
        _require(os.path.isfile(os.path.join(out_dir, f)), "missing %s" % f)
    for d in REQUIRED_DIRS:
        _require(os.path.isdir(os.path.join(out_dir, d)), "missing folder %s" % d)
    for rel in checksums.REQUIRED_PATHS:
        _require(os.path.isfile(os.path.join(out_dir, rel)), "missing %s" % rel)

    _require(report.get("atlas_validation_status") == ATLAS_VALIDATED,
             "atlas_validation_status is not ATLAS_VALIDATED")
    _require(report.get("atlas_registry_status") == REGISTRY_VERIFIED,
             "atlas_registry_status is not REGISTRY_VERIFIED")

    # atlas registry copy must be canonical Atlas form and verify the vocabulary
    copy_bytes = canonical.read_bytes(os.path.join(out_dir, OUT_ATLAS_COPY))
    _require(canonical.is_atlas_canonical_bytes(copy_bytes),
             "atlas registry copy is not canonical")
    registry = canonical.load_json(os.path.join(out_dir, OUT_ATLAS_COPY))

    workflow_types = _names(registry.get("workflow_types"), "workflow_type")
    action_types = _names(registry.get("action_types"), "action_type")
    atlas_statuses = set(_names(registry.get("statuses"), "status"))
    atlas_predicates = set(_names(registry.get("claim_predicates"), "predicate"))

    _require(report.get("workflow_type") in workflow_types
             if report.get("workflow_type") else versions.WORKFLOW_TYPE in workflow_types,
             "workflow type not present in copied Atlas registry")
    _require(versions.ACTION_TYPE in action_types,
             "CREATE_DIRECTORY not present in copied Atlas registry")

    # observed statuses must all be in Atlas
    observed_status_fields = (
        "sentinel_status", "aletheia_status", "bridge_status",
        "odin_reasoning_status", "histor_sentinel_status",
        "histor_aletheia_status", "histor_odin_status", "case_bundle_status",
        "workflow_status",
    )
    for field in observed_status_fields:
        val = report.get(field)
        _require(val in atlas_statuses,
                 "observed status %r (%s) not in Atlas vocabulary" % (val, field))
    for s in set(step_statuses):
        _require(s in atlas_statuses,
                 "step status %r not in Atlas vocabulary" % s)

    # observed predicates from Bridge/ODIN must be in Atlas
    observed_predicates = _observed_predicates(out_dir)
    for pred in observed_predicates:
        _require(pred in atlas_predicates,
                 "observed predicate %r not in Atlas vocabulary" % pred)

    # no Atlas truth claims / no forbidden actions in the copied registry
    _require(not _registry_has_truth(registry), "Atlas registry copy has truth claims")
    _require(not any(a in versions.FORBIDDEN_ACTION_TYPES for a in action_types),
             "forbidden action type present in copied Atlas registry")

    # ODIN status must be CONSISTENT or CONTRADICTION_DETECTED
    _require(report.get("odin_reasoning_status") in (ODIN_CONSISTENT, ODIN_CONTRADICTION),
             "ODIN reasoning status not accepted")
    # Case Bundle must be BUNDLED
    _require(report.get("case_bundle_status") == CASE_BUNDLE_VERIFIED,
             "case bundle status is not BUNDLED_VERIFIED_CASE")

    # id consistency across outputs
    _check_id_consistency(out_dir, report, request)

    return VerifyResult(True, workflow_status, "workflow completed")


def _observed_predicates(out_dir):
    preds = set()
    for rel in ("bridge_output/odin_claims.json", "odin_output/reasoning_report.json"):
        path = os.path.join(out_dir, rel)
        if os.path.isfile(path):
            obj = canonical.load_json(path)
            for p in obj.get("predicates", []):
                preds.add(p)
            if obj.get("predicate"):
                preds.add(obj["predicate"])
    return preds


def _registry_has_truth(registry):
    for s in registry.get("statuses", []):
        if isinstance(s, dict) and s.get("truth_claim") is True:
            return True
    for p in registry.get("claim_predicates", []):
        if isinstance(p, dict) and p.get("truth_claim") is True:
            return True
    return False


def _check_id_consistency(out_dir, report, request):
    case_id = report.get("case_id")
    evidence_id = report.get("evidence_id")
    _require(case_id, "missing case_id in report")
    _require(evidence_id, "missing evidence_id in report")
    _require(request.get("evidence_id") == evidence_id,
             "evidence_id mismatch between request and report")

    case_files = {
        "sentinel_run/run_report.json": "case_id",
        "histor_sentinel_case/case_summary.json": "case_id",
        "histor_aletheia_case/evidence_case_summary.json": "case_id",
        "histor_odin_case/odin_case_summary.json": "case_id",
        "case_bundle_v02/case_manifest.json": "case_id",
    }
    for rel, key in case_files.items():
        path = os.path.join(out_dir, rel)
        if os.path.isfile(path):
            obj = canonical.load_json(path)
            _require(obj.get(key) == case_id,
                     "case_id mismatch in %s" % rel)

    evid_files = {
        "sentinel_run/run_report.json": "evidence_id",
        "aletheia_bundle/evidence_manifest.json": "evidence_id",
        "histor_aletheia_case/evidence_case_summary.json": "evidence_id",
        "case_bundle_v02/case_manifest.json": "evidence_id",
    }
    for rel, key in evid_files.items():
        path = os.path.join(out_dir, rel)
        if os.path.isfile(path) and key in canonical.load_json(path):
            obj = canonical.load_json(path)
            _require(obj.get(key) == evidence_id,
                     "evidence_id mismatch in %s" % rel)
