"""Stage runners for the Connected Demo.

RealRunner drives the frozen CLIs via subprocess (the real integration path,
matching how Companion already drives Coordinator). FixtureRunner writes the same
report shapes with no subprocess, so the demo's own selfcheck and unit tests
spawn nothing and need no frozen components.
"""

import os
import subprocess
import sys

from . import canonical


class RealRunner:
    """Drives the frozen Companion, Unified Manifest, Stack Verifier, and Stack
    Selfcheck CLIs by subprocess. Manual integration only; never used by the
    default test suite or selfcheck."""

    def __init__(self, roots, python_exe=None):
        self.roots = roots
        self.python_exe = python_exe or sys.executable

    def _run(self, root, script, args):
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(
            [self.python_exe, "-B", script] + args,
            cwd=os.path.abspath(root), env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return completed.returncode, completed.stdout.decode("utf-8", "replace"), \
            completed.stderr.decode("utf-8", "replace")

    def companion(self, params, out_dir):
        r = self.roots
        args = [
            "create-evidence-case",
            "--case-id", params["case_id"],
            "--evidence-id", params["evidence_id"],
            "--evidence-file", params["evidence_file"],
            "--allowed-root", params["allowed_root"],
            "--case-directory-name", params["case_directory_name"],
            "--coordinator-root", r["coordinator"],
            "--atlas-registry-root", r["atlas_registry"],
            "--sentinel-root", r["sentinel"],
            "--histor-lite-root", r["histor_lite"],
            "--aletheia-root", r["aletheia"],
            "--bridge-root", r["bridge"],
            "--odin-root", r["odin"],
            "--histor-aletheia-root", r["histor_aletheia"],
            "--histor-odin-root", r["histor_odin"],
            "--case-bundle-v02-root", r["case_bundle_v02"],
            "--out", out_dir,
        ]
        return self._run(r["companion"], "companion.py", args)

    def manifest(self, source_run, out_dir):
        return self._run(self.roots["unified_manifest"], "unified_manifest.py",
                         ["build", "--source-type", "companion_v03_output",
                          "--source-run", source_run, "--out", out_dir])

    def stack_verifier(self, source_run, manifest_run, out_dir):
        return self._run(self.roots["stack_verifier"], "stack_verify.py",
                         ["check", "--source-type", "companion_v03_output",
                          "--source-run", source_run, "--manifest-run", manifest_run,
                          "--out", out_dir])

    def stack_selfcheck(self, inventory, stack_verifier_run, out_dir):
        return self._run(self.roots["stack_selfcheck"], "stack_selfcheck.py",
                         ["check", "--inventory", inventory,
                          "--stack-verifier-run", stack_verifier_run,
                          "--out", out_dir])


class FixtureRunner:
    """Writes deterministic report shapes with no subprocess. Used by selfcheck
    and unit tests. honest=False simulates a failing stage."""

    def __init__(self, honest=True):
        self.honest = honest

    def _emit(self, out_dir, name, payload):
        os.makedirs(out_dir, exist_ok=True)
        canonical.write_canonical(os.path.join(out_dir, name), payload)
        return 0, "", ""

    def companion(self, params, out_dir):
        wf = "WORKFLOW_COMPLETED" if self.honest else "WORKFLOW_FAILED"
        comp = "COMPANION_COMPLETED" if self.honest else "COMPANION_FAILED"
        return self._emit(out_dir, "companion_report.json", {
            "case_id": params["case_id"],
            "companion_status": comp,
            "coordinator_workflow_status": wf,
            "atlas_validation_status": "ATLAS_VALIDATED",
        })

    def manifest(self, source_run, out_dir):
        return self._emit(out_dir, "unified_case_manifest.json", {
            "source_status": "SOURCE_VERIFIED" if self.honest else "FAILED_SOURCE"})

    def stack_verifier(self, source_run, manifest_run, out_dir):
        return self._emit(out_dir, "stack_verification_report.json", {
            "source_status": "SOURCE_VERIFIED",
            "stack_verification_status":
                "STACK_VERIFIED" if self.honest else "FAILED_STACK",
            "truth_boundary_valid": True, "atlas_vocabulary_valid": True})

    def stack_selfcheck(self, inventory, stack_verifier_run, out_dir):
        return self._emit(out_dir, "stack_selfcheck_report.json", {
            "stack_selfcheck_status":
                "STACK_SELFCHECK_PASSED" if self.honest else "FAILED_DOCUMENTATION_BOUNDARY",
            "documentation_boundary_status": "DOCUMENTATION_BOUNDARY_VERIFIED",
            "inventory_status": "INVENTORY_VERIFIED"})
