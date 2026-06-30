from atlas_release_gate_lib import documentation_checks
from atlas_release_gate_lib.errors import (
    FAILED_DOCUMENTATION_CHECK, FAILED_HONESTY_CHECK, RELEASE_GATE_PASSED)
from atlas_release_gate_lib.fixtures import (
    GOOD_README, GOOD_KNOWN_LIMITATIONS,
    FROZEN_ATLAS_README, FROZEN_ATLAS_KNOWN_LIMITATIONS)
from tests._helpers import TempCase

# Real frozen Atlas Registry v0.1 wording: expresses the honesty boundary via
# equivalent statements and does NOT contain "does not modify the registry".
_FROZEN_DOCS = FROZEN_ATLAS_README + FROZEN_ATLAS_KNOWN_LIMITATIONS

# Docs with no read-only / no-workflow / no-truth boundary at all.
_NO_BOUNDARY_DOCS = (
    "# Atlas\n"
    "This document describes the registry contents and how terms are listed.\n"
    "It explains the file layout and the version number.\n"
)


class TestDocumentationChecks(TempCase):
    def test_good_docs_pass(self):
        text = GOOD_README + GOOD_KNOWN_LIMITATIONS
        self.assertEqual(documentation_checks.check_documentation(text), [])
        self.assertEqual(documentation_checks.check_honesty(text), [])

    def test_missing_documentation_refused(self):
        bad = ("# Atlas\nThe registry is read-only.\n"
               "It does not run workflows.\nIt does not prove truth.\n")
        _, outcome = self.run_gate(readme_text=bad, limitations_text="# limits\n")
        self.assertEqual(outcome.status, FAILED_DOCUMENTATION_CHECK)

    # --- Honesty check accepts the real frozen Atlas wording ---

    def test_frozen_atlas_wording_passes_honesty(self):
        # Must pass WITHOUT requiring "does not modify the registry".
        self.assertNotIn("does not modify the registry", _FROZEN_DOCS.lower())
        self.assertEqual(documentation_checks.check_honesty(_FROZEN_DOCS), [])

    def test_frozen_atlas_wording_passes_documentation(self):
        self.assertEqual(documentation_checks.check_documentation(_FROZEN_DOCS), [])

    def test_gate_passes_on_frozen_atlas_wording(self):
        _, outcome = self.run_gate(
            readme_text=FROZEN_ATLAS_README,
            limitations_text=FROZEN_ATLAS_KNOWN_LIMITATIONS)
        self.assertEqual(outcome.status, RELEASE_GATE_PASSED)

    def test_records_vocabulary_satisfies_read_only_concept(self):
        # "records vocabulary" alone should satisfy the read-only concept.
        text = ("It records vocabulary.\nIt does not run workflows.\n"
                "It does not decide truth.\n")
        self.assertEqual(documentation_checks.check_honesty(text), [])

    # --- Negative: docs lacking any boundary must fail the honesty check ---

    def test_no_boundary_docs_fail_honesty(self):
        missing = documentation_checks.check_honesty(_NO_BOUNDARY_DOCS)
        self.assertNotEqual(missing, [])
        # all three concept groups should be reported missing
        self.assertEqual(
            set(missing),
            {"read_only_or_vocabulary", "no_workflows_or_calls",
             "no_prove_or_decide_truth"})

    def test_partial_boundary_fails_honesty(self):
        # Has read-only but neither no-workflow nor no-truth.
        text = "Atlas is a read-only registry of terms.\n"
        missing = documentation_checks.check_honesty(text)
        self.assertIn("no_workflows_or_calls", missing)
        self.assertIn("no_prove_or_decide_truth", missing)
