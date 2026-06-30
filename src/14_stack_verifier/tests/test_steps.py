from stack_verifier_lib import steps as steps_mod
from stack_verifier_lib.errors import STEP_FAILED, STEP_SKIPPED, STEP_COMPLETED
from tests._helpers import TempCase


class TestSteps(TempCase):
    def test_fixed_nine_step_order(self):
        obj = steps_mod.build_steps(steps_mod.all_completed())
        ids = [s["step_id"] for s in obj["steps"]]
        self.assertEqual(ids, ["step_%03d" % i for i in range(1, 10)])

    def test_operations(self):
        obj = steps_mod.build_steps(steps_mod.all_completed())
        self.assertEqual(obj["steps"][0]["operation"], "VALIDATE_INPUTS")
        self.assertEqual(obj["steps"][8]["operation"], "VERIFY_STACK_VERIFIER_OUTPUT")

    def test_short_circuit_helper(self):
        st = steps_mod.statuses_with_failure_at(3)
        self.assertEqual(st[:3], [STEP_COMPLETED] * 3)
        self.assertEqual(st[3], STEP_FAILED)
        self.assertTrue(all(s == STEP_SKIPPED for s in st[4:]))
