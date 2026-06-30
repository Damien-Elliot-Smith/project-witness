# tests/test_registry_schema.py
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from atlas_registry_lib.verifier import verify_registry, verify_registry_obj  # noqa: E402
from atlas_registry_lib.errors import RegistryError  # noqa: E402
from atlas_registry_lib import versions  # noqa: E402
from tests.helpers import (  # noqa: E402
    REGISTRY_PATH, good_registry, write_registry, write_registry_raw, mutate)


class TestRegistrySchema(unittest.TestCase):
    def test_1_valid_registry_verifies(self):
        r = verify_registry(REGISTRY_PATH)
        self.assertEqual(r.registry_status, versions.REGISTRY_VERIFIED)

    def test_built_registry_verifies(self):
        r = verify_registry_obj(good_registry())
        self.assertEqual(r.registry_status, versions.REGISTRY_VERIFIED)

    def test_2_missing_registry_file_refused(self):
        with self.assertRaises(RegistryError) as cm:
            verify_registry("/no/such/atlas_registry.json")
        self.assertEqual(cm.exception.reason, "REGISTRY_MISSING")

    def test_3_non_canonical_json_refused(self):
        # pretty-printed (non-canonical) JSON
        path = write_registry_raw(b'{\n  "atlas_registry_version": "0.1.0"\n}\n')
        with self.assertRaises(RegistryError) as cm:
            verify_registry(path)
        self.assertEqual(cm.exception.registry_status,
                         versions.FAILED_NON_CANONICAL_JSON)

    def test_4_missing_top_field_refused(self):
        reg = mutate(lambda r: r.pop("statuses"))
        with self.assertRaises(RegistryError) as cm:
            verify_registry(write_registry(reg))
        self.assertEqual(cm.exception.reason, "MISSING_TOP_FIELD")

    def test_5_extra_top_field_refused(self):
        reg = mutate(lambda r: r.update(surprise=[]))
        with self.assertRaises(RegistryError) as cm:
            verify_registry(write_registry(reg))
        self.assertEqual(cm.exception.reason, "UNKNOWN_TOP_FIELD")

    def test_bad_version_refused(self):
        reg = mutate(lambda r: r.update(atlas_registry_version="9.9.9"))
        with self.assertRaises(RegistryError) as cm:
            verify_registry(write_registry(reg))
        self.assertEqual(cm.exception.reason, "BAD_VERSION")


if __name__ == "__main__":
    unittest.main()
