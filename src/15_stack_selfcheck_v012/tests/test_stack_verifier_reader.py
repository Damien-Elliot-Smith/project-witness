import os

from stack_selfcheck_lib import report as report_mod
from stack_selfcheck_lib.errors import CheckError
from tests import synthetic
from tests._helpers import TempCase


class TestStackVerifierReader(TempCase):
    def _sv(self, **kw):
        run = os.path.join(self.work, "sv_%d" % len(os.listdir(self.work)))
        return synthetic.build_stack_verifier_output(run, **kw)

    def test_valid_stack_verifier_accepted(self):
        report, _ = report_mod.build_selfcheck_report(self.inventory(), self._sv())
        self.assertEqual(report["stack_verifier_status"], "STACK_VERIFIER_OUTPUT_VERIFIED")

    def test_not_provided_accepted(self):
        report, _ = report_mod.build_selfcheck_report(self.inventory())
        self.assertEqual(report["stack_verifier_status"], "NOT_PROVIDED")

    def test_bad_status_refused(self):
        sv = self._sv(stack_verification_status="FAILED_SOURCE_VERIFY")
        with self.assertRaises(CheckError):
            report_mod.build_selfcheck_report(self.inventory(), sv)

    def test_truth_boundary_false_refused(self):
        sv = self._sv(truth_boundary_valid=False)
        with self.assertRaises(CheckError):
            report_mod.build_selfcheck_report(self.inventory(), sv)

    def test_atlas_vocabulary_false_refused(self):
        sv = self._sv(atlas_vocabulary_valid=False)
        with self.assertRaises(CheckError):
            report_mod.build_selfcheck_report(self.inventory(), sv)
