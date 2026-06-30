from atlas_release_gate_lib import steps as steps_mod
from atlas_release_gate_lib.errors import (
    STEP_COMPLETED, STEP_FAILED, STEP_SKIPPED)
from tests._helpers import TempCase


class TestSteps(TempCase):
    def test_fixed_step_order(self):
        ids = [s["step_id"] for s in
               steps_mod.build_steps(steps_mod.all_completed())["steps"]]
        self.assertEqual(ids, ["step_001", "step_002", "step_003", "step_004",
                               "step_005", "step_006", "step_007", "step_008",
                               "step_009"])

    def test_failure_short_circuit(self):
        statuses = steps_mod.statuses_with_failure_at(3)
        self.assertEqual(statuses[:3], [STEP_COMPLETED] * 3)
        self.assertEqual(statuses[3], STEP_FAILED)
        self.assertTrue(all(s == STEP_SKIPPED for s in statuses[4:]))

    def test_all_completed_length(self):
        self.assertEqual(len(steps_mod.all_completed()), len(steps_mod.STEP_PLAN))

    def test_operations_match_plan(self):
        ops = [s["operation"] for s in
               steps_mod.build_steps(steps_mod.all_completed())["steps"]]
        self.assertEqual(ops, [op for _, op in steps_mod.STEP_PLAN])
