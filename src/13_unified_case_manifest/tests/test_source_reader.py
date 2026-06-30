import os
import shutil

from unified_manifest_lib import manifest as manifest_mod, versions
from unified_manifest_lib.errors import BuildError
from tests._helpers import TempCase

COORD = versions.SOURCE_TYPE_COORDINATOR
COMP = versions.SOURCE_TYPE_COMPANION


class TestSourceReader(TempCase):
    def test_missing_source_root(self):
        with self.assertRaises(BuildError):
            manifest_mod.build_manifest_data(COORD, os.path.join(self.work, "nope"))

    def test_missing_coordinator_output_for_companion(self):
        src = self.companion_source()
        shutil.rmtree(os.path.join(src, "coordinator_output"))
        with self.assertRaises(BuildError):
            manifest_mod.build_manifest_data(COMP, src)

    def test_missing_workflow_report(self):
        src = self.coord_source()
        os.remove(os.path.join(src, "workflow_report.json"))
        with self.assertRaises(BuildError):
            manifest_mod.build_manifest_data(COORD, src)

    def test_missing_atlas_validation_report(self):
        src = self.coord_source()
        os.remove(os.path.join(src, "atlas_validation_report.json"))
        with self.assertRaises(BuildError):
            manifest_mod.build_manifest_data(COORD, src)

    def test_missing_atlas_registry_copy(self):
        src = self.coord_source()
        os.remove(os.path.join(src, "atlas_registry_copy.json"))
        with self.assertRaises(BuildError):
            manifest_mod.build_manifest_data(COORD, src)

    def test_missing_case_bundle_manifest(self):
        src = self.coord_source()
        os.remove(os.path.join(src, "case_bundle_v02", "case_manifest.json"))
        with self.assertRaises(BuildError):
            manifest_mod.build_manifest_data(COORD, src)
