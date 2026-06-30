import os

from companion_lib import canonical, verifier
from companion_lib.errors import VerifyError
from tests._helpers import TempCase


class TestHonesty(TempCase):
    def test_clean_run_passes_truth_scan(self):
        self.assertTrue(verifier.verify(self.run_companion().out_dir).ok)

    def test_truth_claim_in_report_fails(self):
        out = self.run_companion().out_dir
        path = os.path.join(out, "companion_report.json")
        rep = canonical.load_json(path)
        rep["known_limitations"].append("The evidence is true.")
        canonical.write_canonical(path, rep)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_negated_limitations_allowed(self):
        # the honest "does not prove ... true" limitations must not trip the scan
        self.assertTrue(verifier.verify(self.run_companion().out_dir).ok)
