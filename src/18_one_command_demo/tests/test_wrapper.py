import json
import os

from one_command_demo_lib import engine, checksums
from one_command_demo_lib.errors import (
    ONE_COMMAND_DEMO_COMPLETED, FAILED_CONFIG_INVALID, FAILED_CONNECTED_DEMO_RUN,
    FAILED_CONNECTED_DEMO_VERIFY, FAILED_REQUIRED_STATUS_MISSING)
from one_command_demo_lib.runner import FakeConnectedDemoRunner
from one_command_demo_lib import verifier
from tests._helpers import WrapperCase


class TestWrapper(WrapperCase):
    def _run(self, runner, name="out"):
        tmp, cfg, _ = self.make_config()
        out = self.out_dir(tmp, name)
        status, report = engine.run_wrapper(cfg, out, runner=runner)
        return out, status, report

    def test_valid_demo_output_accepted(self):
        out, status, report = self._run(FakeConnectedDemoRunner(honest=True))
        self.assertEqual(status, ONE_COMMAND_DEMO_COMPLETED)
        self.assertEqual(report["wrapper_status"], ONE_COMMAND_DEMO_COMPLETED)
        self.assertTrue(verifier.verify(out))

    def test_required_output_entries_exact(self):
        out, _, _ = self._run(FakeConnectedDemoRunner(honest=True))
        self.assertEqual(set(os.listdir(out)),
                         {"one_command_demo_report.json",
                          "one_command_demo_steps.json",
                          "one_command_demo_checksums.txt",
                          "connected_demo_output"})

    def test_wrapper_report_canonical(self):
        out, _, _ = self._run(FakeConnectedDemoRunner(honest=True))
        from one_command_demo_lib import canonical
        path = os.path.join(out, checksums.REPORT_FILE)
        with open(path, "rb") as h:
            raw = h.read()
        self.assertEqual(raw, canonical.canonical_bytes(canonical.load_json(path)))

    def test_wrapper_steps_fixed_order(self):
        out, _, _ = self._run(FakeConnectedDemoRunner(honest=True))
        from one_command_demo_lib import canonical
        steps = canonical.load_json(os.path.join(out, checksums.STEPS_FILE))["steps"]
        ids = [s["step_id"] for s in steps]
        self.assertEqual(ids, ["step_00%d" % i for i in range(1, 9)])
        self.assertTrue(all(s["status"] == "COMPLETED" for s in steps))

    def test_invalid_config_refused(self):
        tmp, cfg, _ = self.make_config()
        with open(cfg, "w") as h:
            json.dump({"config_version": "9.9.9"}, h)
        status, _ = engine.run_wrapper(cfg, self.out_dir(tmp),
                                       runner=FakeConnectedDemoRunner())
        self.assertEqual(status, FAILED_CONFIG_INVALID)

    def test_missing_connected_demo_root_refused(self):
        tmp, cfg, root = self.make_config(with_demo_py=False)
        os.remove(os.path.join(root, "connected_demo.py")) if os.path.exists(
            os.path.join(root, "connected_demo.py")) else None
        status, _ = engine.run_wrapper(cfg, self.out_dir(tmp),
                                       runner=FakeConnectedDemoRunner())
        self.assertEqual(status, FAILED_CONNECTED_DEMO_RUN)

    def test_connected_demo_failure_reported_honestly(self):
        out, status, report = self._run(FakeConnectedDemoRunner(honest=False))
        self.assertEqual(status, FAILED_CONNECTED_DEMO_VERIFY)
        self.assertNotEqual(report["wrapper_status"], ONE_COMMAND_DEMO_COMPLETED)

    def test_missing_required_status_refused(self):
        out, status, _ = self._run(FakeConnectedDemoRunner(bad_substatus=True))
        self.assertEqual(status, FAILED_REQUIRED_STATUS_MISSING)

    def test_truth_boundary_invalid_refused(self):
        out, status, _ = self._run(
            FakeConnectedDemoRunner(honest=True, truth_valid=False))
        self.assertEqual(status, "FAILED_TRUTH_BOUNDARY")

    def test_failure_steps_short_circuit(self):
        tmp, cfg, _ = self.make_config()
        with open(cfg, "w") as h:
            json.dump({"config_version": "9.9.9"}, h)
        out = self.out_dir(tmp)
        engine.run_wrapper(cfg, out, runner=FakeConnectedDemoRunner())
        from one_command_demo_lib import canonical
        steps = canonical.load_json(os.path.join(out, checksums.STEPS_FILE))["steps"]
        self.assertEqual(steps[0]["status"], "FAILED")
        self.assertTrue(all(s["status"] == "SKIPPED_AFTER_FAILURE"
                            for s in steps[1:]))
