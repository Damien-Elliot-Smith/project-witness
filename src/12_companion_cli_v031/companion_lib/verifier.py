"""Verification of a Companion v0.3 output folder."""

import os
import re

from . import (canonical, checksums, deep_checksums, steps as steps_mod,
               versions, coordinator_output)
from .errors import (
    VerifyError, COMPANION_COMPLETED, WORKFLOW_COMPLETED, ATLAS_VALIDATED,
    REGISTRY_VERIFIED, ODIN_CONSISTENT, ODIN_CONTRADICTION, CASE_BUNDLE_VERIFIED,
    STEP_COMPLETED, STEP_FAILED, STEP_SKIPPED, ALL_STEP_STATUSES,
    ALL_COMPANION_STATUSES)

OUT_REQUEST = "workflow_request.json"
OUT_REPORT = "companion_report.json"
OUT_STEPS = "companion_steps.json"
OUT_CHECKSUMS = "companion_checksums.txt"
COORD = "coordinator_output"

REQUIRED_TOP_FILES = (OUT_REQUEST, OUT_REPORT, OUT_STEPS, OUT_CHECKSUMS)
ALLOWED_TOP_LEVEL = set(REQUIRED_TOP_FILES) | {COORD}

# Fields the Companion report mirrors from the Coordinator workflow report,
# as (companion_field, coordinator_field) pairs. Only the workflow status is
# renamed; the rest share names.
_MIRROR_FIELDS = (
    ("coordinator_workflow_status", "workflow_status"),
    ("atlas_validation_status", "atlas_validation_status"),
    ("atlas_registry_status", "atlas_registry_status"),
    ("workflow_type", "workflow_type"),
    ("case_id", "case_id"),
    ("evidence_id", "evidence_id"),
    ("sentinel_status", "sentinel_status"),
    ("aletheia_status", "aletheia_status"),
    ("bridge_status", "bridge_status"),
    ("odin_reasoning_status", "odin_reasoning_status"),
    ("case_bundle_status", "case_bundle_status"),
)

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
    def __init__(self, ok, companion_status, reason=""):
        self.ok = bool(ok)
        self.companion_status = companion_status
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
    plan = steps_mod.STEP_PLAN
    got = steps_obj.get("steps")
    _require(isinstance(got, list) and len(got) == len(plan),
             "companion steps malformed")
    statuses = []
    for i, st in enumerate(got):
        _require(st.get("step_id") == plan[i][0], "wrong step order at %d" % i)
        _require(st.get("component") == plan[i][1], "wrong component at %d" % i)
        _require(st.get("operation") == plan[i][2], "wrong operation at %d" % i)
        s = st.get("status")
        _require(s in ALL_STEP_STATUSES, "bad step status: %r" % s)
        statuses.append(s)
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


