# tests/test_builder.py
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import case_bundle_v02_lib.builder as builder  # noqa: E402
from case_bundle_v02_lib.canonical import canonical_bytes  # noqa: E402
from case_bundle_v02_lib.errors import (  # noqa: E402
    BuildPathError, InputCaseError, CaseIdMismatchError)
from case_bundle_v02_lib import versions  # noqa: E402
from tests.helpers import (  # noqa: E402
    make_sentinel_case, make_aletheia_case, make_odin_case, build_bundle,
    out_dir, FailingInputVerifier, CID)


class TestBuilder(unittest.TestCase):
    def test_4_missing_sentinel_case_refused(self):
        with self.assertRaises(BuildPathError) as cm:
            builder.build_bundle(
                sentinel_case="/no/such", aletheia_case=make_aletheia_case(),
                odin_case=make_odin_case(), out_dir=out_dir())
        self.assertEqual(cm.exception.reason, "SENTINEL_CASE_MISSING")

    def test_5_missing_aletheia_case_refused(self):
        with self.assertRaises(BuildPathError) as cm:
            builder.build_bundle(
                sentinel_case=make_sentinel_case(), aletheia_case="/no/such",
                odin_case=make_odin_case(), out_dir=out_dir())
        self.assertEqual(cm.exception.reason, "ALETHEIA_CASE_MISSING")

    def test_6_missing_odin_case_refused(self):
        with self.assertRaises(BuildPathError) as cm:
            builder.build_bundle(
                sentinel_case=make_sentinel_case(),
                aletheia_case=make_aletheia_case(), odin_case="/no/such",
                out_dir=out_dir())
        self.assertEqual(cm.exception.reason, "ODIN_CASE_MISSING")

    def test_7_sentinel_verify_failure_refused(self):
        with self.assertRaises(InputCaseError) as cm:
            build_bundle(input_verifier=FailingInputVerifier("sentinel"))
        self.assertEqual(cm.exception.bundle_status,
                         versions.FAILED_SENTINEL_CASE_VERIFY)

    def test_8_aletheia_verify_failure_refused(self):
        with self.assertRaises(InputCaseError) as cm:
            build_bundle(input_verifier=FailingInputVerifier("aletheia"))
        self.assertEqual(cm.exception.bundle_status,
                         versions.FAILED_ALETHEIA_CASE_VERIFY)

    def test_9_odin_verify_failure_refused(self):
        with self.assertRaises(InputCaseError) as cm:
            build_bundle(input_verifier=FailingInputVerifier("odin"))
        self.assertEqual(cm.exception.bundle_status,
                         versions.FAILED_ODIN_CASE_VERIFY)

    def test_10_case_id_mismatch_refused(self):
        with self.assertRaises(CaseIdMismatchError) as cm:
            build_bundle(
                sentinel=make_sentinel_case(case_id="case_001"),
                aletheia=make_aletheia_case(case_id="case_001"),
                odin=make_odin_case(case_id="case_OTHER"))
        self.assertEqual(cm.exception.bundle_status, "FAILED_CASE_ID_MISMATCH")

    def test_11_nonempty_output_dir_refused(self):
        out = out_dir()
        os.makedirs(out)
        with open(os.path.join(out, "rogue"), "w") as f:
            f.write("x")
        with self.assertRaises(BuildPathError) as cm:
            build_bundle(out)
        self.assertEqual(cm.exception.reason, "OUTPUT_DIR_NOT_EMPTY")

    def test_12_valid_build_writes_all(self):
        out = out_dir()
        build_bundle(out)
        for name in (versions.MANIFEST_NAME, versions.CHECKSUMS_NAME):
            self.assertTrue(os.path.isfile(os.path.join(out, name)), name)
        for sub, files in ((versions.SENTINEL_DIR, versions.SENTINEL_FILES),
                           (versions.ALETHEIA_DIR, versions.ALETHEIA_FILES),
                           (versions.ODIN_DIR, versions.ODIN_FILES)):
            for f in files:
                self.assertTrue(os.path.isfile(os.path.join(out, sub, f)),
                                f"{sub}/{f}")
        # exactly the allowed top-level entries
        self.assertEqual(
            set(os.listdir(out)),
            {versions.MANIFEST_NAME, versions.CHECKSUMS_NAME} | set(versions.SUBFOLDERS))

    def test_13_subcase_files_copied_byte_identically(self):
        sent, ale, odin = (make_sentinel_case(), make_aletheia_case(),
                           make_odin_case())
        out = out_dir()
        build_bundle(out, sentinel=sent, aletheia=ale, odin=odin)
        for src_dir, sub, files in (
                (sent, versions.SENTINEL_DIR, versions.SENTINEL_FILES),
                (ale, versions.ALETHEIA_DIR, versions.ALETHEIA_FILES),
                (odin, versions.ODIN_DIR, versions.ODIN_FILES)):
            for f in files:
                with open(os.path.join(src_dir, f), "rb") as a:
                    src = a.read()
                with open(os.path.join(out, sub, f), "rb") as b:
                    cp = b.read()
                self.assertEqual(src, cp, f"{sub}/{f} not byte-identical")

    def test_14_manifest_is_canonical(self):
        out = out_dir()
        result = build_bundle(out)
        with open(os.path.join(out, versions.MANIFEST_NAME), "rb") as f:
            raw = f.read()
        self.assertEqual(canonical_bytes(result.manifest), raw)

    def test_15_checksums_written(self):
        out = out_dir()
        build_bundle(out)
        with open(os.path.join(out, versions.CHECKSUMS_NAME),
                  encoding="utf-8") as f:
            lines = [ln for ln in f.read().splitlines() if ln.strip()]
        self.assertEqual(len(lines), 14)

    def test_contradiction_packages(self):
        out = out_dir()
        result = build_bundle(out, odin=make_odin_case(
            reasoning_status="CONTRADICTION_DETECTED", claim_count=2,
            contradiction_count=1))
        self.assertEqual(result.manifest["odin"]["source_reasoning_status"],
                         "CONTRADICTION_DETECTED")
        self.assertEqual(result.manifest["bundle_status"],
                         "BUNDLED_VERIFIED_CASE")

    def test_cli_build_exit_codes(self):
        import case_bundle_v02
        import argparse
        ns = argparse.Namespace(
            sentinel_case=make_sentinel_case(), aletheia_case=make_aletheia_case(),
            odin_case=make_odin_case(), out=out_dir())
        self.assertEqual(case_bundle_v02.cmd_build(ns), 0)
        ns2 = argparse.Namespace(
            sentinel_case="/no/such", aletheia_case=make_aletheia_case(),
            odin_case=make_odin_case(), out=out_dir())
        self.assertEqual(case_bundle_v02.cmd_build(ns2), 2)
        ns3 = argparse.Namespace(
            sentinel_case=make_sentinel_case(case_id="case_001"),
            aletheia_case=make_aletheia_case(case_id="case_001"),
            odin_case=make_odin_case(case_id="case_X"), out=out_dir())
        self.assertEqual(case_bundle_v02.cmd_build(ns3), 1)


if __name__ == "__main__":
    unittest.main()
