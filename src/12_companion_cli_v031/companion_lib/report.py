"""Companion v0.3 report construction (canonical JSON)."""

from . import canonical, versions

KNOWN_LIMITATIONS = (
    "Companion CLI v0.3 is a human-facing wrapper around Coordinator Workflow v0.3.",
    "Atlas is used as a read-only vocabulary boundary through Coordinator v0.3.",
    "Companion CLI v0.3 does not modify Atlas.",
    "Companion CLI v0.3 does not add Atlas terms.",
    "Companion CLI v0.3 does not prove evidence contents are true.",
    "Companion CLI v0.3 does not prove ODIN claims are true.",
    "Companion CLI v0.3 does not interpret evidence contents.",
    "Companion CLI v0.3 does not use natural language.",
    "Companion CLI v0.3 does not use an LLM.",
    "Companion CLI v0.3 does not sign or externally anchor outputs.",
    "Companion CLI v0.3 supports one workflow at a time.",
)


def build_report(fields):
    report = {
        "companion_cli_version": versions.COMPANION_CLI_VERSION,
        "command": "create-evidence-case",
        "coordinator_output_path": "coordinator_output",
        "known_limitations": list(KNOWN_LIMITATIONS),
    }
    report.update(fields)
    return report


def write_report(path, report):
    canonical.write_canonical(path, report)
