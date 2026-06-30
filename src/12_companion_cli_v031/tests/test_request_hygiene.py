"""Tests for the v0.3.1 coordinator request-file hygiene repair.

v0.3.0's SubprocessCoordinatorRunner wrote `_coordinator_request.json` into the
Companion-output top level and never removed it, so Companion's own verifier
rejected the stray file (companion_status = FAILED_COMPANION_VERIFY). v0.3.1
writes that request to a private temp dir outside the output and deletes it.

These tests drive the REAL run()/verify() request-file hygiene path while
simulating the frozen Coordinator in-process, so the default suite spawns no
subprocess and needs no real frozen component.
"""

import os

from companion_lib import engine, verifier, canonical, fixtures
from companion_lib.coordinator_runner import SubprocessCoordinatorRunner
from companion_lib.errors import COMPANION_COMPLETED
from companion_lib.verifier import VerifyError
from tests._helpers import TempCase


class _Completed:
    def __init__(self, returncode):
        self.returncode = returncode
        self.stderr = b""


class _StubSubprocessRunner(SubprocessCoordinatorRunner):
    """Real SubprocessCoordinatorRunner request-file hygiene, but the frozen
    Coordinator CLI is simulated in-process (no subprocess)."""

    def __init__(self, companion_out):
        super().__init__(coordinator_root=companion_out)
        self.companion_out = companion_out
        self.req_paths = []
        self.req_existed_during_run = []

    def _run_cli(self, args):
        if args[0] == "run":
            req = args[args.index("--request") + 1]
            out = args[args.index("--out") + 1]
            self.req_paths.append(req)
            self.req_existed_during_run.append(os.path.isfile(req))
            request = canonical.load_json(req)
            fixtures.build_coordinator_output(out, request)
        return _Completed(0)


class TestRequestHygiene(TempCase):
    def _run(self):
        out = self.params()["out"]
        runner = _StubSubprocessRunner(out)
        oc = engine.create_evidence_case(self.params(), runner)
        return out, runner, oc

    def test_companion_completes_after_real_coordinator(self):
        out, runner, oc = self._run()
        self.assertEqual(oc.companion_status, COMPANION_COMPLETED)

    def test_no_coordinator_request_left_at_top_level(self):
        out, runner, oc = self._run()
        self.assertNotIn("_coordinator_request.json", os.listdir(out))

    def test_request_written_outside_output_and_cleaned_up(self):
        out, runner, oc = self._run()
        self.assertTrue(runner.req_paths, "coordinator run was never invoked")
        for req in runner.req_paths:
            # the request existed while the Coordinator ran ...
            self.assertTrue(all(runner.req_existed_during_run))
            # ... lived OUTSIDE the Companion output tree ...
            self.assertFalse(
                os.path.abspath(req).startswith(os.path.abspath(out) + os.sep))
            # ... and was removed afterwards.
            self.assertFalse(os.path.exists(req))

    def test_companion_verify_passes_after_real_completion(self):
        out, runner, oc = self._run()
        # raises VerifyError on any failure
        verifier.verify(out)

    def test_only_allowed_top_level_entries_remain(self):
        out, runner, oc = self._run()
        allowed = {"workflow_request.json", "companion_report.json",
                   "companion_steps.json", "companion_checksums.txt",
                   "coordinator_output"}
        self.assertEqual(set(os.listdir(out)) - allowed, set())

    def test_unknown_top_level_file_still_refused(self):
        out, runner, oc = self._run()
        # the verifier must still reject a stray top-level file (no weakening)
        canonical.atomic_write_bytes(
            os.path.join(out, "_coordinator_request.json"), b"{}")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_unrelated_unknown_top_level_file_refused(self):
        out, runner, oc = self._run()
        canonical.atomic_write_bytes(os.path.join(out, "stray.json"), b"{}")
        with self.assertRaises(VerifyError):
            verifier.verify(out)
