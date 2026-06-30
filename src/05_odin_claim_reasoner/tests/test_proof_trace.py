# tests/test_proof_trace.py
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from odin_reasoner.reasoner import build_reasoning  # noqa: E402
from odin_reasoner.canonical import canonical_bytes  # noqa: E402
from odin_reasoner import versions  # noqa: E402
from tests.helpers import (  # noqa: E402
    consistent_set, contradiction_set_object)


class TestProofTrace(unittest.TestCase):
    def test_15_proof_trace_generated_deterministically(self):
        d = consistent_set()
        _, t1, _ = build_reasoning(d)
        _, t2, _ = build_reasoning(d)
        self.assertEqual(canonical_bytes(t1), canonical_bytes(t2))

    def test_trace_has_accepted_step_per_claim(self):
        _, trace, _ = build_reasoning(consistent_set())
        accepted = [s for s in trace["steps"]
                    if s["step_type"] == versions.STEP_CLAIM_ACCEPTED]
        self.assertEqual(len(accepted), 1)
        self.assertEqual(accepted[0]["reason"], versions.REASON_SCHEMA_VALID)
        self.assertEqual(accepted[0]["claim_id"], "claim_001")

    def test_trace_contradiction_step_has_both_ids_and_rule(self):
        _, trace, _ = build_reasoning(contradiction_set_object())
        contra = [s for s in trace["steps"]
                  if s["step_type"] == versions.STEP_CONTRADICTION_DETECTED]
        self.assertEqual(len(contra), 1)
        self.assertEqual(sorted(contra[0]["claim_ids"]),
                         ["claim_001", "claim_002"])
        self.assertEqual(contra[0]["reason"], versions.RULE_DIFFERENT_OBJECT)

    def test_trace_step_ids_sequential(self):
        _, trace, _ = build_reasoning(contradiction_set_object())
        ids = [s["step_id"] for s in trace["steps"]]
        self.assertEqual(ids, ["step_001", "step_002", "step_003"])

    def test_trace_version_and_case_id(self):
        _, trace, _ = build_reasoning(consistent_set())
        self.assertEqual(trace["proof_trace_version"],
                         versions.PROOF_TRACE_VERSION)
        self.assertEqual(trace["case_id"], "case_001")


if __name__ == "__main__":
    unittest.main()
