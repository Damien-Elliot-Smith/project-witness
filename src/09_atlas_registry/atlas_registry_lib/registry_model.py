# atlas_registry_lib/registry_model.py
# The canonical Project Witness registry content, built in code so it is always
# canonical and is the single source of truth for the registry file and selfcheck.
# Atlas RECORDS vocabulary already used by the stack; it does not invent behaviour.

from atlas_registry_lib import versions


def _component(cid, name, version, ctype, frozen, description):
    return {
        "component_id": cid, "component_name": name, "component_version": version,
        "component_type": ctype, "frozen_status": frozen,
        "description": description,
    }


COMPONENTS = [
    _component("sentinel_core", "Sentinel Core", "0.2.2", "ACTION_GATE", "FROZEN",
               "Deterministic CREATE_DIRECTORY action gate with replay."),
    _component("histor_lite", "Histor-lite", "0.1.2", "IMPORTER", "FROZEN",
               "Imports a verified Sentinel action run as a case record."),
    _component("case_bundle_v011", "Case Bundle v0.1.1", "0.1.1", "BUNDLER",
               "FROZEN", "Sentinel-only case bundle exporter."),
    _component("coordinator_workflow_v018", "Coordinator Workflow v0.1.8", "0.1.8",
               "COORDINATOR", "FROZEN", "CREATE_CASE_DIRECTORY workflow."),
    _component("companion_cli_v01", "Companion CLI v0.1", "0.1.0", "COMPANION",
               "FROZEN", "Human-facing wrapper for the case-directory workflow."),
    _component("aletheia_evidence_bundle", "Aletheia Evidence Bundle", "0.1.0",
               "EVIDENCE_BUNDLE", "FROZEN",
               "Bundles a local evidence file with integrity metadata."),
    _component("odin_claim_reasoner", "ODIN Claim Reasoner", "0.1.0", "REASONER",
               "FROZEN", "Structural reasoning over presence/integrity claims."),
    _component("aletheia_odin_bridge", "Aletheia -> ODIN Bridge", "0.1.0", "BRIDGE",
               "FROZEN", "Converts a verified Aletheia bundle into ODIN claims."),
    _component("evidence_reasoning_demo", "Evidence Reasoning Demo", "0.1.0",
               "DEMO", "FROZEN",
               "Drives Aletheia -> Bridge -> ODIN as a demonstration."),
    _component("histor_lite_aletheia_importer", "Histor-lite Aletheia Importer",
               "0.1.0", "IMPORTER", "FROZEN",
               "Imports a verified Aletheia evidence bundle as a case record."),
    _component("histor_lite_odin_importer", "Histor-lite ODIN Importer", "0.1.0",
               "IMPORTER", "FROZEN",
               "Imports a verified ODIN reasoning output as a case record."),
    _component("case_bundle_v02", "Case Bundle v0.2", "0.2.0", "BUNDLER", "FROZEN",
               "Packages Sentinel + Aletheia + ODIN case records into one bundle."),
    _component("coordinator_workflow_v02", "Coordinator Workflow v0.2", "0.2.0",
               "COORDINATOR", "FROZEN",
               "Orchestrates the full evidence-and-reasoning case workflow."),
    _component("companion_cli_v02", "Companion CLI v0.2", "0.2.0", "COMPANION",
               "FROZEN", "Human-facing wrapper around Coordinator Workflow v0.2."),
    _component("atlas_registry", "Atlas Registry", "0.1.0", "REGISTRY",
               "IN_PROGRESS",
               "Read-only registry of Project Witness vocabulary and metadata."),
]

