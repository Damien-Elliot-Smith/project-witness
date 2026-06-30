# tests/test_report.py
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from evidence_reasoning_demo.report import build_report  # noqa: E402
from evidence_reasoning_demo.canonical import canonical_bytes  # noqa: E402
from evidence_reasoning_demo import versions  # noqa: E402


def _report():
    return build_report(
        case_id="case_001", evidence_id="evidence_001",
        aletheia_status="VERIFIED_PRESENT", bridge_status="CONVERTED",
        odin_reasoning_status="CONSISTENT", odin_claim_count=2,
        generated_claims=["evidence.present", "evidence.integrity_verified"])


class TestReport(unittest.TestCase):
    def test_18_report_is_canonical(self):
        r = _report()
        raw = canonical_bytes(r)
        # Deterministic + canonical (round-trips, ends with newline).
        self.assertEqual(canonical_bytes(_report()), raw)
        self.assertTrue(raw.endswith(b"\n"))

    def test_report_fields(self):
        r = _report()
        self.assertEqual(r["evidence_reasoning_demo_version"], "0.1.0")
        self.assertEqual(r["demo_status"], "DEMO_COMPLETED")
        self.assertEqual(r["odin_claim_count"], 2)
        self.assertEqual(r["verified_outputs"],
                         ["aletheia_bundle", "bridge_output", "odin_output"])

    def test_report_known_limitations_disclaim_truth(self):
        r = _report()
        joined = " ".join(r["known_limitations"]).lower()
        self.assertIn("does not prove the evidence contents are true", joined)

    def test_report_only_allowed_predicates(self):
        r = _report()
        for pred in r["generated_claims"]:
            self.assertIn(pred, versions.ALLOWED_PREDICATES)


if __name__ == "__main__":
    unittest.main()
