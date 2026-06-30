# tests/test_convert.py
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bridge  # noqa: E402
from aletheia_odin_bridge.canonical import canonical_bytes  # noqa: E402
from aletheia_odin_bridge.errors import (  # noqa: E402
    ComponentPathError, AletheiaVerifyError, ManifestError, OdinValidateError)
from aletheia_odin_bridge import versions  # noqa: E402
from tests.helpers import (  # noqa: E402
    manifest, make_bundle_dir, convert_with_fakes, FakeAletheiaVerifier,
    FakeOdinValidator)


def _out():
    return os.path.join(tempfile.mkdtemp(prefix="bridge_out_"), "out")


class TestConvert(unittest.TestCase):
    def test_5_missing_bundle_refused(self):
        with self.assertRaises(ComponentPathError) as cm:
            bridge.convert(aletheia_root=HERE, odin_root=HERE,
                           bundle_dir="/no/such/bundle", out_dir=_out(),
                           aletheia_verifier=FakeAletheiaVerifier(),
                           odin_validator=FakeOdinValidator())
        self.assertEqual(cm.exception.reason, "BUNDLE_MISSING")

    def test_6_aletheia_verify_failure_refused(self):
        with self.assertRaises(AletheiaVerifyError) as cm:
            convert_with_fakes(_out(), aletheia_ok=False)
        self.assertEqual(cm.exception.reason, "ALETHEIA_VERIFY_FAILED")

    def test_7_missing_aletheia_root_refused(self):
        with self.assertRaises(ComponentPathError) as cm:
            convert_with_fakes(_out(), aletheia_root="/no/such/aletheia")
        self.assertEqual(cm.exception.reason, "ALETHEIA_ROOT_MISSING")

    def test_8_missing_odin_root_refused(self):
        with self.assertRaises(ComponentPathError) as cm:
            convert_with_fakes(_out(), odin_root="/no/such/odin")
        self.assertEqual(cm.exception.reason, "ODIN_ROOT_MISSING")

    def test_15_odin_validation_failure_refused(self):
        with self.assertRaises(OdinValidateError) as cm:
            convert_with_fakes(_out(), odin_ok=False)
        self.assertEqual(cm.exception.reason, "ODIN_VALIDATE_FAILED")

    def test_4_non_verified_present_refused_in_convert(self):
        with self.assertRaises(ManifestError) as cm:
            convert_with_fakes(_out(),
                               manifest_dict=manifest(evidence_status="BUNDLED"))
        self.assertEqual(cm.exception.reason, "STATUS_NOT_VERIFIED_PRESENT")

    def test_16_valid_conversion_writes_all_files(self):
        out = _out()
        result = convert_with_fakes(out)
        for name in (versions.ODIN_CLAIMS_NAME, versions.BRIDGE_REPORT_NAME,
                     versions.MANIFEST_COPY_NAME, versions.CHECKSUMS_NAME):
            self.assertTrue(os.path.isfile(os.path.join(out, name)), name)
        self.assertEqual(result.report["bridge_status"], "CONVERTED")
        self.assertEqual(result.report["odin_validation_status"], "VALID")

    def test_17_bridge_report_canonical(self):
        out = _out()
        result = convert_with_fakes(out)
        with open(os.path.join(out, versions.BRIDGE_REPORT_NAME), "rb") as f:
            raw = f.read()
        self.assertEqual(canonical_bytes(result.report), raw)
        self.assertTrue(raw.endswith(b"\n"))

    def test_18_checksums_written(self):
        out = _out()
        convert_with_fakes(out)
        p = os.path.join(out, versions.CHECKSUMS_NAME)
        self.assertTrue(os.path.isfile(p))
        with open(p, encoding="utf-8") as f:
            lines = [ln for ln in f.read().splitlines() if ln.strip()]
        self.assertEqual(len(lines), 3)

    def test_skip_odin_validation_when_no_root(self):
        out = _out()
        result = convert_with_fakes(out, odin_root=None)
        self.assertEqual(result.report["odin_validation_status"], "SKIPPED")

    def test_no_evidence_file_copied(self):
        # The bridge must NOT copy the evidence file (claim conversion, not custody).
        out = _out()
        convert_with_fakes(out)
        names = set(os.listdir(out))
        self.assertNotIn("evidence", names)
        self.assertNotIn("evidence_001.bin", names)

    def test_nonempty_output_dir_refused(self):
        out = _out()
        os.makedirs(out)
        with open(os.path.join(out, "rogue"), "w") as f:
            f.write("x")
        with self.assertRaises(ComponentPathError) as cm:
            convert_with_fakes(out)
        self.assertEqual(cm.exception.reason, "OUTPUT_DIR_NOT_EMPTY")

    def test_manifest_copy_matches_source(self):
        out = _out()
        m = manifest(evidence_id="evidence_009", case_id="case_009")
        bundle = make_bundle_dir(m)
        convert_with_fakes(out, bundle_dir=bundle)
        with open(os.path.join(out, versions.MANIFEST_COPY_NAME)) as f:
            copied = json.load(f)
        self.assertEqual(copied["evidence_id"], "evidence_009")
        self.assertEqual(copied["case_id"], "case_009")


class TestConvertCLI(unittest.TestCase):
    """CLI-level exit codes with injected fakes."""

    def _args(self, out, odin_root=HERE):
        import argparse
        ns = argparse.Namespace()
        ns.aletheia_root = HERE
        ns.odin_root = odin_root
        ns.bundle = make_bundle_dir(manifest())
        ns.out = out
        return ns

    def test_cli_convert_success_exit_0(self):
        rc = bridge.cmd_convert(self._args(_out()),
                                aletheia_verifier=FakeAletheiaVerifier(),
                                odin_validator=FakeOdinValidator())
        self.assertEqual(rc, 0)

    def test_cli_convert_path_error_exit_2(self):
        ns = self._args(_out())
        ns.bundle = "/no/such/bundle"
        rc = bridge.cmd_convert(ns, aletheia_verifier=FakeAletheiaVerifier(),
                                odin_validator=FakeOdinValidator())
        self.assertEqual(rc, 2)

    def test_cli_convert_aletheia_fail_exit_1(self):
        rc = bridge.cmd_convert(self._args(_out()),
                                aletheia_verifier=FakeAletheiaVerifier(ok=False),
                                odin_validator=FakeOdinValidator())
        self.assertEqual(rc, 1)

    def test_cli_convert_odin_fail_exit_1(self):
        rc = bridge.cmd_convert(self._args(_out()),
                                aletheia_verifier=FakeAletheiaVerifier(),
                                odin_validator=FakeOdinValidator(ok=False))
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
