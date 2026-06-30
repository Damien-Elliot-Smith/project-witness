# aletheia_odin_bridge/claim_builder.py
# Build the ODIN claim set from an Aletheia manifest. ONLY integrity/presence
# claims are generated; a guard rejects any forbidden (truth-like) predicate so a
# future edit can never silently introduce one.

from aletheia_odin_bridge.errors import require, BridgeError
from aletheia_odin_bridge import versions


def _assert_allowed_predicate(predicate):
    require(predicate in versions.ALLOWED_PREDICATES,
            f"refusing to generate non-allowed predicate {predicate!r}",
            BridgeError)
    low = predicate.lower()
    for token in versions.FORBIDDEN_PREDICATE_TOKENS:
        require(token not in low,
                f"refusing to generate truth-like predicate {predicate!r} "
                f"(contains {token!r})", BridgeError)


def build_claims(manifest) -> dict:
    """Build the ODIN claim set (exactly two integrity/presence claims) from a
    validated, VERIFIED_PRESENT Aletheia manifest."""
    evidence_id = manifest["evidence_id"]
    case_id = manifest["case_id"]
    sha = manifest["bundled_file_sha256"]
    subject = f"evidence:{evidence_id}"

    def support(sid):
        return {
            "support_id": sid,
            "source_component": versions.SOURCE_COMPONENT,
            "source_id": evidence_id,
            "source_sha256": sha,
        }

    def claim(cid, predicate, sid):
        _assert_allowed_predicate(predicate)
        return {
            "claim_id": cid,
            "subject": subject,
            "predicate": predicate,
            "object": True,
            "polarity": "AFFIRMED",
            "support": [support(sid)],
        }

    claims = [
        claim("claim_001", versions.PREDICATE_PRESENT, "support_001"),
        claim("claim_002", versions.PREDICATE_INTEGRITY_VERIFIED, "support_002"),
    ]
    return {
        "odin_claim_set_version": versions.ODIN_CLAIM_SET_VERSION,
        "case_id": case_id,
        "claims": claims,
    }
