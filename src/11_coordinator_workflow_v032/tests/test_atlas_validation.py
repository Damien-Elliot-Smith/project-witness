import os

from coordinator_v03_lib import atlas_validation
from coordinator_v03_lib.errors import (
    ATLAS_VALIDATED, FAILED_ATLAS_ROOT_MISSING, FAILED_ATLAS_REGISTRY_MISSING,
    FAILED_ATLAS_VERIFY, FAILED_ATLAS_WORKFLOW_TYPE_MISSING,
    FAILED_ATLAS_ACTION_TYPE_MISSING, FAILED_ATLAS_COMPONENT_MISSING,
    FAILED_ATLAS_STATUS_MISSING, FAILED_ATLAS_PREDICATE_MISSING,
    FAILED_ATLAS_TRUTH_CLAIM, FAILED_ATLAS_FORBIDDEN_ACTION)
from tests._helpers import TempCase


class TestAtlasValidation(TempCase):
    def test_valid_atlas_validated(self):
        self.assertEqual(atlas_validation.validate(self.atlas_root()).status,
                         ATLAS_VALIDATED)

    def test_missing_root_refused(self):
        self.assertEqual(
            atlas_validation.validate(os.path.join(self.work, "nope")).status,
            FAILED_ATLAS_ROOT_MISSING)

    def test_missing_registry_file_refused(self):
        root = self.atlas_root(missing_registry=True)
        self.assertEqual(atlas_validation.validate(root).status,
                         FAILED_ATLAS_REGISTRY_MISSING)

    def test_verify_failure(self):
        root = self.atlas_root(break_verify=True)
        self.assertEqual(atlas_validation.validate(root).status,
                         FAILED_ATLAS_VERIFY)

    def test_missing_workflow_type(self):
        self.assertEqual(
            atlas_validation.validate(self.atlas_root(omit_workflow_type=True)).status,
            FAILED_ATLAS_WORKFLOW_TYPE_MISSING)

    def test_missing_action_type(self):
        self.assertEqual(
            atlas_validation.validate(self.atlas_root(omit_action_type=True)).status,
            FAILED_ATLAS_ACTION_TYPE_MISSING)

    def test_missing_component(self):
        self.assertEqual(
            atlas_validation.validate(
                self.atlas_root(omit_component="odin_claim_reasoner")).status,
            FAILED_ATLAS_COMPONENT_MISSING)

    def test_missing_status(self):
        self.assertEqual(
            atlas_validation.validate(self.atlas_root(omit_status="CONVERTED")).status,
            FAILED_ATLAS_STATUS_MISSING)

    def test_missing_predicate(self):
        self.assertEqual(
            atlas_validation.validate(
                self.atlas_root(omit_predicate="evidence.present")).status,
            FAILED_ATLAS_PREDICATE_MISSING)

    def test_truth_claim_status_refused(self):
        self.assertEqual(
            atlas_validation.validate(self.atlas_root(truth_claim_status=True)).status,
            FAILED_ATLAS_TRUTH_CLAIM)

    def test_truth_claim_predicate_refused(self):
        self.assertEqual(
            atlas_validation.validate(self.atlas_root(truth_claim_predicate=True)).status,
            FAILED_ATLAS_TRUTH_CLAIM)

    def test_forbidden_action_refused(self):
        self.assertEqual(
            atlas_validation.validate(self.atlas_root(forbidden_action="WRITE_FILE")).status,
            FAILED_ATLAS_FORBIDDEN_ACTION)
