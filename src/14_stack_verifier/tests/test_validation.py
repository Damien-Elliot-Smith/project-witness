from stack_verifier_lib import validation
from tests._helpers import TempCase


class TestValidation(TempCase):
    def test_valid_source_types(self):
        self.assertTrue(validation.is_valid_source_type("coordinator_v03_output"))
        self.assertTrue(validation.is_valid_source_type("companion_v03_output"))

    def test_invalid_source_type(self):
        self.assertFalse(validation.is_valid_source_type("nope"))

    def test_safe_id(self):
        self.assertTrue(validation.is_safe_id("case_001"))
        self.assertFalse(validation.is_safe_id("../x"))
        self.assertFalse(validation.is_safe_id("a/b"))

    def test_relative_path(self):
        self.assertTrue(validation.is_relative_path("coordinator_output/x.json"))
        self.assertFalse(validation.is_relative_path("/abs/x.json"))
