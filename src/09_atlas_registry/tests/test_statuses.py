# tests/test_statuses.py
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


def _status(name, group="verification_statuses", truth=False):
    return {"status": name, "status_group": group, "meaning": "x",
            "truth_claim": truth, "allowed_contexts": ["x"]}


class TestStatuses(unittest.TestCase):
    def test_9_duplicate_status_in_group_refused(self):
        reg = mutate(lambda r: r["statuses"].append(dict(r["statuses"][0])))
        with self.assertRaises(RegistryError) as cm:
            verify_registry(write_registry(reg))
        self.assertEqual(cm.exception.registry_status,
                         versions.FAILED_DUPLICATE_ENTRY)

    def test_same_status_different_group_allowed(self):
        # COMPLETED in step_statuses already; add COMPLETED in another group.
        reg = mutate(lambda r: r["statuses"].append(
            _status("COMPLETED", group="other_statuses")))
        r = verify_registry(write_registry(reg))
        self.assertEqual(r.registry_status, versions.REGISTRY_VERIFIED)

    def test_20_status_truth_claim_true_refused(self):
        reg = mutate(lambda r: r["statuses"][0].update(truth_claim=True))
        with self.assertRaises(RegistryError) as cm:
            verify_registry(write_registry(reg))
        self.assertEqual(cm.exception.registry_status,
                         versions.FAILED_TRUTH_CLAIM)
        self.assertEqual(cm.exception.reason, "STATUS_TRUTH_CLAIM")

    def test_truth_claim_not_bool_refused(self):
        reg = mutate(lambda r: r["statuses"][0].update(truth_claim="false"))
        with self.assertRaises(RegistryError) as cm:
            verify_registry(write_registry(reg))
        self.assertEqual(cm.exception.reason, "TRUTH_CLAIM_NOT_BOOL")

    def test_22_truth_like_status_name_refused(self):
        for bad in ("TRUE", "PROVEN_TRUE", "AUTHENTIC", "VERIFIED_TRUE",
                    "SOURCE_TRUSTED", "REALITY_PROVEN"):
            reg = mutate(lambda r, b=bad: r["statuses"].append(_status(b)))
            with self.assertRaises(RegistryError) as cm:
                verify_registry(write_registry(reg))
            self.assertEqual(cm.exception.registry_status,
                             versions.FAILED_TRUTH_CLAIM)
            self.assertEqual(cm.exception.reason, "STATUS_TRUTH_NAME")

    def test_24_required_statuses_present(self):
        r = verify_registry(write_registry(mutate(lambda r: None)))
        names = {s["status"] for s in r.registry["statuses"]}
        for st in versions.REQUIRED_STATUSES:
            self.assertIn(st, names)

    def test_missing_required_status_refused(self):
        reg = mutate(lambda r: r["statuses"].__setitem__(
            slice(None), [s for s in r["statuses"]
                          if s["status"] != "CONVERTED"]))
        with self.assertRaises(RegistryError) as cm:
            verify_registry(write_registry(reg))
        self.assertEqual(cm.exception.reason, "REQUIRED_STATUS_MISSING")


if __name__ == "__main__":
    unittest.main()
