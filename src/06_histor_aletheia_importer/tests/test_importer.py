# tests/test_importer.py
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import histor_aletheia_importer.importer as importer  # noqa: E402
from histor_aletheia_importer.canonical import canonical_bytes  # noqa: E402
from histor_aletheia_importer.errors import (  # noqa: E402
    ComponentPathError, AletheiaVerifyError, ManifestError)
from histor_aletheia_importer import versions  # noqa: E402
from tests.helpers import (  # noqa: E402
    manifest, make_bundle_dir, import_with_fake, FakeAletheiaVerifier)


def _out():
    return os.path.join(tempfile.mkdtemp(prefix="hist_case_"), "case")


class TestImporter(unittest.TestCase):
    def test_2_missing_aletheia_root_refused(self):
        with self.assertRaises(ComponentPathError) as cm:
            import_with_fake(_out(), aletheia_root="/no/such/aletheia")
        self.assertEqual(cm.exception.reason, "ALETHEIA_ROOT_MISSING")

    def test_3_missing_bundle_refused(self):
        with self.assertRaises(ComponentPathError) as cm:
            importer.import_evidence(
                aletheia_root=HERE, bundle_dir="/no/such/bundle", out_dir=_out(),
                aletheia_verifier=FakeAletheiaVerifier())
        self.assertEqual(cm.exception.reason, "BUNDLE_MISSING")

    def test_4_aletheia_verify_failure_refused(self):
        with self.assertRaises(AletheiaVerifyError) as cm:
            import_with_fake(_out(), ok=False)
        self.assertEqual(cm.exception.reason, "ALETHEIA_VERIFY_FAILED")

    def test_5_non_verified_present_refused(self):
        with self.assertRaises(ManifestError) as cm:
            import_with_fake(_out(),
                             manifest_dict=manifest(evidence_status="BUNDLED"))
        self.assertEqual(cm.exception.reason, "STATUS_NOT_VERIFIED_PRESENT")

    def test_6_missing_manifest_field_refused(self):
        with self.assertRaises(ManifestError) as cm:
            import_with_fake(_out(),
                             manifest_dict=manifest(drop=["source_file_sha256"]))
        self.assertEqual(cm.exception.reason, "MANIFEST_FIELD_MISSING")

    def test_9_nonempty_output_dir_refused(self):
        out = _out()
        os.makedirs(out)
        with open(os.path.join(out, "rogue"), "w") as f:
            f.write("x")
        with self.assertRaises(ComponentPathError) as cm:
            import_with_fake(out)
        self.assertEqual(cm.exception.reason, "OUTPUT_DIR_NOT_EMPTY")

    def test_10_valid_import_writes_all_files(self):
        out = _out()
        result = import_with_fake(out)
        for name in (versions.SUMMARY_NAME, versions.MANIFEST_COPY_NAME,
                     versions.REPLAY_REPORT_NAME, versions.CHECKSUMS_NAME):
            self.assertTrue(os.path.isfile(os.path.join(out, name)), name)
        self.assertEqual(result.summary["import_status"],
                         versions.IMPORTED_VERIFIED_ALETHEIA)

    def test_11_evidence_file_not_copied(self):
        out = _out()
        import_with_fake(out)
        names = set(os.listdir(out))
        self.assertNotIn("evidence", names)
        self.assertNotIn("evidence_001.bin", names)
        # Exactly the four allowed files, nothing else.
        self.assertEqual(names, {versions.SUMMARY_NAME, versions.MANIFEST_COPY_NAME,
                                 versions.REPLAY_REPORT_NAME, versions.CHECKSUMS_NAME})

    def test_12_summary_is_canonical(self):
        out = _out()
        result = import_with_fake(out)
        with open(os.path.join(out, versions.SUMMARY_NAME), "rb") as f:
            raw = f.read()
        self.assertEqual(canonical_bytes(result.summary), raw)
        self.assertTrue(raw.endswith(b"\n"))

    def test_13_manifest_copy_is_canonical(self):
        out = _out()
        import_with_fake(out)
        p = os.path.join(out, versions.MANIFEST_COPY_NAME)
        with open(p, "rb") as f:
            raw = f.read()
        obj = json.loads(raw.decode())
        self.assertEqual(canonical_bytes(obj), raw)

    def test_14_replay_report_written(self):
        out = _out()
        import_with_fake(out)
        p = os.path.join(out, versions.REPLAY_REPORT_NAME)
        with open(p, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("Aletheia Evidence Bundle Import Report", text)
        self.assertIn("truth_claim: none", text)
        self.assertIn("does not prove the evidence contents are true", text)

    def test_15_checksums_written(self):
        out = _out()
        import_with_fake(out)
        p = os.path.join(out, versions.CHECKSUMS_NAME)
        with open(p, encoding="utf-8") as f:
            lines = [ln for ln in f.read().splitlines() if ln.strip()]
        self.assertEqual(len(lines), 3)

    def test_status_and_shas_preserved(self):
        out = _out()
        m = manifest(source_sha="a" * 64, bundled_sha="a" * 64)
        result = import_with_fake(out, manifest_dict=m)
        s = result.summary
        self.assertEqual(s["source_evidence_status"], "VERIFIED_PRESENT")
        self.assertEqual(s["source_file_sha256"], "a" * 64)
        self.assertEqual(s["bundled_file_sha256"], "a" * 64)

    def test_cli_import_exit_codes(self):
        import histor_aletheia
        import argparse
        # success
        ns = argparse.Namespace(aletheia_root=HERE,
                                bundle=make_bundle_dir(manifest()), out=_out())
        self.assertEqual(
            histor_aletheia.cmd_import_evidence(
                ns, aletheia_verifier=FakeAletheiaVerifier()), 0)
        # path error -> 2
        ns2 = argparse.Namespace(aletheia_root=HERE, bundle="/no/such", out=_out())
        self.assertEqual(
            histor_aletheia.cmd_import_evidence(
                ns2, aletheia_verifier=FakeAletheiaVerifier()), 2)
        # aletheia verify fail -> 1
        ns3 = argparse.Namespace(aletheia_root=HERE,
                                 bundle=make_bundle_dir(manifest()), out=_out())
        self.assertEqual(
            histor_aletheia.cmd_import_evidence(
                ns3, aletheia_verifier=FakeAletheiaVerifier(ok=False)), 1)


if __name__ == "__main__":
    unittest.main()
