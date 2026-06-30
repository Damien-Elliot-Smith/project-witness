# tests/test_reasoning.py
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from odin_reasoner.reasoner import build_reasoning, reason_to_dir  # noqa: E402
from odin_reasoner.canonical import canonical_bytes  # noqa: E402
from odin_reasoner import versions  # noqa: E402
from tests.helpers import (  # noqa: E402
    claim_set, claim, support, consistent_set, contradiction_set_object,
    contradiction_set_polarity)


class TestReasoning(unittest.TestCase):
    def test_10_consistent_claims_produce_consistent(self):
        report, trace, contradictions = build_reasoning(consistent_set())
        self.assertEqual(report["reasoning_status"], versions.REASONING_CONSISTENT)
        self.assertEqual(report["contradiction_count"], 0)
        self.assertEqual(contradictions, [])
        self.assertEqual(report["claims"][0]["claim_status"],
                         versions.CLAIM_ACCEPTED)
        self.assertEqual(report["claims"][0]["support_status"],
                         versions.SUPPORT_SUPPORTED)

    def test_13_non_contradictory_separate_subjects(self):
        d = claim_set([
            claim("claim_001", subject="evidence:e1", obj=True),
            claim("claim_002", subject="evidence:e2", obj=False,
                  supports=[support("support_002", "b" * 64)]),
        ])
        report, _, _ = build_reasoning(d)
        self.assertEqual(report["reasoning_status"], versions.REASONING_CONSISTENT)

    def test_14_non_contradictory_separate_predicates(self):
        d = claim_set([
            claim("claim_001", predicate="p.one", obj=True),
            claim("claim_002", predicate="p.two", obj=False,
                  supports=[support("support_002", "b" * 64)]),
        ])
        report, _, _ = build_reasoning(d)
        self.assertEqual(report["reasoning_status"], versions.REASONING_CONSISTENT)

    def test_16_report_is_canonical_and_deterministic(self):
        d = consistent_set()
        r1, _, _ = build_reasoning(d)
        r2, _, _ = build_reasoning(d)
        self.assertEqual(canonical_bytes(r1), canonical_bytes(r2))

    def test_17_checksums_file_written(self):
        out = os.path.join(tempfile.mkdtemp(), "odin")
        reason_to_dir(consistent_set(), out)
        for name in (versions.CLAIMS_CANONICAL_NAME,
                     versions.REASONING_REPORT_NAME,
                     versions.PROOF_TRACE_NAME, versions.CHECKSUMS_NAME):
            self.assertTrue(os.path.isfile(os.path.join(out, name)))

    def test_reason_to_dir_consistent(self):
        out = os.path.join(tempfile.mkdtemp(), "odin")
        result = reason_to_dir(consistent_set(), out)
        self.assertEqual(result.reasoning_status, versions.REASONING_CONSISTENT)

    def test_nonempty_output_dir_refused(self):
        out = os.path.join(tempfile.mkdtemp(), "odin")
        os.makedirs(out)
        with open(os.path.join(out, "rogue"), "w") as f:
            f.write("x")
        from odin_reasoner.errors import ValidationError
        with self.assertRaises(ValidationError) as cm:
            reason_to_dir(consistent_set(), out)
        self.assertEqual(cm.exception.reason, "OUTPUT_DIR_NOT_EMPTY")


class TestContradictions(unittest.TestCase):
    def test_11_different_object_contradiction(self):
        report, _, contradictions = build_reasoning(contradiction_set_object())
        self.assertEqual(report["reasoning_status"],
                         versions.REASONING_CONTRADICTION_DETECTED)
        self.assertEqual(report["contradiction_count"], 1)
        self.assertEqual(contradictions[0]["rule"], versions.RULE_DIFFERENT_OBJECT)
        # Both claims marked CONTRADICTED.
        for row in report["claims"]:
            self.assertEqual(row["claim_status"], versions.CLAIM_CONTRADICTED)

    def test_12_opposite_polarity_contradiction(self):
        report, _, contradictions = build_reasoning(contradiction_set_polarity())
        self.assertEqual(report["reasoning_status"],
                         versions.REASONING_CONTRADICTION_DETECTED)
        self.assertEqual(contradictions[0]["rule"],
                         versions.RULE_OPPOSITE_POLARITY)

    def test_bool_and_int_not_equal_objects(self):
        # object True and object 1 must be treated as DIFFERENT objects.
        from odin_reasoner.contradictions import find_contradictions
        claims = [
            {"claim_id": "c1", "subject": "s", "predicate": "p", "object": True,
             "polarity": "AFFIRMED"},
            {"claim_id": "c2", "subject": "s", "predicate": "p", "object": 1,
             "polarity": "AFFIRMED"},
        ]
        cs = find_contradictions(claims)
        self.assertEqual(len(cs), 1)
        self.assertEqual(cs[0]["rule"], versions.RULE_DIFFERENT_OBJECT)

    def test_same_object_same_polarity_no_contradiction(self):
        from odin_reasoner.contradictions import find_contradictions
        claims = [
            {"claim_id": "c1", "subject": "s", "predicate": "p", "object": True,
             "polarity": "AFFIRMED"},
            {"claim_id": "c2", "subject": "s", "predicate": "p", "object": True,
             "polarity": "AFFIRMED"},
        ]
        self.assertEqual(find_contradictions(claims), [])

    def test_contradiction_detection_order_independent(self):
        from odin_reasoner.contradictions import find_contradictions
        a = {"claim_id": "c1", "subject": "s", "predicate": "p", "object": True,
             "polarity": "AFFIRMED"}
        b = {"claim_id": "c2", "subject": "s", "predicate": "p", "object": False,
             "polarity": "AFFIRMED"}
        self.assertEqual(len(find_contradictions([a, b])), 1)
        self.assertEqual(len(find_contradictions([b, a])), 1)


if __name__ == "__main__":
    unittest.main()
