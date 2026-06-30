# tests/test_odin_reader.py
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from histor_odin_importer.odin_reader import (  # noqa: E402
    read_run, validate_report, require_importable_status)
from histor_odin_importer.errors import OdinRunError  # noqa: E402
from histor_odin_importer import versions  # noqa: E402
from tests.helpers import (  # noqa: E402
    report_obj, make_run_dir, consistent_run, contradiction_run)


class TestOdinReader(unittest.TestCase):
    def test_1_valid_run_accepted(self):
        run = read_run(consistent_run())
        self.assertEqual(run.report["case_id"], "case_001")
        require_importable_status(run.report)  # must not raise

    def test_5_missing_report_refused(self):
        d = make_run_dir(omit={versions.ODIN_REPORT_NAME})
        with self.assertRaises(OdinRunError) as cm:
            read_run(d)
        self.assertEqual(cm.exception.reason, "REPORT_MISSING")

    def test_6_missing_proof_trace_refused(self):
        d = make_run_dir(omit={versions.ODIN_TRACE_NAME})
        with self.assertRaises(OdinRunError) as cm:
            read_run(d)
        self.assertEqual(cm.exception.reason, "PROOF_TRACE_MISSING")

    def test_7_missing_claims_refused(self):
        d = make_run_dir(omit={versions.ODIN_CLAIMS_NAME})
        with self.assertRaises(OdinRunError) as cm:
            read_run(d)
        self.assertEqual(cm.exception.reason, "CLAIMS_MISSING")

    def test_8_invalid_input_status_refused(self):
        r = validate_report(report_obj(reasoning_status="INVALID_INPUT"))
        with self.assertRaises(OdinRunError) as cm:
            require_importable_status(r)
        self.assertEqual(cm.exception.reason, "REASONING_STATUS_INVALID")

    def test_9_consistent_status_accepted(self):
        require_importable_status(validate_report(
            report_obj(reasoning_status="CONSISTENT")))

    def test_10_contradiction_status_accepted(self):
        require_importable_status(validate_report(
            report_obj(reasoning_status="CONTRADICTION_DETECTED")))

    def test_other_status_refused(self):
        for bad in ("MAYBE", "OK", "", "consistent"):
            r = validate_report(report_obj(reasoning_status=bad))
            with self.assertRaises(OdinRunError):
                require_importable_status(r)

    def test_report_missing_field_refused(self):
        with self.assertRaises(OdinRunError) as cm:
            validate_report(report_obj(drop=["contradiction_count"]))
        self.assertEqual(cm.exception.reason, "REPORT_INVALID")

    def test_malformed_report_refused(self):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, versions.ODIN_REPORT_NAME), "w") as f:
            f.write("{not json")
        # also need the other files so read order reaches report first
        with self.assertRaises(OdinRunError) as cm:
            read_run(d)
        self.assertIn(cm.exception.reason, ("REPORT_MALFORMED", "REPORT_MISSING"))

    def test_verbatim_bytes_captured(self):
        run = read_run(consistent_run())
        self.assertTrue(run.report_bytes.endswith(b"\n"))
        self.assertTrue(run.claims_bytes.endswith(b"\n"))


if __name__ == "__main__":
    unittest.main()
