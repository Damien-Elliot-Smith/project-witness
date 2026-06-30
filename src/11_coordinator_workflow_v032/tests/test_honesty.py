import os

from coordinator_v03_lib import canonical, verifier
from coordinator_v03_lib.errors import VerifyError
from tests._helpers import TempCase


class TestHonesty(TempCase):
    def _completed(self):
        out, _ = self.run_wf()
        return out

    def test_valid_run_has_no_truth_claims(self):
        self.assertTrue(verifier.verify(self._completed()).ok)

    def test_truth_claim_in_report_fails(self):
        out = self._completed()
        path = os.path.join(out, "workflow_report.json")
        rep = canonical.load_json(path)
        rep["known_limitations"].append("The evidence is true.")
        canonical.write_canonical(path, rep)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_truth_claim_in_atlas_validation_fails(self):
        out = self._completed()
        path = os.path.join(out, "atlas_validation_report.json")
        av = canonical.load_json(path)
        av["known_limitations"].append("The claims are true.")
        canonical.write_canonical(path, av)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_negated_truth_statements_allowed(self):
        # The honest limitations ("does not prove ... true") must not trip the scan.
        self.assertTrue(verifier.verify(self._completed()).ok)
