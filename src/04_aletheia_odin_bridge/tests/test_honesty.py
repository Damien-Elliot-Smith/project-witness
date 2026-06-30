# tests/test_honesty.py
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from aletheia_odin_bridge.claim_builder import build_claims, _assert_allowed_predicate  # noqa: E402
from aletheia_odin_bridge.errors import BridgeError  # noqa: E402
from aletheia_odin_bridge import versions  # noqa: E402
from tests.helpers import manifest  # noqa: E402


class TestHonesty(unittest.TestCase):
    def test_no_truth_predicate_generated(self):
        cs = build_claims(manifest())
        for c in cs["claims"]:
            self.assertIn(c["predicate"], versions.ALLOWED_PREDICATES)

    def test_forbidden_tokens_not_in_allowed_predicates(self):
        for pred in versions.ALLOWED_PREDICATES:
            low = pred.lower()
            for token in versions.FORBIDDEN_PREDICATE_TOKENS:
                self.assertNotIn(token, low,
                                 f"allowed predicate {pred!r} contains {token!r}")

    def test_guard_rejects_forbidden_predicate(self):
        for bad in ("contents.true", "file.authentic", "source.trusted",
                    "statement.proven", "image.real", "data.genuine"):
            with self.assertRaises(BridgeError):
                _assert_allowed_predicate(bad)

    def test_guard_accepts_only_the_two_allowed(self):
        _assert_allowed_predicate("evidence.present")
        _assert_allowed_predicate("evidence.integrity_verified")
        with self.assertRaises(BridgeError):
            _assert_allowed_predicate("evidence.something_else")

    def test_statuses_contain_no_truth_token(self):
        statuses = {
            versions.BRIDGE_CONVERTED, versions.BRIDGE_FAILED_ALETHEIA_VERIFY,
            versions.BRIDGE_FAILED_MANIFEST_INVALID,
            versions.BRIDGE_FAILED_STATUS_NOT_VERIFIED_PRESENT,
            versions.BRIDGE_FAILED_ODIN_VALIDATE,
            versions.BRIDGE_FAILED_CHECKSUMS_INVALID,
        }
        for s in statuses:
            self.assertNotIn("TRUE", s.upper())
            self.assertNotIn("AUTHENTIC", s.upper())
            self.assertNotIn("PROVEN", s.upper())

    def test_known_limitations_disclaim_truth(self):
        joined = " ".join(versions.KNOWN_LIMITATIONS).lower()
        self.assertIn("does not prove the evidence contents are true", joined)

    def test_readme_disclaims_truth_and_says_integrity_metadata(self):
        with open(os.path.join(HERE, "README.md"), encoding="utf-8") as f:
            readme = f.read().lower()
        self.assertIn("integrity", readme)
        self.assertIn("metadata only", readme)
        self.assertTrue("not" in readme and "true" in readme,
                        "README must disclaim proving truth")


if __name__ == "__main__":
    unittest.main()