WORKFLOW_TYPES = [
    {
        "workflow_type": "CREATE_CASE_DIRECTORY",
        "introduced_by_component": "coordinator_workflow_v018",
        "description": "Create a case directory via the Sentinel action gate.",
        "allowed_statuses": ["WORKFLOW_COMPLETED", "FAILED"],
        "known_limitations": [
            "Records a single CREATE_DIRECTORY action workflow only."],
    },
    {
        "workflow_type": "CREATE_EVIDENCE_REASONING_CASE",
        "introduced_by_component": "coordinator_workflow_v02",
        "description": "Run the full action + evidence + reasoning case workflow.",
        "allowed_statuses": [
            "WORKFLOW_COMPLETED", "FAILED_REQUEST_VALIDATION",
            "FAILED_SENTINEL_CREATE_DIRECTORY", "FAILED_HISTOR_IMPORT_SENTINEL",
            "FAILED_ALETHEIA_BUNDLE_FILE", "FAILED_HISTOR_IMPORT_ALETHEIA",
            "FAILED_BRIDGE_CONVERT", "FAILED_ODIN_REASON",
            "FAILED_HISTOR_IMPORT_ODIN", "FAILED_CASE_BUNDLE_BUILD",
            "FAILED_CASE_BUNDLE_VERIFY", "FAILED_COORDINATOR_VERIFY",
            "FAILED_CASE_ID_MISMATCH", "FAILED_CHECKSUMS_INVALID"],
        "known_limitations": [
            "One evidence file, one reasoning run; no queue or concurrency.",
            "It does not prove evidence contents are true.",
            "It does not prove ODIN claims are true."],
    },
]

ACTION_TYPES = [
    {
        "action_type": "CREATE_DIRECTORY",
        "introduced_by_component": "sentinel_core",
        "description": "Create a single directory under an allowed root.",
        "known_limitations": [
            "The only action type in the roadmap for v0.1.",
            "Deterministic and replayable; not a truth claim."],
    },
]


def _status(name, group, meaning, contexts):
    return {
        "status": name, "status_group": group, "meaning": meaning,
        "truth_claim": False, "allowed_contexts": list(contexts),
    }


STATUSES = [
    _status("PASS_STRICT", "sentinel_statuses",
            "Sentinel replay re-derived identically with no exceptions.",
            ["sentinel_replay"]),
    _status("PASS_WITH_ENVIRONMENTAL_EXCEPTIONS", "sentinel_statuses",
            "Sentinel replay passed with documented environmental exceptions.",
            ["sentinel_replay"]),
    _status("FAIL", "sentinel_statuses",
            "Sentinel replay diverged from the saved run.", ["sentinel_replay"]),
    _status("REPLAY_INCOMPATIBLE", "sentinel_statuses",
            "Sentinel run could not be replayed under the current kernel.",
            ["sentinel_replay"]),
    _status("VERIFIED_PRESENT", "aletheia_statuses",
            "Aletheia confirmed the evidence file is present with matching hashes.",
            ["aletheia_evidence"]),
    _status("CONSISTENT", "odin_reasoning_statuses",
            "ODIN found no structural contradiction among the claims.",
            ["odin_reasoning"]),
    _status("CONTRADICTION_DETECTED", "odin_reasoning_statuses",
            "ODIN found a structural contradiction among the claims.",
            ["odin_reasoning"]),
    _status("INVALID_INPUT", "odin_reasoning_statuses",
            "ODIN input was malformed; not a packageable reasoning outcome.",
            ["odin_reasoning"]),
    _status("CONVERTED", "bridge_statuses",
            "The Bridge converted a verified Aletheia bundle into ODIN claims.",
            ["bridge_convert"]),
    _status("IMPORTED_VERIFIED_ALETHEIA", "histor_import_statuses",
            "Histor-lite recorded a verified Aletheia evidence case.",
            ["histor_import"]),
    _status("IMPORTED_VERIFIED_ODIN", "histor_import_statuses",
            "Histor-lite recorded a verified ODIN reasoning case.",
            ["histor_import"]),
    _status("IMPORTED_VERIFIED_SENTINEL", "histor_import_statuses",
            "Histor-lite recorded a verified Sentinel action case.",
            ["histor_import"]),
    _status("BUNDLED_VERIFIED_CASE", "case_bundle_statuses",
            "Case Bundle packaged the three verified case records.",
            ["case_bundle"]),
    _status("WORKFLOW_COMPLETED", "coordinator_statuses",
            "Coordinator ran every workflow step to completion.",
            ["coordinator_workflow"]),
    _status("COMPANION_COMPLETED", "companion_statuses",
            "Companion completed a wrapped Coordinator workflow.",
            ["companion_run"]),
    _status("COMPLETED", "step_statuses", "A workflow step completed.",
            ["workflow_step"]),
    _status("FAILED", "step_statuses", "A workflow step failed.",
            ["workflow_step"]),
    _status("SKIPPED_AFTER_FAILURE", "step_statuses",
            "A workflow step was skipped after an earlier failure.",
            ["workflow_step"]),
    _status("REGISTRY_VERIFIED", "verification_statuses",
            "Atlas verified the registry is structurally valid.",
            ["atlas_verify"]),
]

