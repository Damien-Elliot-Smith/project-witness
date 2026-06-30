import os
import shutil

from stack_verifier_lib import report as report_mod
from stack_verifier_lib.errors import CheckError
from tests._helpers import TempCase, COORD, COMP


class TestSourceReader(TempCase):
    def _expect_fail(self, source_type, src):
        with self.assertRaises(CheckError):
            report_mod.build_stack_report(source_type, src)

    def test_missing_source_root(self):
        self._expect_fail(COORD, os.path.join(self.work, "nope"))

    def test_missing_coordinator_output_for_companion(self):
        src = self.companion_source()
        shutil.rmtree(os.path.join(src, "coordinator_output"))
        self._expect_fail(COMP, src)

    def test_missing_workflow_report(self):
        src = self.coord_source(); os.remove(os.path.join(src, "workflow_report.json"))
        self._expect_fail(COORD, src)

    def test_missing_workflow_steps(self):
        src = self.coord_source(); os.remove(os.path.join(src, "workflow_steps.json"))
        self._expect_fail(COORD, src)

    def test_missing_atlas_validation_report(self):
        src = self.coord_source(); os.remove(os.path.join(src, "atlas_validation_report.json"))
        self._expect_fail(COORD, src)

    def test_missing_atlas_registry_copy(self):
        src = self.coord_source(); os.remove(os.path.join(src, "atlas_registry_copy.json"))
        self._expect_fail(COORD, src)

    def test_missing_case_bundle_manifest(self):
        src = self.coord_source()
        os.remove(os.path.join(src, "case_bundle_v02", "case_manifest.json"))
        self._expect_fail(COORD, src)

    def test_missing_bridge_claims(self):
        src = self.coord_source()
        os.remove(os.path.join(src, "bridge_output", "odin_claims.json"))
        self._expect_fail(COORD, src)

    def test_missing_odin_reasoning_report(self):
        src = self.coord_source()
        os.remove(os.path.join(src, "odin_output", "reasoning_report.json"))
        self._expect_fail(COORD, src)
