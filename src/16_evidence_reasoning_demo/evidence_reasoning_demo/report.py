# evidence_reasoning_demo/report.py
# Build the demo_report dict. Pure; fully determined by inputs.

from evidence_reasoning_demo import versions


def build_report(*, case_id, evidence_id, aletheia_status, bridge_status,
                 odin_reasoning_status, odin_claim_count, generated_claims):
    return {
        "evidence_reasoning_demo_version": versions.DEMO_VERSION,
        "case_id": case_id,
        "evidence_id": evidence_id,
        "demo_status": versions.DEMO_COMPLETED,
        "aletheia_status": aletheia_status,
        "bridge_status": bridge_status,
        "odin_reasoning_status": odin_reasoning_status,
        "odin_claim_count": odin_claim_count,
        "generated_claims": list(generated_claims),
        "verified_outputs": list(versions.SUBFOLDERS),
        "known_limitations": list(versions.KNOWN_LIMITATIONS),
    }
