# tests/test_kernel_faults.py
# Fault-injection and hostile-input tests for the kernel.
#
# 1. ERROR_POSTCONDITION_FAILED: forced by patching the directory check the
#    kernel performs after mkdir, simulating an OS where mkdir "succeeds" but
#    the target is not a directory. v0.1.0 documented this branch as
#    covered-by-construction only; v0.1.1 covers it by injected fault.
# 2. ERROR_EXECUTION_FAILED: forced by patching the executor to raise.
# 3. Non-JSON-native Python objects passed to Kernel.process() must produce a
#    controlled BLOCK_SCHEMA_INVALID receipt (with a sanitised record), never
#    an uncontrolled crash inside receipt construction.

import json
import os
import shutil
import unittest
from unittest import mock

from sentinel_core.errors import PersistenceFailure
from sentinel_core.reason_codes import (
    ERROR, BLOCK, ERROR_POSTCONDITION_FAILED, ERROR_EXECUTION_FAILED,
    BLOCK_SCHEMA_INVALID,
)
from tests.helpers import make_request, new_kernel, temp_root, temp_runs


class TestKernelFaults(unittest.TestCase):
    def setUp(self):
        self.root = temp_root()
        self.runs = temp_runs()
        self.kernel, self.run_path = new_kernel("faults", self.root, self.runs)

    def tearDown(self):
        for d in (self.root, self.runs):
            shutil.rmtree(d, ignore_errors=True)

    def test_postcondition_failure_produces_controlled_error(self):
        # Simulate: mkdir returns success, but the target is not a directory
        # afterwards. The injection is surgical: os.path.isdir lies ONLY about
        # the target, so the path policy's earlier root/parent checks (which
        # also use isdir) still see the truth and the request reaches
        # execution. The kernel must emit ERROR_POSTCONDITION_FAILED with
        # executed=False, persist it, and keep the session open.
        real_isdir = os.path.isdir

        def lying_isdir(p):
            if os.path.basename(p) == "phantom":
                return False
            return real_isdir(p)

        with mock.patch("sentinel_core.kernel.os.path.isdir", side_effect=lying_isdir):
            receipt = self.kernel.process(make_request("F-1", "phantom"))
        self.assertEqual(receipt.decision, ERROR)
        self.assertEqual(receipt.reason_code, ERROR_POSTCONDITION_FAILED)
        self.assertFalse(receipt.executed)
        self.assertEqual(self.kernel.session_state, "OPEN")
        # The receipt was persisted like any other.
        with open(self.run_path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["receipts"][-1]["reason_code"], ERROR_POSTCONDITION_FAILED)

    def test_execution_failure_produces_controlled_error(self):
        # Simulate mkdir raising at execution time (e.g. a race or EACCES).
        with mock.patch("sentinel_core.kernel.execute_create_directory",
                        side_effect=PersistenceFailure("injected mkdir failure")):
            receipt = self.kernel.process(make_request("F-2", "racey"))
        self.assertEqual(receipt.decision, ERROR)
        self.assertEqual(receipt.reason_code, ERROR_EXECUTION_FAILED)
        self.assertFalse(receipt.executed)
        self.assertFalse(os.path.exists(os.path.join(self.root, "racey")))
        self.assertEqual(self.kernel.session_state, "OPEN")

    def test_request_containing_set_is_recorded_safely(self):
        bad = make_request("F-3", "x")
        bad["preconditions"] = {"target_absent"}  # a set: schema-invalid AND uncanonicalisable
        receipt = self.kernel.process(bad)
        self.assertEqual(receipt.decision, BLOCK)
        self.assertEqual(receipt.reason_code, BLOCK_SCHEMA_INVALID)
        # The sanitised record notes the unrepresentable value instead of crashing.
        self.assertIn("unrepresentable", json.dumps(receipt.request))

    def test_arbitrary_object_is_recorded_safely(self):
        class Weird:
            def __repr__(self):
                return "<Weird instance>"
        receipt = self.kernel.process(Weird())
        self.assertEqual(receipt.reason_code, BLOCK_SCHEMA_INVALID)
        self.assertIn("unrepresentable", json.dumps(receipt.request))

    def test_nan_and_non_str_keys_recorded_safely(self):
        bad = make_request("F-4", "x")
        bad["dry_run"] = float("nan")
        bad[42] = "non-str key"
        receipt = self.kernel.process(bad)
        self.assertEqual(receipt.reason_code, BLOCK_SCHEMA_INVALID)
        record = json.dumps(receipt.request)
        self.assertIn("unrepresentable", record)
        self.assertIn("non-str key", record)

    def test_hostile_object_run_still_replays(self):
        # A run containing sanitised hostile records must verify and replay.
        from sentinel_core.replay import replay_from_path
        self.kernel.process({"weird": {1, 2, 3}})
        self.kernel.process(make_request("OK", "legit"))
        self.kernel.close_session()
        ok, report = replay_from_path(self.run_path)
        self.assertTrue(ok, report)


if __name__ == "__main__":
    unittest.main()
