# tests/test_contradictions.py
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from odin_reasoner.contradictions import find_contradictions  # noqa: E402
from odin_reasoner import versions  # noqa: E402


def _c(cid, subject, predicate, obj, polarity):
    return {"claim_id": cid, "subject": subject, "predicate": predicate,
            "object": obj, "polarity": polarity}


class TestContradictionRules(unittest.TestCase):
    def test_different_object_rule(self):
        cs = find_contradictions([
            _c("c1", "s", "p", "x", "AFFIRMED"),
            _c("c2", "s", "p", "y", "AFFIRMED"),
        ])
        self.assertEqual(cs, [{"claim_ids": ["c1", "c2"],
                               "rule": versions.RULE_DIFFERENT_OBJECT}])

    def test_opposite_polarity_rule(self):
        cs = find_contradictions([
            _c("c1", "s", "p", "x", "AFFIRMED"),
            _c("c2", "s", "p", "x", "DENIED"),
        ])
        self.assertEqual(cs[0]["rule"], versions.RULE_OPPOSITE_POLARITY)

    def test_different_object_takes_precedence(self):
        # Different object AND different polarity -> reported as different object.
        cs = find_contradictions([
            _c("c1", "s", "p", "x", "AFFIRMED"),
            _c("c2", "s", "p", "y", "DENIED"),
        ])
        self.assertEqual(cs[0]["rule"], versions.RULE_DIFFERENT_OBJECT)

    def test_three_way_pairs(self):
        # Three mutually different objects -> three pairwise contradictions.
        cs = find_contradictions([
            _c("c1", "s", "p", 1, "AFFIRMED"),
            _c("c2", "s", "p", 2, "AFFIRMED"),
            _c("c3", "s", "p", 3, "AFFIRMED"),
        ])
        self.assertEqual(len(cs), 3)
        self.assertEqual([c["claim_ids"] for c in cs],
                         [["c1", "c2"], ["c1", "c3"], ["c2", "c3"]])

    def test_no_contradiction_across_subjects(self):
        cs = find_contradictions([
            _c("c1", "s1", "p", True, "AFFIRMED"),
            _c("c2", "s2", "p", False, "AFFIRMED"),
        ])
        self.assertEqual(cs, [])

    def test_null_vs_false_distinguished(self):
        cs = find_contradictions([
            _c("c1", "s", "p", None, "AFFIRMED"),
            _c("c2", "s", "p", False, "AFFIRMED"),
        ])
        self.assertEqual(len(cs), 1)
        self.assertEqual(cs[0]["rule"], versions.RULE_DIFFERENT_OBJECT)

    def test_string_objects_equal_no_contradiction(self):
        cs = find_contradictions([
            _c("c1", "s", "p", "same", "AFFIRMED"),
            _c("c2", "s", "p", "same", "AFFIRMED"),
        ])
        self.assertEqual(cs, [])


if __name__ == "__main__":
    unittest.main()
