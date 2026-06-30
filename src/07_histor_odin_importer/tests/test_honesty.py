# tests/test_honesty.py
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from histor_odin_importer import versions  # noqa: E402
from histor_odin_importer.verifier import verify_case  # noqa: E402
from tests.helpers import good_case  # noqa: E402


class TestHonesty(unittest.TestCase):
    def test_default_case_has_no_truth_claim(self):
        r = verify_case(good_case())
        self.assertEqual(r.import_status, "IMPORTED_VERIFIED_ODIN")

    def test_import_statuses_contain_no_truth_token(self):
        statuses = {
            versions.IMPORTED_VERIFIED_ODIN, versions.FAILED_ODIN_VERIFY,
            versions.FAILED_REASONING_STATUS_INVALID,
            versions.FAILED_REPORT_INVALID, versions.FAILED_PROOF_TRACE_INVALID,
            versions.FAILED_CHECKSUMS_INVALID,
        }
        for s in statuses:
            up = s.upper()
            self.assertNotIn("AUTHENTIC", up)
            self.assertNotIn("PROVEN", up)
            self.assertNotIn("GENUINE", up)

    def test_replay_disclaimer_present(self):
        self.assertIn("does not prove that any claim is true",
                      versions.TRUTH_DISCLAIMER.lower())

    def test_known_limitations_disclaim_truth_and_aletheia(self):
        joined = " ".join(versions.KNOWN_LIMITATIONS).lower()
        self.assertIn("does not prove claims are true", joined)
        self.assertIn("does not import aletheia evidence metadata", joined)

    def test_readme_has_required_disclaimers(self):
        with open(os.path.join(HERE, "README.md"), encoding="utf-8") as f:
            readme = f.read().lower()
        self.assertIn("structural reasoning metadata only", readme)
        self.assertTrue("not" in readme and "true" in readme,
                        "README must disclaim proving truth")
        self.assertIn("aletheia", readme)
        self.assertIn("coordinator", readme)
        self.assertIn("companion", readme)


if __name__ == "__main__":
    unittest.main()
