# case_bundle_v02_lib/manifest.py
# Build the case_manifest dict from the facts extracted by the input verifiers.
# Records status metadata only; never asserts truth.

from case_bundle_v02_lib import versions


def build_manifest(*, case_id, sentinel_facts, aletheia_facts, odin_facts) -> dict:
    return {
        "case_bundle_version": versions.CASE_BUNDLE_VERSION,
        "case_id": case_id,
        "bundle_status": versions.BUNDLED_VERIFIED_CASE,
        "included_records": list(versions.INCLUDED_RECORDS),
        "sentinel": {
            "source_component": sentinel_facts["source_component"],
            "case_status": sentinel_facts["case_status"],
            "action_status": sentinel_facts["action_status"],
        },
        "aletheia": {
            "source_component": aletheia_facts["source_component"],
            "import_status": aletheia_facts["import_status"],
            "source_evidence_status": aletheia_facts["source_evidence_status"],
        },
        "odin": {
            "source_component": odin_facts["source_component"],
            "import_status": odin_facts["import_status"],
            "source_reasoning_status": odin_facts["source_reasoning_status"],
            "claim_count": odin_facts["claim_count"],
            "contradiction_count": odin_facts["contradiction_count"],
        },
        "known_limitations": list(versions.KNOWN_LIMITATIONS),
    }
