from companion_lib import steps as steps_mod
from companion_lib.errors import STEP_FAILED, STEP_SKIPPED, STEP_COMPLETED
from tests._helpers import TempCase


class TestSteps(TempCase):
    def test_fixed_seven_step_order(self):
        obj = steps_mod.build_steps(steps_mod.all_completed(), "case_x")
        ids = [s["step_id"] for s in obj["steps"]]
        self.assertEqual(ids, ["step_%03d" % i for i in range(1, 8)])

    def test_components_and_ops(self):
        obj = steps_mod.build_steps(steps_mod.all_completed(), "case_x")
        self.assertEqual(obj["steps"][0]["component"], "companion_cli")
        self.assertEqual(obj["steps"][2]["component"], "coordinator_workflow_v03")
        self.assertEqual(obj["steps"][2]["operation"], "RUN_ATLAS_VALIDATED_WORKFLOW")

    def test_failure_short_circuit_helper(self):
        st = steps_mod.statuses_with_failure_at(2)
        self.assertEqual(st[:2], [STEP_COMPLETED, STEP_COMPLETED])
        self.assertEqual(st[2], STEP_FAILED)
        self.assertTrue(all(s == STEP_SKIPPED for s in st[3:]))
