"""Connected Demo engine.

Runs the four top-level stages in fixed order, short-circuiting on the first
stage that does not reach its required terminal status, then assembles a demo
report. The orchestrator only reads the JSON each frozen CLI already writes; it
copies no evidence contents and makes no truth claim.
"""

import os

from . import canonical
from .canonical import DemoError, require

REPORT_FILE = "connected_demo_report.json"
CHECKSUMS_FILE = "connected_demo_checksums.txt"

_COMPANION_REPORT = "companion_report.json"
_MANIFEST_REPORT = "unified_case_manifest.json"
_VERIFIER_REPORT = "stack_verification_report.json"
_SELFCHECK_REPORT = "stack_selfcheck_report.json"

_STAGE_ORDER = ("companion", "manifest", "stack_verifier", "stack_selfcheck")


def _status(out_dir, name, key):
    path = os.path.join(out_dir, name)
    require(os.path.isfile(path), "stage did not write %s" % name)
    return canonical.load_json(path).get(key)


def run_demo(params, runner, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    inventory = params["inventory"]

    companion_out = os.path.join(out_dir, "companion_output")
    manifest_out = os.path.join(out_dir, "manifest_output")
    verifier_out = os.path.join(out_dir, "stack_verifier_output")
    selfcheck_out = os.path.join(out_dir, "stack_selfcheck_output")

    observed = {}
    stages = []

    def record(stage, ok, detail):
        stages.append({"stage": stage, "ok": bool(ok), "detail": detail})

    # Stage 1: Companion (drives Coordinator v0.3.2, Atlas validation, the full
    # lower stack). Yields COMPANION_COMPLETED, WORKFLOW_COMPLETED, ATLAS_VALIDATED.
    rc, _, err = runner.companion(params, companion_out)
    require(rc == 0, "companion stage failed: %s" % err.strip()[:200])
    observed["companion_status"] = _status(companion_out, _COMPANION_REPORT, "companion_status")
    observed["coordinator_workflow_status"] = _status(companion_out, _COMPANION_REPORT, "coordinator_workflow_status")
    observed["atlas_validation_status"] = _status(companion_out, _COMPANION_REPORT, "atlas_validation_status")
    record("companion", observed["companion_status"] == "COMPANION_COMPLETED", observed["companion_status"])

    # Stage 2: Unified Case Manifest (SOURCE_VERIFIED).
    rc, _, err = runner.manifest(companion_out, manifest_out)
    require(rc == 0, "manifest stage failed: %s" % err.strip()[:200])
    observed["source_status"] = _status(manifest_out, _MANIFEST_REPORT, "source_status")
    record("manifest", observed["source_status"] == "SOURCE_VERIFIED", observed["source_status"])

    # Stage 3: Stack Verifier (STACK_VERIFIED).
    rc, _, err = runner.stack_verifier(companion_out, manifest_out, verifier_out)
    require(rc == 0, "stack verifier stage failed: %s" % err.strip()[:200])
    observed["stack_verification_status"] = _status(verifier_out, _VERIFIER_REPORT, "stack_verification_status")
    record("stack_verifier", observed["stack_verification_status"] == "STACK_VERIFIED",
           observed["stack_verification_status"])

    # Stage 4: Stack Selfcheck v0.1.2 (STACK_SELFCHECK_PASSED), cross-checking the
    # Stack Verifier output.
    rc, _, err = runner.stack_selfcheck(inventory, verifier_out, selfcheck_out)
    require(rc == 0, "stack selfcheck stage failed: %s" % err.strip()[:200])
    observed["stack_selfcheck_status"] = _status(selfcheck_out, _SELFCHECK_REPORT, "stack_selfcheck_status")
    record("stack_selfcheck", observed["stack_selfcheck_status"] == "STACK_SELFCHECK_PASSED",
           observed["stack_selfcheck_status"])

    all_ok = all(observed.get(key) == expected
                 for key, expected in canonical.REQUIRED.items())
    demo_status = canonical.DEMO_COMPLETED if all_ok else canonical.DEMO_FAILED

    report = {
        "connected_demo_version": canonical.CONNECTED_DEMO_VERSION,
        "demo_status": demo_status,
        "case_id": params["case_id"],
        "evidence_id": params["evidence_id"],
        "observed_statuses": observed,
        "stages": stages,
        "required_statuses": canonical.REQUIRED,
    }
    canonical.write_canonical(os.path.join(out_dir, REPORT_FILE), report)
    _write_checksums(out_dir)
    return report


def _write_checksums(out_dir):
    import hashlib
    lines = []
    path = os.path.join(out_dir, REPORT_FILE)
    with open(path, "rb") as handle:
        digest = hashlib.sha256(handle.read()).hexdigest()
    lines.append("%s  %s" % (digest, REPORT_FILE))
    canonical.atomic_write_bytes(os.path.join(out_dir, CHECKSUMS_FILE),
                                 ("\n".join(lines) + "\n").encode("utf-8"))
