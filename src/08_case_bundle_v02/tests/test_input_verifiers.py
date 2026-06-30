# tests/test_input_verifiers.py
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from case_bundle_v02_lib.input_verifiers import InProcessInputVerifier  # noqa: E402
from case_bundle_v02_lib.errors import InputCaseError  # noqa: E402
from case_bundle_v02_lib import versions  # noqa: E402
from tests.helpers import (  # noqa: E402
    make_sentinel_case, make_aletheia_case, make_odin_case)


class TestInputVerifiers(unittest.TestCase):
    def setUp(self):
        self.v = InProcessInputVerifier()

    def test_1_valid_sentinel_accepted(self):
        facts = self.v.verify_sentinel(make_sentinel_case())
        self.assertEqual(facts["case_id"], "case_001")
        self.assertEqual(facts["action_status"], "PASS_STRICT")
        self.assertEqual(facts["source_component"], "histor_lite")

    def test_2_valid_aletheia_accepted(self):
        facts = self.v.verify_aletheia(make_aletheia_case())
        self.assertEqual(facts["source_evidence_status"], "VERIFIED_PRESENT")

    def test_3_valid_odin_accepted(self):
        facts = self.v.verify_odin(make_odin_case())
        self.assertEqual(facts["source_reasoning_status"], "CONSISTENT")

    def test_odin_contradiction_accepted(self):
        facts = self.v.verify_odin(make_odin_case(
            reasoning_status="CONTRADICTION_DETECTED", claim_count=2,
            contradiction_count=1))
        self.assertEqual(facts["source_reasoning_status"], "CONTRADICTION_DETECTED")

    def test_odin_invalid_input_refused(self):
        with self.assertRaises(InputCaseError) as cm:
            self.v.verify_odin(make_odin_case(reasoning_status="INVALID_INPUT"))
        self.assertEqual(cm.exception.reason, "ODIN_INVALID_INPUT")

    def test_4_missing_sentinel_refused(self):
        with self.assertRaises(InputCaseError) as cm:
            self.v.verify_sentinel("/no/such/case")
        self.assertEqual(cm.exception.reason, "CASE_MISSING")

    def test_sentinel_internal_checksum_mismatch_refused(self):
        d = make_sentinel_case()
        with open(os.path.join(d, versions.SENTINEL_SUMMARY), "ab") as f:
            f.write(b" ")
        with self.assertRaises(InputCaseError) as cm:
            self.v.verify_sentinel(d)
        self.assertEqual(cm.exception.reason, "INTERNAL_CHECKSUM_MISMATCH")

    def test_aletheia_internal_checksum_mismatch_refused(self):
        d = make_aletheia_case()
        with open(os.path.join(d, versions.ALETHEIA_SUMMARY), "ab") as f:
            f.write(b" ")
        with self.assertRaises(InputCaseError) as cm:
            self.v.verify_aletheia(d)
        self.assertEqual(cm.exception.reason, "INTERNAL_CHECKSUM_MISMATCH")

    def test_missing_required_file_refused(self):
        d = make_odin_case()
        os.remove(os.path.join(d, versions.ODIN_CLAIMS_COPY))
        with self.assertRaises(InputCaseError) as cm:
            self.v.verify_odin(d)
        self.assertEqual(cm.exception.reason, "CASE_FILE_MISSING")


if __name__ == "__main__":
    unittest.main()
