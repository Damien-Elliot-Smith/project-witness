from stack_verifier_lib import report as report_mod
from stack_verifier_lib.errors import CheckError
from tests._helpers import TempCase, COORD


class TestAtlasChecks(TempCase):
    def _build(self, **opts):
        return report_mod.build_stack_report(COORD, self.coord_source(registry_opts=opts))

    def test_missing_required_status_refused(self):
        with self.assertRaises(CheckError):
            self._build(omit_status="CONSISTENT")

    def test_missing_required_predicate_refused(self):
        with self.assertRaises(CheckError):
            self._build(omit_predicate="evidence.present")

    def test_atlas_truth_claim_status_refused(self):
        with self.assertRaises(CheckError):
            self._build(truth_claim_status=True)

    def test_atlas_truth_claim_predicate_refused(self):
        with self.assertRaises(CheckError):
            self._build(truth_claim_predicate=True)

    def test_forbidden_action_refused(self):
        with self.assertRaises(CheckError):
            self._build(forbidden_action="WRITE_FILE")
