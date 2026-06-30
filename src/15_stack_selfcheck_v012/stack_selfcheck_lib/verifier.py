"""Verify a Stack Selfcheck v0.1 output folder. Does not require the inventory or
the Stack Verifier output to still exist."""

import os
import re

from . import canonical, checksums, validation, versions, steps as steps_mod
from .errors import (VerifyError, STACK_SELFCHECK_PASSED, INVENTORY_VERIFIED,
                     STACK_VERIFIER_OUTPUT_VERIFIED, STACK_VERIFIER_NOT_PROVIDED,
                     STEP_COMPLETED, STEP_FAILED, STEP_SKIPPED, ALL_STEP_STATUSES,
                     DOCUMENTATION_BOUNDARY_VERIFIED,
                     COMPONENT_CHECKED, COMPONENT_LEGACY_DOCUMENTATION_ACCEPTED)

REPORT_FILE = "stack_selfcheck_report.json"
STEPS_FILE = "stack_selfcheck_steps.json"
CHECKSUMS_FILE = "stack_selfcheck_checksums.txt"
REQUIRED_TOP = (REPORT_FILE, STEPS_FILE, CHECKSUMS_FILE)
ALLOWED_TOP = set(REQUIRED_TOP)

_BOOLEANS = ("required_components_present", "component_versions_consistent",
             "component_roots_present", "zip_sidecars_valid",
             "documentation_boundaries_present", "truth_boundary_valid")

_TRUTH_PATTERNS = (
    re.compile(r"\b(?:is|are|was|were)\s+true\b"),
    re.compile(r"\b(?:is|are|was|were)\s+authentic\b"),
    re.compile(r"\b(?:is|are|was|were)\s+trusted\b"),
    re.compile(r"\bproves?\s+reality\b"),
    re.compile(r"\bproves?\s+truth\b"),
    re.compile(r"\bevidence\s+is\s+true\b"),
    re.compile(r"\bclaims?\s+are\s+true\b"),
    re.compile(r"\bproves?\s+the\s+stack\s+works\b"),
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


def _check_components(report):
    comps = report.get("checked_components")
    _require(isinstance(comps, list) and comps, "no checked_components")
    seen = set()
    for c in comps:
        cid = c.get("component_id")
        _require(validation.is_safe_id(cid), "unsafe component_id: %r" % cid)
        _require(cid not in seen, "duplicate component_id: %r" % cid)
        seen.add(cid)


_ALLOWANCE_FIELDS = frozenset({
    "component_id", "legacy_documentation_profile",
    "legacy_documentation_allowance_used", "missing_docs_allowed", "reason"})


def _check_legacy_allowances(report):
    """Confirm the legacy documentation allowances are well-formed and honest.

    The verifier independently re-derives the permitted omissions from the
    registry; it never trusts the report's own claim of entitlement. Anything
    inconsistent, over-broad, unknown, or silently passed fails.
    """
    allowances = report.get("legacy_documentation_allowances")
    _require(isinstance(allowances, list), "legacy_documentation_allowances missing")

    used_in_records = set()
    seen = set()
    last = None
    for rec in allowances:
        _require(isinstance(rec, dict), "legacy allowance is not an object")
        _require(set(rec) == _ALLOWANCE_FIELDS,
                 "legacy allowance has unexpected fields")
        cid = rec["component_id"]
        _require(validation.is_safe_id(cid), "legacy allowance unsafe id: %r" % cid)
        _require(cid not in seen, "duplicate legacy allowance: %r" % cid)
        seen.add(cid)
        # records must be sorted by component_id (canonical, stable order)
        _require(last is None or cid > last, "legacy allowances not sorted")
        last = cid
        _require(cid in versions.LEGACY_DOCUMENTATION_ALLOWANCES,
                 "legacy allowance for non-legacy component: %r" % cid)
        _require(rec["legacy_documentation_profile"]
                 == versions.LEGACY_DOCUMENTATION_PROFILE,
                 "legacy allowance wrong profile: %r" % cid)
        missing = rec["missing_docs_allowed"]
        _require(isinstance(missing, list), "missing_docs_allowed not a list")
        registry = versions.LEGACY_DOCUMENTATION_ALLOWANCES[cid]
        _require(set(missing) <= set(registry),
                 "legacy allowance exceeds registry for %r" % cid)
        _require(len(set(missing)) == len(missing),
                 "duplicate missing_docs_allowed for %r" % cid)
        used = rec["legacy_documentation_allowance_used"]
        _require(isinstance(used, bool), "allowance_used not bool for %r" % cid)
        # honesty: used iff something was actually omitted (never silent)
        _require(used == bool(missing),
                 "legacy allowance_used inconsistent with missing_docs for %r" % cid)
        _require(isinstance(rec["reason"], str) and rec["reason"],
                 "legacy allowance missing reason for %r" % cid)
        if used:
            used_in_records.add(cid)

    # Cross-check against checked_components: the set of components marked
    # COMPONENT_LEGACY_DOCUMENTATION_ACCEPTED must equal the set that actually
    # used an allowance. No component may quietly carry one view but not the
    # other.
    marked = set()
    for c in report["checked_components"]:
        status = c.get("check_status")
        _require(status in (COMPONENT_CHECKED,
                            COMPONENT_LEGACY_DOCUMENTATION_ACCEPTED),
                 "unexpected check_status: %r" % status)
        if status == COMPONENT_LEGACY_DOCUMENTATION_ACCEPTED:
            marked.add(c["component_id"])
            _require(c.get("legacy_documentation_profile")
                     == versions.LEGACY_DOCUMENTATION_PROFILE,
                     "legacy component missing profile in checked_components")
        else:
            _require(c.get("legacy_documentation_profile") is None,
                     "non-legacy component carries a legacy profile")
    _require(marked == used_in_records,
             "legacy markings inconsistent between report sections")


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

    _require(report.get("stack_selfcheck_status") == STACK_SELFCHECK_PASSED,
             "stack_selfcheck_status is not STACK_SELFCHECK_PASSED")
    _require(report.get("inventory_status") == INVENTORY_VERIFIED,
             "inventory_status is not INVENTORY_VERIFIED")
    for b in _BOOLEANS:
        _require(report.get(b) is True, "boolean %s is not true" % b)
    _require(report.get("documentation_boundary_status")
             == DOCUMENTATION_BOUNDARY_VERIFIED,
             "documentation_boundary_status is not DOCUMENTATION_BOUNDARY_VERIFIED")
    _require(report.get("stack_verifier_status") in
             (STACK_VERIFIER_OUTPUT_VERIFIED, STACK_VERIFIER_NOT_PROVIDED),
             "invalid stack_verifier_status")
    _check_components(report)
    _check_legacy_allowances(report)
    _require(validation.has_no_absolute_paths(report),
             "absolute path stored in report")
    _require(all(s == STEP_COMPLETED for s in step_statuses),
             "passed selfcheck has a non-COMPLETED step")

    return VerifyResult(True, report.get("stack_selfcheck_status"), "stack selfcheck verified")
