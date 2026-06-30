# tests/test_claim_schema.py
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from odin_reasoner.claims import validate_claim_set  # noqa: E402
from odin_reasoner.errors import ValidationError  # noqa: E402
from tests.helpers import (  # noqa: E402
    claim_set, claim, support, consistent_set, deep)


class TestClaimSchema(unittest.TestCase):
    def test_1_valid_claim_set_accepted(self):
        validate_claim_set(consistent_set())  # must not raise

    def test_2_missing_claims_field_refused(self):
        d = consistent_set()
        del d["claims"]
        with self.assertRaises(ValidationError) as cm:
            validate_claim_set(d)
        self.assertEqual(cm.exception.reason, "CLAIM_SET_FIELDS")

    def test_3_extra_top_level_field_refused(self):
        d = consistent_set()
        d["surprise"] = 1
        with self.assertRaises(ValidationError) as cm:
            validate_claim_set(d)
        self.assertEqual(cm.exception.reason, "CLAIM_SET_FIELDS")

    def test_4_duplicate_claim_id_refused(self):
        d = claim_set([claim("claim_001"),
                       claim("claim_001", subject="other:x",
                             supports=[support("support_002", "b" * 64)])])
        with self.assertRaises(ValidationError) as cm:
            validate_claim_set(d)
        self.assertEqual(cm.exception.reason, "DUPLICATE_CLAIM_ID")

    def test_7_empty_support_list_refused(self):
        d = claim_set([claim("claim_001", supports=[])])
        with self.assertRaises(ValidationError) as cm:
            validate_claim_set(d)
        self.assertEqual(cm.exception.reason, "SUPPORT_EMPTY")

    def test_8_invalid_polarity_refused(self):
        d = claim_set([claim("claim_001", polarity="MAYBE")])
        with self.assertRaises(ValidationError) as cm:
            validate_claim_set(d)
        self.assertEqual(cm.exception.reason, "CLAIM_POLARITY")

    def test_9_float_object_refused(self):
        d = claim_set([claim("claim_001", obj=1.5)])
        with self.assertRaises(ValidationError) as cm:
            validate_claim_set(d)
        self.assertEqual(cm.exception.reason, "CLAIM_OBJECT_TYPE")

    def test_allowed_object_types(self):
        for obj in ("a string", True, False, 42, None):
            validate_claim_set(claim_set([claim("claim_001", obj=obj)]))

    def test_missing_claim_field_refused(self):
        d = consistent_set()
        del d["claims"][0]["polarity"]
        with self.assertRaises(ValidationError) as cm:
            validate_claim_set(d)
        self.assertEqual(cm.exception.reason, "CLAIM_FIELDS")

    def test_extra_support_field_refused(self):
        d = consistent_set()
        d["claims"][0]["support"][0]["extra"] = "x"
        with self.assertRaises(ValidationError) as cm:
            validate_claim_set(d)
        self.assertEqual(cm.exception.reason, "SUPPORT_FIELDS")

    def test_bad_support_sha_refused(self):
        d = consistent_set()
        d["claims"][0]["support"][0]["source_sha256"] = "nothex"
        with self.assertRaises(ValidationError) as cm:
            validate_claim_set(d)
        self.assertEqual(cm.exception.reason, "SUPPORT_SHA256")

    def test_empty_claims_list_refused(self):
        with self.assertRaises(ValidationError) as cm:
            validate_claim_set(claim_set([]))
        self.assertEqual(cm.exception.reason, "CLAIMS_EMPTY")

    def test_wrong_version_refused(self):
        d = consistent_set()
        d["odin_claim_set_version"] = "9.9.9"
        with self.assertRaises(ValidationError) as cm:
            validate_claim_set(d)
        self.assertEqual(cm.exception.reason, "CLAIM_SET_VERSION")


if __name__ == "__main__":
    unittest.main()
