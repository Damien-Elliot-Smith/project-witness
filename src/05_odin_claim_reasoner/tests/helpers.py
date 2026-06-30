# tests/helpers.py
import copy
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

_SHA = "a" * 64
_SHB = "b" * 64


def support(sid="support_001", sha=_SHA, source_id="evidence_001"):
    return {
        "support_id": sid,
        "source_component": "aletheia_evidence_bundle",
        "source_id": source_id,
        "source_sha256": sha,
    }


def claim(claim_id="claim_001", subject="evidence:evidence_001",
          predicate="evidence.integrity_verified", obj=True,
          polarity="AFFIRMED", supports=None):
    return {
        "claim_id": claim_id,
        "subject": subject,
        "predicate": predicate,
        "object": obj,
        "polarity": polarity,
        "support": supports if supports is not None else [support()],
    }


def claim_set(claims=None, case_id="case_001"):
    return {
        "odin_claim_set_version": "0.1.0",
        "case_id": case_id,
        "claims": claims if claims is not None else [claim()],
    }


def consistent_set():
    return claim_set([claim("claim_001")])


def contradiction_set_object():
    return claim_set([
        claim("claim_001", obj=True),
        claim("claim_002", obj=False, supports=[support("support_002", _SHB)]),
    ])


def contradiction_set_polarity():
    return claim_set([
        claim("claim_001", subject="case:case_001",
              predicate="case_directory.exists", obj=True, polarity="AFFIRMED"),
        claim("claim_002", subject="case:case_001",
              predicate="case_directory.exists", obj=True, polarity="DENIED",
              supports=[support("support_002", _SHB)]),
    ])


def deep(obj):
    return copy.deepcopy(obj)
