# tests/test_claim_builder.py
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from aletheia_odin_bridge.claim_builder import build_claims  # noqa: E402
from aletheia_odin_bridge.canonical import canonical_bytes  # noqa: E402
from aletheia_odin_bridge import versions  # noqa: E402
from tests.helpers import manifest, SHA  # noqa: E402


class TestClaimBuilder(unittest.TestCase):
    def test_9_claims_generated_canonically(self):
        cs = build_claims(manifest())
        # Deterministic: rebuilding gives byte-identical canonical output.
        self.assertEqual(canonical_bytes(build_claims(manifest())),
                         canonical_bytes(cs))
        self.assertEqual(cs["odin_claim_set_version"], "0.1.0")
        self.assertEqual(cs["case_id"], "case_001")

    def test_10_exactly_two_claims(self):
        cs = build_claims(manifest())
        self.assertEqual(len(cs["claims"]), 2)

    def test_11_only_allowed_predicates(self):
        cs = build_claims(manifest())
        preds = [c["predicate"] for c in cs["claims"]]
        self.assertEqual(preds, ["evidence.present", "evidence.integrity_verified"])
        for p in preds:
            self.assertIn(p, versions.ALLOWED_PREDICATES)

    def test_12_support_preserves_evidence_id(self):
        cs = build_claims(manifest(evidence_id="evidence_042"))
        for c in cs["claims"]:
            self.assertEqual(c["subject"], "evidence:evidence_042")
            for s in c["support"]:
                self.assertEqual(s["source_id"], "evidence_042")
                self.assertEqual(s["source_component"], "aletheia_evidence_bundle")

    def test_13_support_sha_equals_bundled_sha(self):
        cs = build_claims(manifest(sha=SHA))
        for c in cs["claims"]:
            for s in c["support"]:
                self.assertEqual(s["source_sha256"], SHA)

    def test_14_no_truth_predicates(self):
        cs = build_claims(manifest())
        for c in cs["claims"]:
            low = c["predicate"].lower()
            for token in versions.FORBIDDEN_PREDICATE_TOKENS:
                self.assertNotIn(token, low)

    def test_all_claims_affirmed_true(self):
        cs = build_claims(manifest())
        for c in cs["claims"]:
            self.assertEqual(c["object"], True)
            self.assertEqual(c["polarity"], "AFFIRMED")

    def test_claim_ids_unique(self):
        cs = build_claims(manifest())
        ids = [c["claim_id"] for c in cs["claims"]]
        self.assertEqual(len(ids), len(set(ids)))
        support_ids = [s["support_id"] for c in cs["claims"] for s in c["support"]]
        self.assertEqual(len(support_ids), len(set(support_ids)))


if __name__ == "__main__":
    unittest.main()
