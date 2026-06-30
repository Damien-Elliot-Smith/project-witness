from atlas_release_gate_lib import feature_checks
from atlas_release_gate_lib.errors import FAILED_FORBIDDEN_FEATURE_CHECK
from atlas_release_gate_lib.fixtures import GOOD_README, GOOD_KNOWN_LIMITATIONS
from tests._helpers import TempCase

# Base honest doc plus an affirmative forbidden line, appended to README so the
# documentation and honesty steps still pass and the gate reaches step_007.
_HONEST = GOOD_README + GOOD_KNOWN_LIMITATIONS


def _names(violations):
    return {name for name, _ in violations}


class TestFeatureChecks(TempCase):
    def test_honest_limitations_no_false_positive(self):
        self.assertEqual(feature_checks.scan_forbidden_features(_HONEST), [])

    def test_affirmative_coordinator_detected(self):
        v = feature_checks.scan_forbidden_features(
            "Atlas supports Coordinator integration.")
        self.assertIn("coordinator_integration", _names(v))

    def test_affirmative_companion_detected(self):
        v = feature_checks.scan_forbidden_features(
            "Atlas provides Companion integration.")
        self.assertIn("companion_integration", _names(v))

    def test_affirmative_workflow_detected(self):
        v = feature_checks.scan_forbidden_features(
            "Atlas executes workflows at runtime.")
        self.assertIn("workflow_execution", _names(v))

    def test_affirmative_llm_detected(self):
        v = feature_checks.scan_forbidden_features(
            "Atlas uses an LLM for reasoning.")
        self.assertIn("llm", _names(v))

    def test_affirmative_signing_detected(self):
        v = feature_checks.scan_forbidden_features(
            "Atlas signs the release package.")
        self.assertIn("signing", _names(v))

    def test_gate_refuses_affirmative_coordinator(self):
        bad = GOOD_README + "\nAtlas supports Coordinator integration.\n"
        _, outcome = self.run_gate(readme_text=bad)
        self.assertEqual(outcome.status, FAILED_FORBIDDEN_FEATURE_CHECK)

    def test_gate_refuses_affirmative_llm(self):
        bad = GOOD_README + "\nAtlas uses an LLM for reasoning.\n"
        _, outcome = self.run_gate(readme_text=bad)
        self.assertEqual(outcome.status, FAILED_FORBIDDEN_FEATURE_CHECK)


class TestFrozenAtlasFeatureWording(TempCase):
    """Mirrors genuine frozen Atlas Registry v0.1 wording: forbidden terms as
    vocabulary / listed components / refused out-of-roadmap actions / out-of-
    scope items must NOT be flagged, while affirmative support claims must be."""

    def test_frozen_wording_no_false_positives(self):
        from atlas_release_gate_lib.fixtures import FROZEN_ATLAS_FEATURE_WORDING
        self.assertEqual(
            feature_checks.scan_forbidden_features(FROZEN_ATLAS_FEATURE_WORDING), [])

    def test_full_frozen_docs_no_false_positives(self):
        from atlas_release_gate_lib.fixtures import (
            FROZEN_ATLAS_README, FROZEN_ATLAS_KNOWN_LIMITATIONS,
            FROZEN_ATLAS_FEATURE_WORDING)
        text = (FROZEN_ATLAS_README + FROZEN_ATLAS_KNOWN_LIMITATIONS +
                FROZEN_ATLAS_FEATURE_WORDING)
        self.assertEqual(feature_checks.scan_forbidden_features(text), [])

    def test_gate_passes_on_frozen_feature_wording(self):
        from atlas_release_gate_lib.errors import RELEASE_GATE_PASSED
        from atlas_release_gate_lib.fixtures import (
            FROZEN_ATLAS_README, FROZEN_ATLAS_FEATURE_WORDING)
        # README carries the boundaries; the feature wording is appended.
        _, outcome = self.run_gate(
            readme_text=FROZEN_ATLAS_README + "\n" + FROZEN_ATLAS_FEATURE_WORDING)
        self.assertEqual(outcome.status, RELEASE_GATE_PASSED)

    def test_honest_vocabulary_phrases_pass(self):
        for phrase in (
            "workflow types",
            "status vocabulary",
            "Coordinator and Companion are listed as components",
            "refuses WRITE_FILE / DELETE_FILE / SHELL_COMMAND / NETWORK_CALL",
            "forbidden action types are refused",
            "ontology expansion is out of scope",
            "signing or external anchoring are out of scope",
        ):
            self.assertEqual(
                feature_checks.scan_forbidden_features(phrase), [],
                "false positive on honest phrase: %r" % phrase)

    def test_affirmative_support_claims_all_caught(self):
        claims = (
            "Atlas integrates with Coordinator.",
            "Atlas connects to Companion.",
            "Atlas runs workflows.",
            "Atlas uses LLM reasoning.",
            "Atlas supports signing.",
            "Atlas supports external anchoring.",
            "Atlas provides WRITE_FILE.",
            "Atlas supports DELETE_FILE.",
            "Atlas supports SHELL_COMMAND.",
            "Atlas supports NETWORK_CALL.",
        )
        for claim in claims:
            self.assertNotEqual(
                feature_checks.scan_forbidden_features(claim), [],
                "affirmative claim not caught: %r" % claim)

    def test_affirmative_claim_in_otherwise_honest_docs_is_caught(self):
        from atlas_release_gate_lib.errors import FAILED_FORBIDDEN_FEATURE_CHECK
        from atlas_release_gate_lib.fixtures import (
            FROZEN_ATLAS_README, FROZEN_ATLAS_FEATURE_WORDING)
        bad = (FROZEN_ATLAS_README + "\n" + FROZEN_ATLAS_FEATURE_WORDING +
               "\nAtlas integrates with Coordinator.\n")
        _, outcome = self.run_gate(readme_text=bad)
        self.assertEqual(outcome.status, FAILED_FORBIDDEN_FEATURE_CHECK)
