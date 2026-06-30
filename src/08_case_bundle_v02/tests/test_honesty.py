# tests/test_honesty.py
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from case_bundle_v02_lib import versions  # noqa: E402
from case_bundle_v02_lib.verifier import verify_bundle  # noqa: E402
from tests.helpers import good_bundle  # noqa: E402


class TestHonesty(unittest.TestCase):
    def test_default_bundle_has_no_truth_claim(self):
        r = verify_bundle(good_bundle())
        self.assertEqual(r.bundle_status, "BUNDLED_VERIFIED_CASE")

    def test_bundle_statuses_contain_no_truth_token(self):
        statuses = {
            versions.BUNDLED_VERIFIED_CASE, versions.FAILED_SENTINEL_CASE_VERIFY,
            versions.FAILED_ALETHEIA_CASE_VERIFY, versions.FAILED_ODIN_CASE_VERIFY,
            versions.FAILED_CASE_ID_MISMATCH, versions.FAILED_CHECKSUMS_INVALID,
        }
        for s in statuses:
            up = s.upper()
            self.assertNotIn("AUTHENTIC", up)
            self.assertNotIn("PROVEN", up)

    def test_known_limitations_disclaim_both_truths(self):
        joined = " ".join(versions.KNOWN_LIMITATIONS).lower()
        self.assertIn("does not prove evidence contents are true", joined)
        self.assertIn("does not prove odin claims are true", joined)
        self.assertIn("whole-folder fabrication remains possible", joined)

    def test_readme_has_required_disclaimers(self):
        with open(os.path.join(HERE, "README.md"), encoding="utf-8") as f:
            readme = f.read().lower()
        self.assertIn("packages verified", readme)
        self.assertTrue("not" in readme and "true" in readme)
        self.assertIn("does not execute", readme)
        self.assertIn("coordinator", readme)
        self.assertIn("companion", readme)


if __name__ == "__main__":
    unittest.main()
