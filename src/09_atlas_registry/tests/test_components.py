# tests/test_components.py
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


class TestComponents(unittest.TestCase):
    def test_6_duplicate_component_id_refused(self):
        reg = mutate(lambda r: r["components"].append(
            dict(r["components"][0])))
        with self.assertRaises(RegistryError) as cm:
            verify_registry(write_registry(reg))
        self.assertEqual(cm.exception.registry_status,
                         versions.FAILED_DUPLICATE_ENTRY)

    def test_11_unsafe_component_id_refused(self):
        reg = mutate(lambda r: r["components"][0].update(component_id="../evil"))
        with self.assertRaises(RegistryError) as cm:
            verify_registry(write_registry(reg))
        self.assertEqual(cm.exception.reason, "UNSAFE_ID")

    def test_14_invalid_component_type_refused(self):
        reg = mutate(lambda r: r["components"][0].update(component_type="WIDGET"))
        with self.assertRaises(RegistryError) as cm:
            verify_registry(write_registry(reg))
        self.assertEqual(cm.exception.reason, "BAD_COMPONENT_TYPE")

    def test_15_invalid_frozen_status_refused(self):
        reg = mutate(lambda r: r["components"][0].update(frozen_status="MAYBE"))
        with self.assertRaises(RegistryError) as cm:
            verify_registry(write_registry(reg))
        self.assertEqual(cm.exception.reason, "BAD_FROZEN_STATUS")

    def test_12_version_not_string_refused(self):
        reg = mutate(lambda r: r["components"][0].update(component_version=1))
        with self.assertRaises(RegistryError) as cm:
            verify_registry(write_registry(reg))
        self.assertEqual(cm.exception.reason, "VERSION_NOT_STRING")

    def test_16_missing_required_component_refused(self):
        reg = mutate(lambda r: r["components"].__setitem__(
            slice(None), [c for c in r["components"]
                          if c["component_id"] != "atlas_registry"]))
        with self.assertRaises(RegistryError) as cm:
            verify_registry(write_registry(reg))
        self.assertEqual(cm.exception.reason, "REQUIRED_COMPONENT_MISSING")

    def test_all_required_components_present(self):
        r = verify_registry(write_registry(mutate(lambda r: None)))
        ids = {c["component_id"] for c in r.registry["components"]}
        for cid in versions.REQUIRED_COMPONENT_IDS:
            self.assertIn(cid, ids)


if __name__ == "__main__":
    unittest.main()
