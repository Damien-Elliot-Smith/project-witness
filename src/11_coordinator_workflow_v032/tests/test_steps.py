from coordinator_v03_lib import steps as steps_mod
from coordinator_v03_lib.errors import STEP_COMPLETED, STEP_FAILED, STEP_SKIPPED
from tests._helpers import TempCase


class TestSteps(TempCase):
    def test_fixed_11_step_order(self):
        ids = [s["step_id"] for s in
               steps_mod.build_steps(steps_mod.all_completed())["steps"]]
        self.assertEqual(ids, ["step_%03d" % i for i in range(1, 12)])

    def test_operations_match_plan(self):
        ops = [s["operation"] for s in
               steps_mod.build_steps(steps_mod.all_completed())["steps"]]
        self.assertEqual(ops, [op for _, op in steps_mod.STEP_PLAN])
        self.assertEqual(ops[0], "ATLAS_VALIDATE_REGISTRY")
        self.assertEqual(ops[10], "COORDINATOR_VERIFY_OUTPUT")

    def test_failure_short_circuit_helper(self):
        st = steps_mod.statuses_with_failure_at(0)
        self.assertEqual(st[0], STEP_FAILED)
        self.assertTrue(all(s == STEP_SKIPPED for s in st[1:]))

    def test_all_completed_length(self):
        self.assertEqual(len(steps_mod.all_completed()), 11)
