# tests/test_honesty.py
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from atlas_registry_lib.verifier import verify_registry  # noqa: E402
from atlas_registry_lib import versions  # noqa: E402
from tests.helpers import REGISTRY_PATH  # noqa: E402


class TestHonesty(unittest.TestCase):
    def test_all_statuses_truth_claim_false(self):
        r = verify_registry(REGISTRY_PATH)
        for s in r.registry["statuses"]:
            self.assertIs(s["truth_claim"], False, s["status"])

    def test_all_predicates_truth_claim_false(self):
        r = verify_registry(REGISTRY_PATH)
        for p in r.registry["claim_predicates"]:
            self.assertIs(p["truth_claim"], False, p["predicate"])

    def test_no_truth_like_status_names(self):
        r = verify_registry(REGISTRY_PATH)
        names = {s["status"].upper() for s in r.registry["statuses"]}
        self.assertEqual(names & versions.FORBIDDEN_STATUS_NAMES, set())

    def test_known_limitations_present(self):
        r = verify_registry(REGISTRY_PATH)
        joined = " ".join(r.registry["known_limitations"]).lower()
        self.assertIn("read-only", joined)
        self.assertIn("does not run workflows", joined)
        self.assertIn("does not prove truth", joined)

    def test_38_readme_disclaimers_present(self):
        with open(os.path.join(HERE, "README.md"), encoding="utf-8") as f:
            readme = f.read().lower()
        self.assertIn("read-only", readme)
        self.assertIn("does not run workflows", readme)
        self.assertIn("does not prove truth", readme)
        self.assertTrue("coordinator" in readme and "companion" in readme)


if __name__ == "__main__":
    unittest.main()
