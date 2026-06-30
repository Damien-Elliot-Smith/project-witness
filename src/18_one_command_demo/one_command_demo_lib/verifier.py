"""Verify a One-Command Demo wrapper output folder.

Checks the exact top-level entries, canonical report, strict checksums, the
required statuses, the truth boundary, the absence of affirmative truth claims,
and the absence of absolute local paths. Read-only; no subprocess; no frozen
components.
"""

import os
import re

from . import canonical, checksums, versions
from .errors import VerifyError

ALLOWED_TOP_LEVEL = {
    checksums.REPORT_FILE, checksums.STEPS_FILE, checksums.CHECKSUMS_FILE,
    "connected_demo_output",
}

_NEGATION = ("does not", "do not", "not ", "no ", "never", "without", "n't",
             "cannot", "neither", "nor ", "makes no", "make no", "nothing",
             "remains possible", "only runs")
_TRUTH_PATTERNS = (
    re.compile(r"\b(?:evidence|content|contents|claim|claims|file|files|"
               r"source|sources)\b[^.?!]{0,30}?\b(?:is|are)\s+true\b"),
    re.compile(r"\b(?:file|files|source|sources|evidence)\b[^.?!]{0,30}?"
               r"\b(?:is|are)\s+(?:authentic|trusted)\b"),
    re.compile(r"\bproves?\s+truth\b"),
    re.compile(r"\bproves?\s+reality\b"),
    re.compile(r"\bverif(?:y|ies)\s+external\s+reality\b"),
)
_ABS_PATH = re.compile(r"(?:^|[\"\s:])(?:/home/|/mnt/|/root/|/Users/|[A-Za-z]:\\\\)")
_SENT = re.compile(r"[.!?]+")


def _sentences(text):
    out = []
    for raw in _SENT.split(text.lower()):
        s = " ".join(raw.split())
        if s:
            out.append(s)
    return out


def _walk_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            for item in _walk_strings(value):
                yield item
    elif isinstance(obj, list):
        for value in obj:
            for item in _walk_strings(value):
                yield item


def _scan_truth(report):
    for text in _walk_strings(report):
        for sentence in _sentences(text):
            if any(m in sentence for m in _NEGATION):
                continue
            for pat in _TRUTH_PATTERNS:
                if pat.search(sentence):
                    raise VerifyError("truth-like claim in report: %r"
                                      % sentence[:70])


def _scan_absolute_paths(report):
    for text in _walk_strings(report):
        if _ABS_PATH.search(text):
            raise VerifyError("absolute path in report: %r" % text[:60])


def verify(out_dir):
    if not os.path.isdir(out_dir):
        raise VerifyError("output directory does not exist")

    entries = set(os.listdir(out_dir))
    unknown = entries - ALLOWED_TOP_LEVEL
    if unknown:
        raise VerifyError("unknown top-level entries: %s" % sorted(unknown))
    for required in ALLOWED_TOP_LEVEL:
        if required not in entries:
            raise VerifyError("missing top-level entry: %s" % required)
    if not os.path.isdir(os.path.join(out_dir, "connected_demo_output")):
        raise VerifyError("connected_demo_output is not a directory")

    report_path = os.path.join(out_dir, checksums.REPORT_FILE)
    with open(report_path, "rb") as handle:
        raw = handle.read()
    report = canonical.load_json(report_path)
    if raw != canonical.canonical_bytes(report):
        raise VerifyError("report is not canonical")

    checksums.verify_checksums(out_dir)

    if report.get("wrapper_status") != "ONE_COMMAND_DEMO_COMPLETED":
        raise VerifyError("wrapper_status is not ONE_COMMAND_DEMO_COMPLETED")
    for key, expected in versions.REQUIRED_STATUSES.items():
        if report.get(key) != expected:
            raise VerifyError("required status missing or wrong: %s" % key)
    if report.get("truth_boundary_valid") is not True:
        raise VerifyError("truth_boundary_valid is not true")

    _scan_truth(report)
    _scan_absolute_paths(report)
    return True
