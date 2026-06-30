# tests/test_honesty.py
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from evidence_reasoning_demo import versions  # noqa: E402
from tests.helpers import good_output, run_with_fake, FakeComponentRunner  # noqa: E402
from evidence_reasoning_demo.verifier import verify_run  # noqa: E402
from evidence_reasoning_demo.errors import VerifyError  # noqa: E402


class TestHonesty(unittest.TestCase):
    def test_no_truth_claims_in_default_output(self):
        out = good_output()
        r = verify_run(out)  # must pass, and only allowed predicates present
        self.assertEqual(r.demo_status, "DEMO_COMPLETED")

    def test_forbidden_tokens_not_in_allowed_predicates(self):
        for pred in versions.ALLOWED_PREDICATES:
            low = pred.lower()
            for token in versions.FORBIDDEN_PREDICATE_TOKENS:
                self.assertNotIn(token, low)

    def test_demo_statuses_contain_no_truth_token(self):
        statuses = {
            versions.DEMO_COMPLETED, versions.FAILED_INPUT_VALIDATION,
            versions.FAILED_ALETHEIA_BUNDLE, versions.FAILED_ALETHEIA_VERIFY,
            versions.FAILED_BRIDGE_CONVERT, versions.FAILED_BRIDGE_VERIFY,
            versions.FAILED_ODIN_REASON, versions.FAILED_ODIN_VERIFY,
            versions.FAILED_CHECKSUMS_INVALID,
        }
        for s in statuses:
            self.assertNotIn("TRUE", s.upper())
            self.assertNotIn("AUTHENTIC", s.upper())
            self.assertNotIn("PROVEN", s.upper())

    def test_truth_claim_from_upstream_is_rejected(self):
        # If a (hypothetical) upstream surfaced a truth-like claim, verify rejects.
        out = run_with_fake(
            runner=FakeComponentRunner(
                generated_claims=["evidence.present", "contents.true"])).out_dir
        with self.assertRaises(VerifyError) as cm:
            verify_run(out)
        self.assertIn(cm.exception.reason,
                      ("DISALLOWED_PREDICATE", "TRUTH_PREDICATE"))

    def test_known_limitations_disclaim_truth(self):
        joined = " ".join(versions.KNOWN_LIMITATIONS).lower()
        self.assertIn("does not prove the evidence contents are true", joined)

    def test_readme_has_required_disclaimers(self):
        with open(os.path.join(HERE, "README.md"), encoding="utf-8") as f:
            readme = f.read().lower()
        self.assertIn("executes and verifies", readme)
        self.assertTrue("not" in readme and "true" in readme,
                        "README must disclaim proving truth")
        self.assertIn("companion", readme)
        self.assertIn("coordinator", readme)


if __name__ == "__main__":
    unittest.main()
