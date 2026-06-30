# histor_aletheia_importer/report.py
# Build the evidence_case_summary dict and the aletheia_replay_report.txt text.
# Both record integrity metadata only; neither asserts truth of contents.

from histor_aletheia_importer import versions


def build_summary(*, manifest, manifest_sha256) -> dict:
    """Build the evidence_case_summary from a validated, VERIFIED_PRESENT
    manifest. The Aletheia integrity status is preserved exactly."""
    return {
        "histor_aletheia_importer_version": versions.IMPORTER_VERSION,
        "case_id": manifest["case_id"],
        "evidence_id": manifest["evidence_id"],
        "import_status": versions.IMPORTED_VERIFIED_ALETHEIA,
        "source_component": versions.SOURCE_COMPONENT,
        "source_evidence_status": manifest["evidence_status"],
        "source_file_name": manifest["source_file_name"],
        "source_file_size_bytes": manifest["source_file_size_bytes"],
        "source_file_sha256": manifest["source_file_sha256"],
        "bundled_file_sha256": manifest["bundled_file_sha256"],
        "source_bundle_manifest_sha256": manifest_sha256,
        "known_limitations": list(versions.KNOWN_LIMITATIONS),
    }


def build_replay_report(summary) -> str:
    """Build the plain-text replay report. Records integrity metadata only and
    states explicitly that no truth claim is made (truth_claim: none)."""
    lines = [
        "Aletheia Evidence Bundle Import Report",
        f"import_status: {summary['import_status']}",
        f"case_id: {summary['case_id']}",
        f"evidence_id: {summary['evidence_id']}",
        f"source_evidence_status: {summary['source_evidence_status']}",
        f"source_file_sha256: {summary['source_file_sha256']}",
        f"bundled_file_sha256: {summary['bundled_file_sha256']}",
        "truth_claim: none",
        "",
        versions.TRUTH_DISCLAIMER,
    ]
    return "\n".join(lines) + "\n"
