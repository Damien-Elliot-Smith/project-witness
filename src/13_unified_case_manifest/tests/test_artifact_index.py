import os

from unified_manifest_lib import manifest as manifest_mod, versions, validation
from tests._helpers import TempCase

COORD = versions.SOURCE_TYPE_COORDINATOR
COMP = versions.SOURCE_TYPE_COMPANION


class TestArtifactIndex(TempCase):
    def test_artifact_hashes_recorded(self):
        manifest, _ = manifest_mod.build_manifest_data(COORD, self.coord_source())
        arts = manifest["source_artifacts"]
        self.assertTrue(arts)
        for art in arts:
            self.assertRegex(art["sha256"], r"^[0-9a-f]{64}$")
            self.assertIn("artifact_id", art)
            self.assertIn("produced_by", art)

    def test_absolute_paths_not_stored(self):
        manifest, _ = manifest_mod.build_manifest_data(COMP, self.companion_source())
        for art in manifest["source_artifacts"]:
            self.assertTrue(validation.is_relative_path(art["relative_path"]))
            self.assertFalse(os.path.isabs(art["relative_path"]))

    def test_unique_ids_and_paths(self):
        manifest, _ = manifest_mod.build_manifest_data(COMP, self.companion_source())
        ids = [a["artifact_id"] for a in manifest["source_artifacts"]]
        paths = [a["relative_path"] for a in manifest["source_artifacts"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(paths), len(set(paths)))

    def test_companion_prefixes_coordinator_paths(self):
        manifest, idx = manifest_mod.build_manifest_data(COMP, self.companion_source())
        by_id = {a["artifact_id"]: a for a in manifest["source_artifacts"]}
        self.assertEqual(by_id["coordinator_workflow_report"]["relative_path"],
                         "coordinator_output/workflow_report.json")
        self.assertEqual(by_id["companion_report"]["relative_path"],
                         "companion_report.json")
        self.assertEqual(idx["source_artifacts_indexed"],
                         len(manifest["source_artifacts"]))
