import os

from stack_verifier_lib import report as report_mod
from stack_verifier_lib.errors import CheckError
from tests._helpers import TempCase, COMP


class TestManifestReader(TempCase):
    def test_valid_manifest_crosscheck(self):
        src = self.companion_source()
        man = self.manifest_output(COMP, src)
        report, _ = report_mod.build_stack_report(COMP, src, man)
        self.assertEqual(report["manifest_status"], "MANIFEST_VERIFIED")
        self.assertTrue(report["manifest_consistent"])

    def test_manifest_optional_not_provided(self):
        report, _ = report_mod.build_stack_report(COMP, self.companion_source())
        self.assertEqual(report["manifest_status"], "NOT_PROVIDED")

    def test_manifest_checksum_mismatch_refused(self):
        src = self.companion_source(); man = self.manifest_output(COMP, src)
        path = os.path.join(man, "source_index.json")
        with open(path, "ab") as h:
            h.write(b" ")
        with self.assertRaises(CheckError):
            report_mod.build_stack_report(COMP, src, man)

    def test_manifest_case_id_mismatch_refused(self):
        src = self.companion_source()
        man = self.manifest_output(COMP, src, override_case_id="case_tampered00000")
        with self.assertRaises(CheckError):
            report_mod.build_stack_report(COMP, src, man)

    def test_manifest_evidence_id_mismatch_refused(self):
        src = self.companion_source()
        man = self.manifest_output(COMP, src, override_evidence_id="evidence_other")
        with self.assertRaises(CheckError):
            report_mod.build_stack_report(COMP, src, man)

    def test_manifest_status_mismatch_refused(self):
        src = self.companion_source()
        man = self.manifest_output(COMP, src, override_status="PASS_WITH_ENVIRONMENTAL_EXCEPTIONS")
        with self.assertRaises(CheckError):
            report_mod.build_stack_report(COMP, src, man)

    def test_manifest_artifact_hash_mismatch_refused(self):
        src = self.companion_source()
        man = self.manifest_output(COMP, src, override_artifact_sha="b" * 64)
        with self.assertRaises(CheckError):
            report_mod.build_stack_report(COMP, src, man)
