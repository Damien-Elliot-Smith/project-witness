"""Verify a unified case manifest output folder. Does not require the original
source folder to still exist; it verifies the manifest package itself."""

import os
import re

from . import canonical, checksums, validation, versions
from .errors import (VerifyError, SOURCE_VERIFIED, NOT_APPLICABLE, SENTINEL_OK,
                     ALETHEIA_OK, BRIDGE_OK, ODIN_OK, CASE_BUNDLE_OK)

MANIFEST_FILE = "unified_case_manifest.json"
SOURCE_INDEX_FILE = "source_index.json"
CHECKSUMS_FILE = "unified_manifest_checksums.txt"
REQUIRED_TOP = (MANIFEST_FILE, SOURCE_INDEX_FILE, CHECKSUMS_FILE)
ALLOWED_TOP = set(REQUIRED_TOP)

_TRUTH_PATTERNS = (
    re.compile(r"\b(?:is|are|was|were)\s+true\b"),
    re.compile(r"\b(?:is|are|was|were)\s+authentic\b"),
    re.compile(r"\b(?:is|are|was|were)\s+trusted\b"),
    re.compile(r"\bproves?\s+reality\b"),
    re.compile(r"\bproves?\s+truth\b"),
    re.compile(r"\bevidence\s+is\s+true\b"),
    re.compile(r"\bclaims?\s+are\s+true\b"),
    re.compile(r"\bfile\s+is\s+authentic\b"),
    re.compile(r"\bsource\s+is\s+trusted\b"),
    re.compile(r"\bproves?\s+reality\b"),
)
_NEGATION = ("does not", "do not", "not ", "no ", "never", "without", "n't")
_SENT = re.compile(r"[.\n;:!?]+")


class VerifyResult:
    def __init__(self, ok, source_status, reason=""):
        self.ok = bool(ok)
        self.source_status = source_status
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


def _scan_truth_flags(obj):
    if isinstance(obj, dict):
        if obj.get("truth_claim") is True:
            raise VerifyError("truth-claim flag present in manifest")
        for v in obj.values():
            _scan_truth_flags(v)
    elif isinstance(obj, list):
        for v in obj:
            _scan_truth_flags(v)


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
    artifacts = m.get("source_artifacts")
    _require(isinstance(artifacts, list) and artifacts, "no source_artifacts")
    seen_ids, seen_paths = set(), set()
    for art in artifacts:
        aid = art.get("artifact_id")
        rel = art.get("relative_path")
        digest = art.get("sha256")
        _require(aid and aid not in seen_ids, "duplicate/empty artifact_id: %r" % aid)
        _require(rel and rel not in seen_paths, "duplicate/empty relative_path: %r" % rel)
        _require(validation.is_relative_path(rel), "absolute artifact path: %r" % rel)
        _require(isinstance(digest, str) and re.match(r"^[0-9a-f]{64}$", digest),
                 "bad artifact sha256: %r" % digest)
        seen_ids.add(aid)
        seen_paths.add(rel)


def verify(out_dir):
    top = set(os.listdir(out_dir))
    for f in REQUIRED_TOP:
        _require(f in top, "missing required file: %s" % f)
    unknown = top - ALLOWED_TOP
    _require(not unknown, "unknown top-level entries: %s" % sorted(unknown))

    man_bytes = canonical.read_bytes(os.path.join(out_dir, MANIFEST_FILE))
    idx_bytes = canonical.read_bytes(os.path.join(out_dir, SOURCE_INDEX_FILE))
    _require(canonical.is_canonical_bytes(man_bytes), "manifest not canonical")
    _require(canonical.is_canonical_bytes(idx_bytes), "source_index not canonical")

    manifest = canonical.load_json(os.path.join(out_dir, MANIFEST_FILE))
    source_index = canonical.load_json(os.path.join(out_dir, SOURCE_INDEX_FILE))

    checksums.verify_checksums(out_dir)

    _require(validation.is_valid_source_type(manifest.get("source_type")),
             "invalid source_type")
    source_status = manifest.get("source_status")
    _require(source_status == SOURCE_VERIFIED,
             "source_status is not SOURCE_VERIFIED")
    _require(validation.is_safe_id(manifest.get("case_id")), "invalid case_id")
    _require(validation.is_safe_id(manifest.get("evidence_id")), "invalid evidence_id")
    _require(manifest.get("workflow_type") == versions.WORKFLOW_TYPE,
             "invalid workflow_type")
    _require(manifest.get("action_type") == versions.ACTION_TYPE,
             "invalid action_type")
    _check_statuses(manifest)
    _check_artifacts(manifest)
    _scan_truth_flags(manifest)
    _scan_truth(manifest, source_index)

    return VerifyResult(True, source_status, "manifest verified")
