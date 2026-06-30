import os

from stack_selfcheck_lib import canonical, verifier
from stack_selfcheck_lib.errors import VerifyError
from tests._helpers import TempCase


class TestHonesty(TempCase):
    def _out(self):
        return self.build_output(self.inventory())

    def test_clean_passes(self):
        self.assertTrue(verifier.verify(self._out()).ok)

    def test_truth_claim_in_report_fails(self):
        out = self._out()
        path = os.path.join(out, "stack_selfcheck_report.json")
        rep = canonical.load_json(path)
        rep["known_limitations"].append("The stack proves reality.")
        canonical.write_canonical(path, rep); self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_truth_claim_in_steps_fails(self):
        out = self._out()
        path = os.path.join(out, "stack_selfcheck_steps.json")
        steps = canonical.load_json(path)
        steps["steps"][0]["note"] = "The evidence is true."
        canonical.write_canonical(path, steps); self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_negated_limitations_allowed(self):
        self.assertTrue(verifier.verify(self._out()).ok)
