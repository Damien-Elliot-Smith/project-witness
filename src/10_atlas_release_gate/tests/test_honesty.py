import os

from atlas_release_gate_lib import canonical, verifier
from atlas_release_gate_lib.errors import VerifyError, RELEASE_GATE_PASSED
from tests._helpers import TempCase


class TestHonesty(TempCase):
    def test_valid_run_has_no_truth_claims(self):
        out_dir, outcome = self.run_gate()
        self.assertEqual(outcome.status, RELEASE_GATE_PASSED)
        # A clean passed run verifies, meaning the truth scan found nothing.
        self.assertTrue(verifier.verify(out_dir).ok)

    def test_truth_claim_in_report_fails_verify(self):
        out_dir, _ = self.run_gate()
        path = os.path.join(out_dir, "atlas_release_gate_report.json")
        report = canonical.load_json(path)
        report["known_limitations"].append("The claims are true.")
        canonical.write_canonical(path, report)
        self.rebuild_checksums(out_dir)
        with self.assertRaises(VerifyError):
            verifier.verify(out_dir)

    def test_authentic_claim_fails_verify(self):
        out_dir, _ = self.run_gate()
        path = os.path.join(out_dir, "atlas_release_gate_report.json")
        report = canonical.load_json(path)
        report["known_limitations"].append("The files are authentic.")
        canonical.write_canonical(path, report)
        self.rebuild_checksums(out_dir)
        with self.assertRaises(VerifyError):
            verifier.verify(out_dir)

    def test_negated_truth_statement_is_allowed(self):
        # The honest limitation "does not prove truth" must NOT trip the scan.
        out_dir, _ = self.run_gate()
        self.assertTrue(verifier.verify(out_dir).ok)
