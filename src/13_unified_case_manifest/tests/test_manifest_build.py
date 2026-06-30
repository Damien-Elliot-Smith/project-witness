import os

from unified_manifest_lib import canonical, manifest as manifest_mod, versions
from unified_manifest_lib.errors import BuildError
from tests._helpers import TempCase

COORD = versions.SOURCE_TYPE_COORDINATOR
COMP = versions.SOURCE_TYPE_COMPANION


def _rebuild_coord_checksums(coord_dir):
    from tests import synthetic
    paths = [p for p in synthetic._COORD_PATHS
             if os.path.isfile(os.path.join(coord_dir, p))]
    lines = ["%s  %s" % (synthetic._sha(os.path.join(coord_dir, p)), p) for p in paths]
    with open(os.path.join(coord_dir, "workflow_checksums.txt"), "wb") as h:
        h.write(("\n".join(lines) + "\n").encode("utf-8"))


class TestManifestBuild(TempCase):
    def test_valid_coordinator_accepted(self):
        m, _ = manifest_mod.build_manifest_data(COORD, self.coord_source())
        self.assertEqual(m["source_status"], "SOURCE_VERIFIED")
        self.assertEqual(m["companion_status"], "NOT_APPLICABLE")

    def test_valid_companion_accepted(self):
        m, _ = manifest_mod.build_manifest_data(COMP, self.companion_source())
        self.assertEqual(m["source_status"], "SOURCE_VERIFIED")
        self.assertEqual(m["companion_status"], "COMPANION_COMPLETED")

    def test_case_id_mismatch_refused(self):
        src = self.coord_source(manifest_case_id="case_other00000000")
        with self.assertRaises(BuildError):
            manifest_mod.build_manifest_data(COORD, src)

    def test_evidence_id_mismatch_refused(self):
        src = self.coord_source(manifest_evidence_id="evidence_other")
        with self.assertRaises(BuildError):
            manifest_mod.build_manifest_data(COORD, src)

    def test_wrong_workflow_type_refused(self):
        src = self.coord_source()
        path = os.path.join(src, "workflow_report.json")
        rep = canonical.load_json(path)
        rep["workflow_type"] = "SOME_OTHER_WORKFLOW"
        canonical.write_canonical(path, rep)
        _rebuild_coord_checksums(src)
        with self.assertRaises(BuildError):
            manifest_mod.build_manifest_data(COORD, src)

    def test_non_workflow_completed_refused(self):
        src = self.coord_source(workflow_status="FAILED_SENTINEL")
        with self.assertRaises(BuildError):
            manifest_mod.build_manifest_data(COORD, src)

    def test_non_atlas_validated_refused(self):
        src = self.coord_source(atlas_validation_status="FAILED_ATLAS_VERIFY")
        with self.assertRaises(BuildError):
            manifest_mod.build_manifest_data(COORD, src)

    def test_non_registry_verified_refused(self):
        src = self.coord_source()
        path = os.path.join(src, "workflow_report.json")
        rep = canonical.load_json(path)
        rep["atlas_registry_status"] = "REGISTRY_NOT_VERIFIED"
        canonical.write_canonical(path, rep)
        _rebuild_coord_checksums(src)
        with self.assertRaises(BuildError):
            manifest_mod.build_manifest_data(COORD, src)

    def test_bad_sentinel_status_refused(self):
        with self.assertRaises(BuildError):
            manifest_mod.build_manifest_data(COORD, self.coord_source(sentinel_status="FAIL"))

    def test_bad_aletheia_status_refused(self):
        with self.assertRaises(BuildError):
            manifest_mod.build_manifest_data(COORD, self.coord_source(aletheia_status="MISSING"))

    def test_bad_bridge_status_refused(self):
        with self.assertRaises(BuildError):
            manifest_mod.build_manifest_data(COORD, self.coord_source(bridge_status="NOPE"))

    def test_odin_consistent_accepted(self):
        m, _ = manifest_mod.build_manifest_data(COORD, self.coord_source(odin_status="CONSISTENT"))
        self.assertEqual(m["odin_reasoning_status"], "CONSISTENT")

    def test_odin_contradiction_accepted(self):
        m, _ = manifest_mod.build_manifest_data(
            COORD, self.coord_source(odin_status="CONTRADICTION_DETECTED"))
        self.assertEqual(m["odin_reasoning_status"], "CONTRADICTION_DETECTED")

    def test_odin_invalid_input_refused(self):
        with self.assertRaises(BuildError):
            manifest_mod.build_manifest_data(COORD, self.coord_source(odin_status="INVALID_INPUT"))

    def test_bad_case_bundle_status_refused(self):
        with self.assertRaises(BuildError):
            manifest_mod.build_manifest_data(COORD, self.coord_source(case_bundle_status="UNBUNDLED"))

    def test_manifest_and_index_canonical(self):
        out = self.build_output(COMP, self.companion_source())
        self.assertTrue(canonical.is_canonical_bytes(
            canonical.read_bytes(os.path.join(out, "unified_case_manifest.json"))))
        self.assertTrue(canonical.is_canonical_bytes(
            canonical.read_bytes(os.path.join(out, "source_index.json"))))

    def test_checksums_written(self):
        out = self.build_output(COORD, self.coord_source())
        self.assertTrue(os.path.isfile(os.path.join(out, "unified_manifest_checksums.txt")))
