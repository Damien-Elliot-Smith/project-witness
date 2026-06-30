# histor_odin_importer/report.py
# Build the odin_case_summary dict and the odin_replay_report.txt text. Both record
# structural reasoning metadata only; neither asserts truth of any claim.

from histor_odin_importer import versions


def build_summary(*, report, trace, claims, claims_sha256, report_sha256,
                  trace_sha256) -> dict:
    """Build the odin_case_summary from a validated, importable ODIN run. ODIN's
    reasoning status is preserved exactly."""
    return {
        "histor_odin_importer_version": versions.IMPORTER_VERSION,
        "case_id": report["case_id"],
        "import_status": versions.IMPORTED_VERIFIED_ODIN,
        "source_component": versions.SOURCE_COMPONENT,
        "source_reasoning_status": report["reasoning_status"],
        "claim_count": report["claim_count"],
        "contradiction_count": report["contradiction_count"],
        "proof_step_count": len(trace["steps"]),
        "source_claims_sha256": claims_sha256,
        "source_reasoning_report_sha256": report_sha256,
        "source_proof_trace_sha256": trace_sha256,
        "known_limitations": list(versions.KNOWN_LIMITATIONS),
    }


def build_replay_report(summary) -> str:
    """Build the plain-text replay report. Records reasoning metadata only and
    states explicitly that no truth claim is made (truth_claim: none)."""
    lines = [
        "ODIN Reasoning Import Report",
        f"import_status: {summary['import_status']}",
        f"case_id: {summary['case_id']}",
        f"source_reasoning_status: {summary['source_reasoning_status']}",
        f"claim_count: {summary['claim_count']}",
        f"contradiction_count: {summary['contradiction_count']}",
        f"proof_step_count: {summary['proof_step_count']}",
        "truth_claim: none",
        "",
        versions.TRUTH_DISCLAIMER,
    ]
    return "\n".join(lines) + "\n"
