"""Coordinator v0.3 runners for Companion.

FakeCoordinatorRunner       -- in-process; builds a faithful Coordinator v0.3
                               output for the default unit tests and selfcheck.
                               No subprocesses, no real frozen components.
SubprocessCoordinatorRunner -- real adapter that calls frozen Coordinator v0.3
                               via subprocess. Used only for the manual
                               integration smoke test; NOT part of the freeze
                               gate (the default suite never constructs it).
"""

import json
import os
import subprocess
import sys
import tempfile

from . import canonical, fixtures


class RunResult:
    def __init__(self, ok, workflow_status, detail=""):
        self.ok = bool(ok)
        self.workflow_status = workflow_status
        self.detail = detail


class FakeCoordinatorRunner:
    def __init__(self, run_ok=True, verify_ok=True,
                 atlas_validation_status="ATLAS_VALIDATED",
                 workflow_status="WORKFLOW_COMPLETED",
                 odin_status="CONSISTENT",
                 case_bundle_status="BUNDLED_VERIFIED_CASE",
                 registry_opts=None):
        self.run_ok = run_ok
        self.verify_ok = verify_ok
        self.atlas_validation_status = atlas_validation_status
        self.workflow_status = workflow_status
        self.odin_status = odin_status
        self.case_bundle_status = case_bundle_status
        self.registry_opts = registry_opts

    def run(self, request, coord_dir):
        fixtures.build_coordinator_output(
            coord_dir, request,
            atlas_validation_status=self.atlas_validation_status,
            workflow_status=self.workflow_status,
            odin_status=self.odin_status,
            case_bundle_status=self.case_bundle_status,
            registry_opts=self.registry_opts)
        ok = self.run_ok and self.workflow_status == "WORKFLOW_COMPLETED"
        return RunResult(ok, self.workflow_status)

    def verify(self, coord_dir):
        return self.verify_ok


class SubprocessCoordinatorRunner:
    """Calls the frozen Coordinator Workflow v0.3 CLI. Manual integration only."""

    def __init__(self, coordinator_root, python_exe=None):
        self.coordinator_root = os.path.abspath(coordinator_root)
        self.python_exe = python_exe or sys.executable

    def _run_cli(self, args):
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [self.python_exe, "-B", "coordinator_v03.py"] + args,
            cwd=self.coordinator_root, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def run(self, request, coord_dir):
        coord_dir = os.path.abspath(coord_dir)
        os.makedirs(os.path.dirname(coord_dir), exist_ok=True)
        # v0.3.1 hygiene repair: the Coordinator only READS --request (it copies
        # it into its own output as workflow_request_copy.json), so Companion
        # does not need to keep the request beside the output. v0.3.0 wrote it as
        # _coordinator_request.json at the Companion-output top level and never
        # removed it, so Companion's own verifier rejected the stray file. Write
        # it to a private temp dir OUTSIDE the output tree and delete it, leaving
        # only allowed top-level entries in the final Companion output.
        tmp_dir = tempfile.mkdtemp(prefix="companion_coord_req_")
        req_path = os.path.join(tmp_dir, "_coordinator_request.json")
        try:
            canonical.write_canonical(req_path, request)
            completed = self._run_cli(
                ["run", "--request", req_path, "--out", coord_dir])
        finally:
            try:
                os.remove(req_path)
            except OSError:
                pass
            try:
                os.rmdir(tmp_dir)
            except OSError:
                pass
        workflow_status = None
        report_path = os.path.join(coord_dir, "workflow_report.json")
        if os.path.isfile(report_path):
            try:
                workflow_status = canonical.load_json(report_path).get("workflow_status")
            except (OSError, ValueError):
                workflow_status = None
        return RunResult(completed.returncode == 0, workflow_status,
                         completed.stderr.decode("utf-8", "replace"))

    def verify(self, coord_dir):
        completed = self._run_cli(["verify", "--run", coord_dir])
        return completed.returncode == 0