def verify(out_dir, coordinator_root=None):
    top = set(os.listdir(out_dir))
    for f in REQUIRED_TOP_FILES:
        _require(f in top, "missing required file: %s" % f)
    _require(os.path.isdir(os.path.join(out_dir, COORD)),
             "missing coordinator_output/")
    unknown = top - ALLOWED_TOP_LEVEL
    _require(not unknown, "unknown top-level entries: %s" % sorted(unknown))

    req_bytes = canonical.read_bytes(os.path.join(out_dir, OUT_REQUEST))
    rep_bytes = canonical.read_bytes(os.path.join(out_dir, OUT_REPORT))
    steps_bytes = canonical.read_bytes(os.path.join(out_dir, OUT_STEPS))
    _require(canonical.is_canonical_bytes(req_bytes), "workflow_request not canonical")
    _require(canonical.is_canonical_bytes(rep_bytes), "companion_report not canonical")
    _require(canonical.is_canonical_bytes(steps_bytes), "companion_steps not canonical")

    request = canonical.load_json(os.path.join(out_dir, OUT_REQUEST))
    report = canonical.load_json(os.path.join(out_dir, OUT_REPORT))
    steps_obj = canonical.load_json(os.path.join(out_dir, OUT_STEPS))

    companion_status = report.get("companion_status")
    _require(companion_status in ALL_COMPANION_STATUSES,
             "unknown companion status: %r" % companion_status)

    step_statuses = _check_steps(steps_obj)
    present = checksums.present_paths(out_dir)
    checksums.verify_checksums(out_dir, present)
    # v0.3.2 (RT-004 repair): recurse into every nested component checksum
    # file and enforce the Aletheia manifest's bundled-file hash binding, so
    # tampered evidence bytes fail at the Companion layer instead of only at
    # the component layer.
    deep_checksums.verify_deep(out_dir)
    _scan_truth(report, steps_obj)

    if companion_status != COMPANION_COMPLETED:
        return VerifyResult(False, companion_status, "companion did not complete")

    # ---- completed-run invariants ----
    _require(all(s == STEP_COMPLETED for s in step_statuses),
             "completed companion run has a non-COMPLETED step")
    for rel in checksums.REQUIRED_PATHS:
        _require(os.path.isfile(os.path.join(out_dir, rel)), "missing %s" % rel)

    coord_dir = os.path.join(out_dir, COORD)
    creport = coordinator_output.read_workflow_report(coord_dir)
    cav = coordinator_output.read_atlas_validation(coord_dir)
    registry = coordinator_output.read_registry(coord_dir)

    _require(report.get("coordinator_workflow_version") == "0.3.0",
             "coordinator_workflow_version is not 0.3.0")
    _require(report.get("coordinator_workflow_status") == WORKFLOW_COMPLETED,
             "coordinator_workflow_status is not WORKFLOW_COMPLETED")
    _require(report.get("atlas_validation_status") == ATLAS_VALIDATED,
             "atlas_validation_status is not ATLAS_VALIDATED")
    _require(report.get("atlas_registry_status") == REGISTRY_VERIFIED,
             "atlas_registry_status is not REGISTRY_VERIFIED")

    workflow_types = _names(registry.get("workflow_types"), "workflow_type")
    action_types = _names(registry.get("action_types"), "action_type")
    atlas_statuses = set(_names(registry.get("statuses"), "status"))
    atlas_predicates = set(_names(registry.get("claim_predicates"), "predicate"))

    _require(versions.WORKFLOW_TYPE in workflow_types,
             "workflow type not in copied Atlas registry")
    _require(versions.ACTION_TYPE in action_types,
             "CREATE_DIRECTORY not in copied Atlas registry")

    # Observed statuses that Atlas records must be present. ATLAS_VALIDATED is the
    # Coordinator v0.3 validation result, NOT an Atlas Registry v0.1 term, so it is
    # checked as a fixed value above (rule 18), not looked up in Atlas here.
    for field in ("companion_status", "coordinator_workflow_status",
                  "atlas_registry_status", "sentinel_status", "aletheia_status",
                  "bridge_status", "odin_reasoning_status", "case_bundle_status"):
        val = report.get(field)
        _require(val in atlas_statuses,
                 "observed status %r (%s) not in copied Atlas registry"
                 % (val, field))
    for s in set(step_statuses):
        _require(s in atlas_statuses, "step status %r not in Atlas" % s)

    for pred in versions.REQUIRED_PREDICATES:
        _require(pred in atlas_predicates,
                 "predicate %r not in copied Atlas registry" % pred)

    _require(not _registry_has_truth(registry),
             "copied Atlas registry has truth claims")
    _require(not any(a in versions.FORBIDDEN_ACTION_TYPES for a in action_types),
             "forbidden action type in copied Atlas registry")

    # rule 26 -- Companion mirrors Coordinator report / Atlas validation report
    for comp_field, coord_field in _MIRROR_FIELDS:
        _require(report.get(comp_field) == creport.get(coord_field),
                 "mirrored field %r differs from Coordinator report" % comp_field)
    _require(report.get("atlas_validation_status") == cav.get("atlas_validation_status"),
             "atlas_validation_status differs from Atlas validation report")
    _require(report.get("atlas_registry_status") == cav.get("atlas_registry_status"),
             "atlas_registry_status differs from Atlas validation report")

    # ODIN / Case Bundle acceptance
    _require(report.get("odin_reasoning_status") in (ODIN_CONSISTENT, ODIN_CONTRADICTION),
             "ODIN reasoning status not accepted")
    _require(report.get("case_bundle_status") == CASE_BUNDLE_VERIFIED,
             "case bundle status is not BUNDLED_VERIFIED_CASE")

    # rule 27/28 -- id consistency
    case_id = report.get("case_id")
    evidence_id = report.get("evidence_id")
    _require(case_id, "missing case_id")
    _require(evidence_id, "missing evidence_id")
    _require(steps_obj.get("case_id") == case_id, "case_id mismatch in companion steps")
    _require(creport.get("case_id") == case_id, "case_id mismatch in coordinator report")
    manifest = canonical.load_json(
        os.path.join(coord_dir, "case_bundle_v02", "case_manifest.json"))
    _require(manifest.get("case_id") == case_id, "case_id mismatch in case bundle")
    _require(request.get("evidence_id") == evidence_id,
             "evidence_id mismatch in workflow request")
    _require(creport.get("evidence_id") == evidence_id,
             "evidence_id mismatch in coordinator report")

    # rule 29 -- Coordinator output verifies (structural fallback)
    coordinator_output.structural_verify(coord_dir)

    return VerifyResult(True, companion_status, "companion completed")


def _registry_has_truth(registry):
    for s in registry.get("statuses", []):
        if isinstance(s, dict) and s.get("truth_claim") is True:
            return True
    for p in registry.get("claim_predicates", []):
        if isinstance(p, dict) and p.get("truth_claim") is True:
            return True
    return False
