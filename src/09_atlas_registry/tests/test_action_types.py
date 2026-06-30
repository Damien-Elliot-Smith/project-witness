# tests/test_action_types.py
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


def _action(name):
    return {"action_type": name, "introduced_by_component": "sentinel_core",
            "description": "x", "known_limitations": []}


class TestActionTypes(unittest.TestCase):
    def test_8_duplicate_action_type_refused(self):
        reg = mutate(lambda r: r["action_types"].append(
            dict(r["action_types"][0])))
        with self.assertRaises(RegistryError) as cm:
            verify_registry(write_registry(reg))
        self.assertEqual(cm.exception.registry_status,
                         versions.FAILED_DUPLICATE_ENTRY)

    def test_13_unsafe_action_type_refused(self):
        reg = mutate(lambda r: r["action_types"][0].update(
            action_type="bad/action"))
        with self.assertRaises(RegistryError) as cm:
            verify_registry(write_registry(reg))
        self.assertEqual(cm.exception.reason, "UNSAFE_ID")

    def test_18_missing_required_action_type_refused(self):
        reg = mutate(lambda r: r["action_types"].clear())
        with self.assertRaises(RegistryError) as cm:
            verify_registry(write_registry(reg))
        self.assertEqual(cm.exception.reason, "REQUIRED_ACTION_MISSING")

    def test_forbidden_action_type_refused(self):
        for bad in ("WRITE_FILE", "DELETE_FILE", "SHELL_COMMAND", "NETWORK_CALL"):
            reg = mutate(lambda r, b=bad: r["action_types"].append(_action(b)))
            with self.assertRaises(RegistryError) as cm:
                verify_registry(write_registry(reg))
            self.assertEqual(cm.exception.reason, "FORBIDDEN_ACTION_TYPE")

    def test_required_action_type_present(self):
        r = verify_registry(write_registry(mutate(lambda r: None)))
        names = {a["action_type"] for a in r.registry["action_types"]}
        self.assertIn("CREATE_DIRECTORY", names)


if __name__ == "__main__":
    unittest.main()
