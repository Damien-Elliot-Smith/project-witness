# tests/test_workflow_types.py
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


class TestWorkflowTypes(unittest.TestCase):
    def test_7_duplicate_workflow_type_refused(self):
        reg = mutate(lambda r: r["workflow_types"].append(
            dict(r["workflow_types"][0])))
        with self.assertRaises(RegistryError) as cm:
            verify_registry(write_registry(reg))
        self.assertEqual(cm.exception.registry_status,
                         versions.FAILED_DUPLICATE_ENTRY)

    def test_12_unsafe_workflow_type_refused(self):
        reg = mutate(lambda r: r["workflow_types"][0].update(
            workflow_type="bad/type"))
        with self.assertRaises(RegistryError) as cm:
            verify_registry(write_registry(reg))
        self.assertEqual(cm.exception.reason, "UNSAFE_ID")

    def test_17_missing_required_workflow_type_refused(self):
        reg = mutate(lambda r: r["workflow_types"].__setitem__(
            slice(None), [w for w in r["workflow_types"]
                          if w["workflow_type"] != "CREATE_EVIDENCE_REASONING_CASE"]))
        with self.assertRaises(RegistryError) as cm:
            verify_registry(write_registry(reg))
        self.assertEqual(cm.exception.reason, "REQUIRED_WORKFLOW_MISSING")

    def test_both_required_workflow_types_present(self):
        r = verify_registry(write_registry(mutate(lambda r: None)))
        names = {w["workflow_type"] for w in r.registry["workflow_types"]}
        for wt in versions.REQUIRED_WORKFLOW_TYPES:
            self.assertIn(wt, names)


if __name__ == "__main__":
    unittest.main()
