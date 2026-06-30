from stack_selfcheck_lib import report as report_mod
from stack_selfcheck_lib.errors import CheckError
from tests._helpers import TempCase

# a clean, fully-negated doc baseline
_CLEAN = ("# c\nThis does not prove truth. It does not run workflows. "
          "It does not copy evidence contents. Atlas is read-only. "
          "It does not sign or externally anchor. It does not use an LLM. "
          "No GUI. No queues or concurrency. No natural language.\n")


class TestDocumentationChecks(TempCase):
    def test_boundary_present_accepted(self):
        report, _ = report_mod.build_selfcheck_report(self.inventory())
        self.assertTrue(report["documentation_boundaries_present"])

    def _bad_doc(self, cid, text):
        inv = self.inventory()
        self.set_component_doc(cid, "README.md", text)
        self.set_component_doc(cid, "KNOWN_LIMITATIONS.md", text)
        with self.assertRaises(CheckError):
            report_mod.build_selfcheck_report(inv)

    def test_truth_token_without_disclaimer_refused(self):
        # A doc that uses a truth-domain token but never disclaims proving truth
        # (no negated truth statement, no structural marker) is still refused.
        self._bad_doc("histor_lite_v012",
                      "# c\nThe verdict field can take the value true here.\n")

    def test_vacuous_no_truth_tokens_accepted(self):
        # A component whose docs make no truth-domain claim at all needs no
        # truth-boundary disclaimer (it never claims to prove truth).
        inv = self.inventory()
        vac = ("# c\nA deterministic gate for one filesystem action. "
               "It records receipts and seals.\n")
        self.set_component_doc("histor_lite_v012", "README.md", vac)
        self.set_component_doc("histor_lite_v012", "KNOWN_LIMITATIONS.md", vac)
        report, _ = report_mod.build_selfcheck_report(inv)
        self.assertEqual(report["stack_selfcheck_status"], "STACK_SELFCHECK_PASSED")

    def test_missing_does_not_run_workflows_for_read_only_refused(self):
        # stack_verifier_v01 is read_only; drop its "does not run workflows"
        self._bad_doc("stack_verifier_v01",
                      "# c\nIt does not prove truth. It does not copy evidence contents.\n")

    def test_missing_does_not_copy_evidence_for_evidence_component_refused(self):
        # unified_case_manifest_v01 is an evidence component
        self._bad_doc("unified_case_manifest_v01",
                      "# c\nIt does not prove truth. It does not run workflows.\n")

    def test_honest_limitation_accepted(self):
        inv = self.inventory()
        self.set_component_doc("histor_lite_v012", "README.md", _CLEAN)
        report, _ = report_mod.build_selfcheck_report(inv)
        self.assertEqual(report["stack_selfcheck_status"], "STACK_SELFCHECK_PASSED")

    def _affirmative(self, claim):
        inv = self.inventory()
        text = _CLEAN + "\nThis component %s.\n" % claim
        self.set_component_doc("histor_lite_v012", "README.md", text)
        with self.assertRaises(CheckError):
            report_mod.build_selfcheck_report(inv)

    def test_affirmative_signing_refused(self):
        self._affirmative("supports signing")

    def test_affirmative_anchoring_refused(self):
        self._affirmative("supports external anchoring")

    def test_affirmative_llm_refused(self):
        self._affirmative("uses an LLM")

    def test_affirmative_gui_refused(self):
        self._affirmative("provides a GUI")

    def test_affirmative_queue_refused(self):
        self._affirmative("supports concurrency")
