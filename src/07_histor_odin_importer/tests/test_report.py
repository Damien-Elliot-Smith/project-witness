# tests/test_report.py
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from histor_odin_importer.report import build_summary, build_replay_report  # noqa: E402
from histor_odin_importer.canonical import canonical_bytes  # noqa: E402
from histor_odin_importer import versions  # noqa: E402
from tests.helpers import report_obj, trace_obj, claims_obj  # noqa: E402


def _summary(reasoning_status="CONSISTENT", claim_count=1, contradiction_count=0,
             step_count=1):
    return build_summary(
        report=report_obj("case_001", reasoning_status, claim_count,
                          contradiction_count),
        trace=trace_obj("case_001", step_count),
        claims=claims_obj("case_001", claim_count),
        claims_sha256="a" * 64, report_sha256="b" * 64, trace_sha256="c" * 64)


class TestReport(unittest.TestCase):
    def test_summary_fields(self):
        s = _summary()
        self.assertEqual(s["histor_odin_importer_version"], "0.1.0")
        self.assertEqual(s["import_status"], "IMPORTED_VERIFIED_ODIN")
        self.assertEqual(s["source_component"], "odin_claim_reasoner")
        self.assertEqual(s["source_reasoning_status"], "CONSISTENT")
        self.assertEqual(s["source_claims_sha256"], "a" * 64)
        self.assertEqual(s["source_reasoning_report_sha256"], "b" * 64)
        self.assertEqual(s["source_proof_trace_sha256"], "c" * 64)

    def test_proof_step_count_from_trace(self):
        s = _summary(step_count=3)
        self.assertEqual(s["proof_step_count"], 3)

    def test_status_preserved_for_contradiction(self):
        s = _summary(reasoning_status="CONTRADICTION_DETECTED",
                     contradiction_count=1)
        self.assertEqual(s["source_reasoning_status"], "CONTRADICTION_DETECTED")
        self.assertEqual(s["contradiction_count"], 1)

    def test_summary_deterministic_canonical(self):
        self.assertEqual(canonical_bytes(_summary()), canonical_bytes(_summary()))

    def test_known_limitations_disclaim_truth(self):
        joined = " ".join(_summary()["known_limitations"]).lower()
        self.assertIn("does not prove claims are true", joined)
        self.assertIn("does not import aletheia evidence metadata", joined)

    def test_replay_report_contents(self):
        report = build_replay_report(_summary(claim_count=2, step_count=2))
        self.assertIn("ODIN Reasoning Import Report", report)
        self.assertIn("import_status: IMPORTED_VERIFIED_ODIN", report)
        self.assertIn("source_reasoning_status: CONSISTENT", report)
        self.assertIn("claim_count: 2", report)
        self.assertIn("proof_step_count: 2", report)
        self.assertIn("truth_claim: none", report)
        self.assertIn(versions.TRUTH_DISCLAIMER, report)
        self.assertTrue(report.endswith("\n"))


if __name__ == "__main__":
    unittest.main()
