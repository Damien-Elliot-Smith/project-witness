# tests/test_action_schema.py
import unittest

from sentinel_core.action_schema import validate_action_request, ACTION_SCHEMA_VERSION
from sentinel_core.errors import SchemaError
from tests.helpers import make_request


class TestActionSchema(unittest.TestCase):
    def _valid(self):
        return make_request("REQ-1", "demo/output")

    def test_valid_request_passes(self):
        out = validate_action_request(self._valid())
        self.assertEqual(out["action_type"], "CREATE_DIRECTORY")
        self.assertEqual(out["preconditions"], sorted(["target_absent", "parent_exists", "inside_allowed_root"]))

    def test_non_dict_rejected(self):
        for bad in ["make me a folder", 42, None, ["x"]]:
            with self.assertRaises(SchemaError):
                validate_action_request(bad)

    def test_natural_language_string_rejected(self):
        with self.assertRaises(SchemaError):
            validate_action_request("make me a folder somewhere")

    def test_missing_field_rejected(self):
        r = self._valid()
        del r["target_path"]
        with self.assertRaises(SchemaError):
            validate_action_request(r)

    def test_extra_field_rejected(self):
        r = self._valid()
        r["sneaky"] = True
        with self.assertRaises(SchemaError):
            validate_action_request(r)

    def test_wrong_schema_version_rejected(self):
        r = self._valid()
        r["schema_version"] = "9.9.9"
        with self.assertRaises(SchemaError):
            validate_action_request(r)

    def test_dry_run_must_be_bool(self):
        r = self._valid()
        r["dry_run"] = "false"
        with self.assertRaises(SchemaError):
            validate_action_request(r)

    def test_empty_request_id_rejected(self):
        r = self._valid()
        r["request_id"] = ""
        with self.assertRaises(SchemaError):
            validate_action_request(r)

    def test_control_character_in_request_id_rejected(self):
        r = self._valid()
        r["request_id"] = "REQ\x00-1"
        with self.assertRaises(SchemaError):
            validate_action_request(r)

    def test_request_with_allowed_root_rejected_as_extra_field(self):
        # v1.1.0 removed allowed_root from the schema. A v1.0.0-style request
        # that still carries it must be rejected, failing closed instead of
        # honouring a caller-selected root.
        r = self._valid()
        r["allowed_root"] = "/anywhere/the/caller/likes"
        with self.assertRaises(SchemaError):
            validate_action_request(r)

    def test_wrong_preconditions_rejected(self):
        r = self._valid()
        r["preconditions"] = ["target_absent"]
        with self.assertRaises(SchemaError):
            validate_action_request(r)

    def test_non_string_condition_rejected(self):
        r = self._valid()
        r["postconditions"] = [123, "target_exists"]
        with self.assertRaises(SchemaError):
            validate_action_request(r)

    def test_empty_target_path_allowed_by_schema(self):
        # Empty target_path is structurally valid (str); it is the path policy
        # that blocks it with BLOCK_EMPTY_PATH. Schema only checks type/length.
        r = self._valid()
        r["target_path"] = ""
        out = validate_action_request(r)
        self.assertEqual(out["target_path"], "")


if __name__ == "__main__":
    unittest.main()
