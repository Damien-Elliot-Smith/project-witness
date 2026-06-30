# tests/test_predicates.py
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from atlas_registry_lib.verifier import verify_registry  # noqa: E402
from atlas_registry_lib.errors import RegistryError  # noqa: E402
from atlas_registry_lib import versions  # noqa: E402
from tests.helpers import write_registry, mutate  # noqa: E402


def _pred(name, truth=False):
    return {"predicate": name, "meaning": "x", "allowed_object_types": ["boolean"],
            "truth_claim": truth, "introduced_by_component": "odin_claim_reasoner"}


class TestPredicates(unittest.TestCase):
    def test_10_duplicate_predicate_refused(self):
        reg = mutate(lambda r: r["claim_predicates"].append(
            dict(r["claim_predicates"][0])))
        with self.assertRaises(RegistryError) as cm:
            verify_registry(write_registry(reg))
        self.assertEqual(cm.exception.registry_status,
                         versions.FAILED_DUPLICATE_ENTRY)

    def test_19_missing_required_predicate_refused(self):
        reg = mutate(lambda r: r["claim_predicates"].__setitem__(
            slice(None), [p for p in r["claim_predicates"]
                          if p["predicate"] != "evidence.present"]))
        with self.assertRaises(RegistryError) as cm:
            verify_registry(write_registry(reg))
        self.assertEqual(cm.exception.reason, "REQUIRED_PREDICATE_MISSING")

    def test_21_predicate_truth_claim_true_refused(self):
        reg = mutate(lambda r: r["claim_predicates"][0].update(truth_claim=True))
        with self.assertRaises(RegistryError) as cm:
            verify_registry(write_registry(reg))
        self.assertEqual(cm.exception.registry_status,
                         versions.FAILED_TRUTH_CLAIM)
        self.assertEqual(cm.exception.reason, "PREDICATE_TRUTH_CLAIM")

    def test_23_truth_like_predicate_refused(self):
        for bad in ("contents.true", "file.authentic", "source.trusted",
                    "statement.proven", "reality.proven"):
            reg = mutate(lambda r, b=bad: r["claim_predicates"].append(_pred(b)))
            with self.assertRaises(RegistryError) as cm:
                verify_registry(write_registry(reg))
            self.assertEqual(cm.exception.registry_status,
                             versions.FAILED_TRUTH_CLAIM)
            self.assertEqual(cm.exception.reason, "PREDICATE_TRUTH_NAME")

    def test_25_required_predicates_present(self):
        r = verify_registry(write_registry(mutate(lambda r: None)))
        names = {p["predicate"] for p in r.registry["claim_predicates"]}
        for pred in versions.REQUIRED_PREDICATES:
            self.assertIn(pred, names)


if __name__ == "__main__":
    unittest.main()
