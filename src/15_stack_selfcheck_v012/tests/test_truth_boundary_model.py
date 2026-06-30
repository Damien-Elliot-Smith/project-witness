"""v0.1.2 truth-boundary phrase-model compatibility tests.

These exercise documentation_checks directly: equivalent honest wording is
accepted, markdown emphasis does not break negation, the literal phrase is still
accepted, the vacuous case is accepted, and affirmative truth-like and
out-of-scope feature claims are still refused.
"""

import os
import tempfile
import unittest

from stack_selfcheck_lib import documentation_checks as dc
from stack_selfcheck_lib.errors import CheckError


def _comp(text, **flags):
    root = tempfile.mkdtemp()
    with open(os.path.join(root, "README.md"), "w", encoding="utf-8") as handle:
        handle.write(text)
    comp = {"component_id": "c", "root_path": root}
    comp.update(flags)
    return comp


def _truth_refused(text):
    try:
        dc.check_truth_boundary(_comp(text))
        return False
    except CheckError:
        return True


def _boundary_present(text, **flags):
    try:
        dc.check_boundaries(_comp(text, **flags))
        return True
    except CheckError:
        return False


class TestLiteralAndEquivalents(unittest.TestCase):
    def test_literal_phrase_accepted(self):
        self.assertTrue(_boundary_present("# c\nIt does not prove truth.\n"))
        self.assertFalse(_truth_refused("# c\nIt does not prove truth.\n"))

    def test_equivalent_phrases_accepted(self):
        for phrase in (
            "It does not prove evidence contents are true.",
            "It does not prove ODIN claims are true.",
            "It does not verify external reality.",
            "It does not prove files are authentic.",
            "It does not prove sources are trusted.",
            "Structural verification only.",
            "It records structure, hashes, and statuses only.",
        ):
            text = "# c\n" + phrase + "\n"
            self.assertTrue(_boundary_present(text), phrase)
            self.assertFalse(_truth_refused(text), phrase)

    def test_list_governed_by_heading_accepted(self):
        text = ("# c\nIt does not modify the registry, run workflows, "
                "or prove truth.\n")
        self.assertTrue(_boundary_present(text))
        self.assertFalse(_truth_refused(text))

    def test_vacuous_accepted(self):
        text = "# c\nA deterministic action gate. It records receipts.\n"
        self.assertTrue(_boundary_present(text))
        self.assertFalse(_truth_refused(text))


class TestMarkdownNegation(unittest.TestCase):
    def test_bold_negation_accepted(self):
        for text in (
            "# c\nIt does **not** prove truth.\n",
            "# c\nIt does *not* verify external reality.\n",
            "# c\nIt does not **prove** evidence contents are true.\n",
        ):
            self.assertFalse(_truth_refused(text), text)
            self.assertTrue(_boundary_present(text), text)

    def test_out_of_scope_list_item_accepted(self):
        text = "# c\nIt does not prove truth.\n## Out of scope\n\n- LLM reasoning.\n"
        self.assertFalse(_truth_refused(text))


class TestAffirmativeStillRefused(unittest.TestCase):
    def test_affirmative_truth_refused(self):
        for claim in (
            "This component proves the evidence contents are true.",
            "The ODIN claims are true.",
            "Evidence is true.",
            "All files are authentic.",
            "The sources are trusted.",
            "This case proves reality.",
            "The stack proves reality.",
            "It proves truth.",
        ):
            self.assertTrue(_truth_refused("# c\n" + claim + "\n"), claim)

    def test_affirmative_feature_refused(self):
        for claim in (
            "This component uses an LLM.",
            "It is powered by an LLM.",
            "It supports signing.",
            "It signs the outputs.",
            "It supports external anchoring.",
            "It provides a GUI.",
            "It supports concurrency.",
            "It supports queues.",
            "It uses natural-language interpretation.",
        ):
            self.assertTrue(_truth_refused("# c\n" + claim + "\n"), claim)

    def test_boolean_true_not_a_truth_claim(self):
        # A benign technical statement about a boolean flag is not refused.
        text = "# c\nThe verifier's own ok flag is true.\nIt does not prove truth.\n"
        self.assertFalse(_truth_refused(text))


if __name__ == "__main__":
    unittest.main()
