# tests/test_steps.py
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from evidence_reasoning_demo.steps import (  # noqa: E402
    build_steps, all_completed_steps, STEP_SEQUENCE)
from evidence_reasoning_demo.canonical import canonical_bytes  # noqa: E402
from evidence_reasoning_demo import versions  # noqa: E402


class TestSteps(unittest.TestCase):
    def test_19_steps_canonical_and_deterministic(self):
        s = all_completed_steps("case_001")
        self.assertEqual(canonical_bytes(all_completed_steps("case_001")),
                         canonical_bytes(s))
        self.assertTrue(canonical_bytes(s).endswith(b"\n"))

    def test_six_steps_in_fixed_order(self):
        s = all_completed_steps("case_001")
        self.assertEqual(len(s["steps"]), 6)
        seq = [(x["component"], x["operation"]) for x in s["steps"]]
        self.assertEqual(seq, list(STEP_SEQUENCE))
        ids = [x["step_id"] for x in s["steps"]]
        self.assertEqual(ids, [f"step_{i+1:03d}" for i in range(6)])

    def test_all_completed(self):
        s = all_completed_steps("case_001")
        for x in s["steps"]:
            self.assertEqual(x["status"], versions.STEP_COMPLETED)

    def test_failure_marks_failed_then_skipped(self):
        # Fail at index 2 (bridge convert): steps 0,1 COMPLETED, step 2 FAILED,
        # steps 3-5 SKIPPED_AFTER_FAILURE.
        s = build_steps("case_001", completed_count=2, failed_index=2)
        statuses = [x["status"] for x in s["steps"]]
        self.assertEqual(statuses, [
            versions.STEP_COMPLETED, versions.STEP_COMPLETED,
            versions.STEP_FAILED, versions.STEP_SKIPPED_AFTER_FAILURE,
            versions.STEP_SKIPPED_AFTER_FAILURE,
            versions.STEP_SKIPPED_AFTER_FAILURE])

    def test_only_allowed_step_statuses(self):
        allowed = {versions.STEP_COMPLETED, versions.STEP_FAILED,
                   versions.STEP_SKIPPED_AFTER_FAILURE}
        s = build_steps("case_001", completed_count=1, failed_index=1)
        for x in s["steps"]:
            self.assertIn(x["status"], allowed)


if __name__ == "__main__":
    unittest.main()
