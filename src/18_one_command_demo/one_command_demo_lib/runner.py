"""Connected Demo runners.

RealConnectedDemoRunner drives the frozen Connected Demo v0.1 public CLI by
subprocess. It never edits the frozen package; it only calls `connected_demo.py
run` and `connected_demo.py verify`. FakeConnectedDemoRunner writes the same
report shapes with no subprocess and no frozen components, for the default unit
tests and selfcheck.
"""

import json
import os
import subprocess
import sys

from . import canonical

# connected_demo.py run flags, in the order the frozen CLI expects, mapped from
# the keys of the connected_demo_config JSON.
_RUN_KEYS = (
    "companion_root", "coordinator_root", "atlas_registry_root", "sentinel_root",
    "histor_lite_root", "aletheia_root", "bridge_root", "odin_root",
    "histor_aletheia_root", "histor_odin_root", "case_bundle_v02_root",
    "unified_manifest_root", "stack_verifier_root", "stack_selfcheck_root",
    "case_id", "evidence_id", "evidence_file", "allowed_root",
    "case_directory_name", "inventory",
)


def _flag(key):
    return "--" + key.replace("_", "-")


class RealConnectedDemoRunner:
    def __init__(self, connected_demo_root, demo_config, python_exe=None):
        self.root = os.path.abspath(connected_demo_root)
        self.demo_config = demo_config
        self.python_exe = python_exe or sys.executable

    def _run(self, args):
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(
            [self.python_exe, "-B", "connected_demo.py"] + args,
            cwd=self.root, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return (completed.returncode,
                completed.stdout.decode("utf-8", "replace"),
                completed.stderr.decode("utf-8", "replace"))

    def run_demo(self, demo_out):
        args = ["run"]
        for key in _RUN_KEYS:
            args += [_flag(key), str(self.demo_config[key])]
        args += ["--out", demo_out]
        return self._run(args)

    def verify_demo(self, demo_out):
        return self._run(["verify", "--run", demo_out])


class FakeConnectedDemoRunner:
    """Writes deterministic Connected Demo report shapes. honest=False simulates a
    Connected Demo that does not reach all statuses. No subprocess."""

    def __init__(self, honest=True, truth_valid=True, bad_substatus=False):
        self.honest = honest
        self.truth_valid = truth_valid
        self.bad_substatus = bad_substatus

    def run_demo(self, demo_out):
        os.makedirs(demo_out, exist_ok=True)
        wf = "WORKFLOW_COMPLETED" if self.honest else "WORKFLOW_FAILED"
        demo = "DEMO_COMPLETED" if self.honest else "DEMO_FAILED"
        observed = {
            "companion_status": "COMPANION_COMPLETED" if self.honest else "COMPANION_FAILED",
            "coordinator_workflow_status": wf,
            "atlas_validation_status": "ATLAS_VALIDATED",
            "source_status": "SOURCE_VERIFIED",
            "stack_verification_status": "STACK_VERIFIED" if self.honest else "FAILED_STACK",
            "stack_selfcheck_status": "STACK_SELFCHECK_PASSED",
        }
        # bad_substatus: the demo reports overall DEMO_COMPLETED and verifies, but
        # one required sub-status is wrong. Used to exercise the wrapper's own
        # required-status check (step_006).
        if self.bad_substatus:
            demo = "DEMO_COMPLETED"
            observed["coordinator_workflow_status"] = "WORKFLOW_FAILED"
        canonical.write_canonical(os.path.join(demo_out, "connected_demo_report.json"), {
            "demo_status": demo, "observed_statuses": observed,
            "connected_demo_version": "0.1.0"})
        sv_dir = os.path.join(demo_out, "stack_verifier_output")
        os.makedirs(sv_dir, exist_ok=True)
        canonical.write_canonical(os.path.join(sv_dir, "stack_verification_report.json"), {
            "stack_verification_status": "STACK_VERIFIED",
            "truth_boundary_valid": bool(self.truth_valid),
            "atlas_vocabulary_valid": True})
        return (0, json.dumps({"demo_status": demo}), "")

    def verify_demo(self, demo_out):
        try:
            report = canonical.load_json(
                os.path.join(demo_out, "connected_demo_report.json"))
        except Exception as exc:  # noqa: BLE001
            return (1, "", str(exc))
        ok = report.get("demo_status") == "DEMO_COMPLETED"
        return (0 if ok else 1,
                json.dumps({"demo_status": report.get("demo_status"),
                            "verify_ok": ok}), "")
