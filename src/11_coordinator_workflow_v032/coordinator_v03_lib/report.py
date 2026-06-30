"""Coordinator v0.3 workflow report construction (canonical JSON)."""

from . import canonical, versions

KNOWN_LIMITATIONS = (
    "Coordinator Workflow v0.3 validates vocabulary against Atlas Registry v0.1.",
    "Atlas validation does not prove evidence contents are true.",
    "Atlas validation does not prove ODIN claims are true.",
    "Coordinator Workflow v0.3 does not use natural language or LLMs.",
    "Coordinator Workflow v0.3 does not sign or externally anchor outputs.",
    "Coordinator Workflow v0.3 supports one workflow at a time.",
)


def build_report(fields):
    report = {
        "coordinator_workflow_version": versions.COORDINATOR_WORKFLOW_VERSION,
        "known_limitations": list(KNOWN_LIMITATIONS),
    }
    report.update(fields)
    return report


def write_report(path, report):
    canonical.write_canonical(path, report)
