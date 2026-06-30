import os

from atlas_release_gate_lib import gate
from atlas_release_gate_lib.atlas_runner import FakeAtlasRunner
from atlas_release_gate_lib.errors import (
    FAILED_ATLAS_ROOT_MISSING, FAILED_REQUIRED_FILE_MISSING, RELEASE_GATE_PASSED)
from atlas_release_gate_lib import validation
from tests._helpers import TempCase


class TestValidation(TempCase):
    def test_valid_release_accepted(self):
        _, outcome = self.run_gate()
        self.assertEqual(outcome.status, RELEASE_GATE_PASSED)

    def test_missing_atlas_root_refused(self):
        out_dir = os.path.join(self.work, "out")
        outcome = gate.run_check(os.path.join(self.work, "nope"),
                                 out_dir, FakeAtlasRunner())
        self.assertEqual(outcome.status, FAILED_ATLAS_ROOT_MISSING)
        self.assertFalse(outcome.passed)

    def test_missing_required_file_refused(self):
        _, outcome = self.run_gate(omit={"RUN_FORMAT.md"})
        self.assertEqual(outcome.status, FAILED_REQUIRED_FILE_MISSING)

    def test_missing_registry_file_refused(self):
        _, outcome = self.run_gate(omit={"registry/atlas_registry.json"})
        self.assertEqual(outcome.status, FAILED_REQUIRED_FILE_MISSING)

    def test_missing_required_helper(self):
        root = self.make_atlas(omit={"README.md"})
        self.assertIn("README.md", validation.missing_required(root))
