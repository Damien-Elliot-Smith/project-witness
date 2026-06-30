# tests/test_report.py
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from histor_aletheia_importer.report import build_summary, build_replay_report  # noqa: E402
from histor_aletheia_importer.canonical import canonical_bytes  # noqa: E402
from histor_aletheia_importer import versions  # noqa: E402
from tests.helpers import manifest  # noqa: E402


def _summary():
    return build_summary(manifest=manifest(), manifest_sha256="b" * 64)


class TestReport(unittest.TestCase):
    def test_summary_fields(self):
        s = _summary()
        self.assertEqual(s["histor_aletheia_importer_version"], "0.1.0")
        self.assertEqual(s["import_status"], "IMPORTED_VERIFIED_ALETHEIA")
        self.assertEqual(s["source_component"], "aletheia_evidence_bundle")
        self.assertEqual(s["source_evidence_status"], "VERIFIED_PRESENT")
        self.assertEqual(s["source_bundle_manifest_sha256"], "b" * 64)

    def test_summary_deterministic_canonical(self):
        self.assertEqual(canonical_bytes(_summary()), canonical_bytes(_summary()))

    def test_summary_known_limitations_disclaim_truth(self):
        s = _summary()
        joined = " ".join(s["known_limitations"]).lower()
        self.assertIn("does not prove the evidence contents are true", joined)

    def test_replay_report_contents(self):
        report = build_replay_report(_summary())
        self.assertIn("Aletheia Evidence Bundle Import Report", report)
        self.assertIn("import_status: IMPORTED_VERIFIED_ALETHEIA", report)
        self.assertIn("source_evidence_status: VERIFIED_PRESENT", report)
        self.assertIn("truth_claim: none", report)
        self.assertIn(versions.TRUTH_DISCLAIMER, report)
        self.assertTrue(report.endswith("\n"))

    def test_replay_report_has_both_shas(self):
        s = _summary()
        report = build_replay_report(s)
        self.assertIn(f"source_file_sha256: {s['source_file_sha256']}", report)
        self.assertIn(f"bundled_file_sha256: {s['bundled_file_sha256']}", report)


if __name__ == "__main__":
    unittest.main()
