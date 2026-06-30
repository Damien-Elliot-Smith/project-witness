# odin_reasoner/proof_trace.py
# Build a deterministic proof trace from the validated claims and the detected
# contradictions. Steps are emitted in a fixed order: one CLAIM_ACCEPTED step per
# claim (in claim order), then one CONTRADICTION_DETECTED step per contradiction
# (in detection order). Step ids are sequential and stable.

from odin_reasoner import versions


def build_proof_trace(*, case_id, claims, contradictions):
    steps = []
    n = 0
    for claim in claims:
        n += 1
        steps.append({
            "step_id": f"step_{n:03d}",
            "step_type": versions.STEP_CLAIM_ACCEPTED,
            "claim_id": claim["claim_id"],
            "reason": versions.REASON_SCHEMA_VALID,
        })
    for c in contradictions:
        n += 1
        steps.append({
            "step_id": f"step_{n:03d}",
            "step_type": versions.STEP_CONTRADICTION_DETECTED,
            "claim_ids": list(c["claim_ids"]),
            "reason": c["rule"],
        })
    return {
        "proof_trace_version": versions.PROOF_TRACE_VERSION,
        "case_id": case_id,
        "steps": steps,
    }
