# odin_reasoner/aletheia_import.py
# Convert an Aletheia Evidence Bundle manifest into structured ODIN integrity
# claims. It creates claims ONLY about preservation/presence and integrity — never
# about the truth of the file's contents. Tiny and deterministic.

import json
import os

from odin_reasoner.errors import require, ImportError_
from odin_reasoner.validation import is_valid_sha256, is_safe_id
from odin_reasoner import versions

_REQUIRED_MANIFEST_FIELDS = ("evidence_id", "case_id", "evidence_status",
                             "bundled_file_sha256")
_VERIFIED_PRESENT = "VERIFIED_PRESENT"


def build_claims_from_manifest(manifest) -> dict:
    """Build an ODIN claim set from an Aletheia manifest dict. Raises
    ImportError_ if the manifest is unusable or not VERIFIED_PRESENT."""
    require(isinstance(manifest, dict), "manifest must be a JSON object",
            ImportError_, reason="MANIFEST_NOT_OBJECT")
    for f in _REQUIRED_MANIFEST_FIELDS:
        require(f in manifest, f"manifest missing field {f!r}",
                ImportError_, reason="MANIFEST_FIELD_MISSING")

    require(manifest["evidence_status"] == _VERIFIED_PRESENT,
            f"manifest evidence_status {manifest['evidence_status']!r} is not "
            f"{_VERIFIED_PRESENT}; refusing to import",
            ImportError_, reason="MANIFEST_NOT_VERIFIED_PRESENT")

    evidence_id = manifest["evidence_id"]
    case_id = manifest["case_id"]
    sha = manifest["bundled_file_sha256"]
    require(is_safe_id(evidence_id), f"unsafe evidence_id {evidence_id!r}",
            ImportError_, reason="UNSAFE_EVIDENCE_ID")
    require(is_safe_id(case_id), f"unsafe case_id {case_id!r}",
            ImportError_, reason="UNSAFE_CASE_ID")
    require(is_valid_sha256(sha), f"invalid bundled_file_sha256 {sha!r}",
            ImportError_, reason="INVALID_SHA256")

    subject = f"evidence:{evidence_id}"
    support = [{
        "support_id": "support_001",
        "source_component": "aletheia_evidence_bundle",
        "source_id": evidence_id,
        "source_sha256": sha,
    }]

    # ONLY presence + integrity claims. No claim about contents being true.
    claims = [
        {
            "claim_id": "claim_001",
            "subject": subject,
            "predicate": "evidence.present",
            "object": True,
            "polarity": versions.POLARITY_AFFIRMED,
            "support": [dict(support[0])],
        },
        {
            "claim_id": "claim_002",
            "subject": subject,
            "predicate": "evidence.integrity_verified",
            "object": True,
            "polarity": versions.POLARITY_AFFIRMED,
            "support": [dict(support[0])],
        },
    ]
    return {
        "odin_claim_set_version": versions.ODIN_CLAIM_SET_VERSION,
        "case_id": case_id,
        "claims": claims,
    }


def import_manifest_file(manifest_path) -> dict:
    require(os.path.isfile(manifest_path),
            f"manifest file not found: {manifest_path!r}",
            ImportError_, reason="MANIFEST_MISSING")
    try:
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as e:  # noqa: BLE001
        raise ImportError_("MANIFEST_MALFORMED",
                           f"manifest is not valid JSON: {e}")
    return build_claims_from_manifest(manifest)
