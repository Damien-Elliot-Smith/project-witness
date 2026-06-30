# tests/test_importer.py
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import histor_odin_importer.importer as importer  # noqa: E402
from histor_odin_importer.canonical import canonical_bytes  # noqa: E402
from histor_odin_importer.errors import (  # noqa: E402
    ComponentPathError, OdinVerifyError, OdinRunError)
from histor_odin_importer import versions  # noqa: E402
from tests.helpers import (  # noqa: E402
    make_run_dir, report_obj, trace_obj, claims_obj, consistent_run,
    contradiction_run, import_with_fake, FakeOdinVerifier)


def _out():
    return os.path.join(tempfile.mkdtemp(prefix="odin_case_"), "case")


class TestImporter(unittest.TestCase):
    def test_2_missing_odin_root_refused(self):
        with self.assertRaises(ComponentPathError) as cm:
            import_with_fake(_out(), odin_root="/no/such/odin")
        self.assertEqual(cm.exception.reason, "ODIN_ROOT_MISSING")

    def test_3_missing_run_refused(self):
        with self.assertRaises(ComponentPathError) as cm:
            importer.import_reasoning(
                odin_root=HERE, run_dir="/no/such/run", out_dir=_out(),
                odin_verifier=FakeOdinVerifier())
        self.assertEqual(cm.exception.reason, "RUN_MISSING")

    def test_4_odin_verify_failure_refused(self):
        with self.assertRaises(OdinVerifyError) as cm:
            import_with_fake(_out(), ok=False)
        self.assertEqual(cm.exception.reason, "ODIN_VERIFY_FAILED")

    def test_8_invalid_input_refused(self):
        run = make_run_dir(report_obj(reasoning_status="INVALID_INPUT"))
        with self.assertRaises(OdinRunError) as cm:
            import_with_fake(_out(), run_dir=run)
        self.assertEqual(cm.exception.reason, "REASONING_STATUS_INVALID")

    def test_9_consistent_accepted(self):
        out = _out()
        result = import_with_fake(out, run_dir=consistent_run())
        self.assertEqual(result.summary["source_reasoning_status"], "CONSISTENT")
        self.assertEqual(result.summary["import_status"],
                         versions.IMPORTED_VERIFIED_ODIN)

    def test_10_contradiction_accepted(self):
        out = _out()
        result = import_with_fake(out, run_dir=contradiction_run())
        self.assertEqual(result.summary["source_reasoning_status"],
                         "CONTRADICTION_DETECTED")
        self.assertEqual(result.summary["import_status"],
                         versions.IMPORTED_VERIFIED_ODIN)
        self.assertEqual(result.summary["contradiction_count"], 1)

    def test_12_nonempty_output_dir_refused(self):
        out = _out()
        os.makedirs(out)
        with open(os.path.join(out, "rogue"), "w") as f:
            f.write("x")
        with self.assertRaises(ComponentPathError) as cm:
            import_with_fake(out)
        self.assertEqual(cm.exception.reason, "OUTPUT_DIR_NOT_EMPTY")

    def test_13_valid_import_writes_all_files(self):
        out = _out()
        import_with_fake(out)
        for name in (versions.SUMMARY_NAME, versions.REPORT_COPY_NAME,
                     versions.TRACE_COPY_NAME, versions.CLAIMS_COPY_NAME,
                     versions.REPLAY_REPORT_NAME, versions.CHECKSUMS_NAME):
            self.assertTrue(os.path.isfile(os.path.join(out, name)), name)
        # exactly six, nothing else
        self.assertEqual(set(os.listdir(out)),
                         {versions.SUMMARY_NAME, versions.REPORT_COPY_NAME,
                          versions.TRACE_COPY_NAME, versions.CLAIMS_COPY_NAME,
                          versions.REPLAY_REPORT_NAME, versions.CHECKSUMS_NAME})

    def test_14_copies_not_rewritten(self):
        run = consistent_run()
        out = _out()
        import_with_fake(out, run_dir=run)
        # byte-identical to the source files
        for src, cp in ((versions.ODIN_REPORT_NAME, versions.REPORT_COPY_NAME),
                        (versions.ODIN_TRACE_NAME, versions.TRACE_COPY_NAME),
                        (versions.ODIN_CLAIMS_NAME, versions.CLAIMS_COPY_NAME)):
            with open(os.path.join(run, src), "rb") as f:
                src_bytes = f.read()
            with open(os.path.join(out, cp), "rb") as f:
                cp_bytes = f.read()
            self.assertEqual(src_bytes, cp_bytes, f"{cp} was rewritten")

    def test_15_summary_is_canonical(self):
        out = _out()
        result = import_with_fake(out)
        with open(os.path.join(out, versions.SUMMARY_NAME), "rb") as f:
            raw = f.read()
        self.assertEqual(canonical_bytes(result.summary), raw)

    def test_16_17_18_copies_are_canonical(self):
        out = _out()
        import_with_fake(out)
        for name in (versions.REPORT_COPY_NAME, versions.TRACE_COPY_NAME,
                     versions.CLAIMS_COPY_NAME):
            with open(os.path.join(out, name), "rb") as f:
                raw = f.read()
            obj = json.loads(raw.decode())
            self.assertEqual(canonical_bytes(obj), raw, f"{name} not canonical")

    def test_19_replay_report_written(self):
        out = _out()
        import_with_fake(out)
        with open(os.path.join(out, versions.REPLAY_REPORT_NAME),
                  encoding="utf-8") as f:
            text = f.read()
        self.assertIn("ODIN Reasoning Import Report", text)
        self.assertIn("truth_claim: none", text)
        self.assertIn("does not prove that any claim is true", text)

    def test_20_checksums_written(self):
        out = _out()
        import_with_fake(out)
        with open(os.path.join(out, versions.CHECKSUMS_NAME),
                  encoding="utf-8") as f:
            lines = [ln for ln in f.read().splitlines() if ln.strip()]
        self.assertEqual(len(lines), 5)

    def test_proof_step_count_preserved(self):
        out = _out()
        result = import_with_fake(out, run_dir=contradiction_run())
        self.assertEqual(result.summary["proof_step_count"], 2)
        self.assertEqual(result.summary["claim_count"], 2)

    def test_cli_import_exit_codes(self):
        import histor_odin
        import argparse
        ns = argparse.Namespace(odin_root=HERE, run=consistent_run(), out=_out())
        self.assertEqual(histor_odin.cmd_import_reasoning(
            ns, odin_verifier=FakeOdinVerifier()), 0)
        ns2 = argparse.Namespace(odin_root=HERE, run="/no/such", out=_out())
        self.assertEqual(histor_odin.cmd_import_reasoning(
            ns2, odin_verifier=FakeOdinVerifier()), 2)
        ns3 = argparse.Namespace(odin_root=HERE, run=consistent_run(), out=_out())
        self.assertEqual(histor_odin.cmd_import_reasoning(
            ns3, odin_verifier=FakeOdinVerifier(ok=False)), 1)
        # INVALID_INPUT -> exit 1
        ns4 = argparse.Namespace(
            odin_root=HERE,
            run=make_run_dir(report_obj(reasoning_status="INVALID_INPUT")),
            out=_out())
        self.assertEqual(histor_odin.cmd_import_reasoning(
            ns4, odin_verifier=FakeOdinVerifier()), 1)


if __name__ == "__main__":
    unittest.main()