CLAIM_PREDICATES = [
    {
        "predicate": "evidence.present",
        "meaning": "An evidence item is present with a recorded hash.",
        "allowed_object_types": ["boolean"], "truth_claim": False,
        "introduced_by_component": "odin_claim_reasoner",
    },
    {
        "predicate": "evidence.integrity_verified",
        "meaning": "An evidence item's stored and recomputed hashes matched.",
        "allowed_object_types": ["boolean"], "truth_claim": False,
        "introduced_by_component": "odin_claim_reasoner",
    },
]

CASE_RECORD_TYPES = [
    {
        "record_type": "sentinel_case",
        "produced_by_component": "histor_lite",
        "required_files": ["case_summary.json", "sentinel_replay_report.txt",
                           "checksums.txt"],
        "description": "A verified Sentinel action case record.",
    },
    {
        "record_type": "aletheia_case",
        "produced_by_component": "histor_lite_aletheia_importer",
        "required_files": ["evidence_case_summary.json",
                           "aletheia_manifest_copy.json",
                           "aletheia_replay_report.txt",
                           "evidence_case_checksums.txt"],
        "description": "A verified Aletheia evidence case record.",
    },
    {
        "record_type": "odin_case",
        "produced_by_component": "histor_lite_odin_importer",
        "required_files": ["odin_case_summary.json",
                           "odin_reasoning_report_copy.json",
                           "odin_proof_trace_copy.json", "odin_claims_copy.json",
                           "odin_replay_report.txt", "odin_case_checksums.txt"],
        "description": "A verified ODIN reasoning case record.",
    },
    {
        "record_type": "case_bundle_v02",
        "produced_by_component": "case_bundle_v02",
        "required_files": ["case_manifest.json", "bundle_checksums.txt",
                           "sentinel_case", "aletheia_case", "odin_case"],
        "description": "A portable bundle of the three verified case records.",
    },
    {
        "record_type": "coordinator_output",
        "produced_by_component": "coordinator_workflow_v02",
        "required_files": ["workflow_request_copy.json", "workflow_report.json",
                           "workflow_steps.json", "workflow_checksums.txt",
                           "case_bundle_v02"],
        "description": "The full output of a Coordinator workflow run.",
    },
    {
        "record_type": "companion_output",
        "produced_by_component": "companion_cli_v02",
        "required_files": ["workflow_request.json", "companion_report.json",
                           "companion_steps.json", "companion_checksums.txt",
                           "coordinator_output"],
        "description": "The full output of a Companion CLI run.",
    },
]


def build_registry() -> dict:
    """Construct the canonical Atlas registry dict (single source of truth)."""
    return {
        "atlas_registry_version": versions.ATLAS_REGISTRY_VERSION,
        "registry_id": versions.REGISTRY_ID,
        "components": COMPONENTS,
        "workflow_types": WORKFLOW_TYPES,
        "action_types": ACTION_TYPES,
        "statuses": STATUSES,
        "claim_predicates": CLAIM_PREDICATES,
        "case_record_types": CASE_RECORD_TYPES,
        "known_limitations": list(versions.KNOWN_LIMITATIONS),
    }
