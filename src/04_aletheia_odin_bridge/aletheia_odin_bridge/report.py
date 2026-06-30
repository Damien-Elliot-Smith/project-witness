# aletheia_odin_bridge/report.py
# Build the bridge_report dict. Pure; fully determined by inputs.

from aletheia_odin_bridge import versions


def build_report(*, case_id, evidence_id, aletheia_evidence_status,
                 claims, odin_validation_status):
    predicates = [c["predicate"] for c in claims]
    return {
        "bridge_version": versions.BRIDGE_VERSION,
        "case_id": case_id,
        "evidence_id": evidence_id,
        "bridge_status": versions.BRIDGE_CONVERTED,
        "aletheia_evidence_status": aletheia_evidence_status,
        "odin_claim_count": len(claims),
        "odin_validation_status": odin_validation_status,
        "generated_claims": predicates,
        "known_limitations": list(versions.KNOWN_LIMITATIONS),
    }
