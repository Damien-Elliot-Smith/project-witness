import os
import tempfile
import unittest

from connected_demo_lib import engine, canonical
from connected_demo_lib.runners import FixtureRunner

_PARAMS = {"case_id": "C", "evidence_id": "E", "evidence_file": "x",
           "allowed_root": "x", "case_directory_name": "c", "inventory": "x"}


class TestConnectedDemo(unittest.TestCase):
    def test_honest_chain_completes(self):
        out = tempfile.mkdtemp()
        rep = engine.run_demo(_PARAMS, FixtureRunner(honest=True), out)
        self.assertEqual(rep["demo_status"], "DEMO_COMPLETED")
        for key, val in canonical.REQUIRED.items():
            self.assertEqual(rep["observed_statuses"][key], val)

    def test_failing_stage_short_circuits(self):
        out = tempfile.mkdtemp()
        rep = engine.run_demo(_PARAMS, FixtureRunner(honest=False), out)
        self.assertEqual(rep["demo_status"], "DEMO_FAILED")

    def test_report_is_canonical_and_checksummed(self):
        out = tempfile.mkdtemp()
        engine.run_demo(_PARAMS, FixtureRunner(honest=True), out)
        with open(os.path.join(out, engine.REPORT_FILE), "rb") as handle:
            raw = handle.read()
        self.assertEqual(raw, canonical.canonical_bytes(canonical.load_json(
            os.path.join(out, engine.REPORT_FILE))))
        self.assertTrue(os.path.isfile(os.path.join(out, engine.CHECKSUMS_FILE)))

    def test_no_truth_claim_in_report(self):
        out = tempfile.mkdtemp()
        engine.run_demo(_PARAMS, FixtureRunner(honest=True), out)
        with open(os.path.join(out, engine.REPORT_FILE), encoding="utf-8") as handle:
            text = handle.read().lower()
        self.assertNotIn("is true", text)
        self.assertNotIn("proves truth", text)


if __name__ == "__main__":
    unittest.main()
