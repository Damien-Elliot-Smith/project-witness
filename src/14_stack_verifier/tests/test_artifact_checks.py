from stack_verifier_lib import report as report_mod, validation
from tests._helpers import TempCase, COORD, COMP


class TestArtifactChecks(TempCase):
    def test_hashes_recorded(self):
        report, checked = report_mod.build_stack_report(COORD, self.coord_source())
        self.assertTrue(checked)
        for art in checked:
            self.assertRegex(art["sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(art["check_status"], "ARTIFACT_CHECKED")

    def test_relative_paths_only(self):
        report, checked = report_mod.build_stack_report(COMP, self.companion_source())
        for art in checked:
            self.assertTrue(validation.is_relative_path(art["relative_path"]))

    def test_unique_within_label(self):
        report, checked = report_mod.build_stack_report(COMP, self.companion_source())
        ids = [(a["source_label"], a["artifact_id"]) for a in checked]
        paths = [(a["source_label"], a["relative_path"]) for a in checked]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(paths), len(set(paths)))

    def test_manifest_label_present(self):
        src = self.companion_source(); man = self.manifest_output(COMP, src)
        report, checked = report_mod.build_stack_report(COMP, src, man)
        labels = {a["source_label"] for a in checked}
        self.assertIn("MANIFEST_RUN", labels)
        self.assertIn("SOURCE_RUN", labels)

    def test_companion_paths_prefixed(self):
        report, checked = report_mod.build_stack_report(COMP, self.companion_source())
        by_id = {a["artifact_id"]: a for a in checked}
        self.assertEqual(by_id["coordinator_workflow_report"]["relative_path"],
                         "coordinator_output/workflow_report.json")
        self.assertEqual(by_id["companion_report"]["relative_path"],
                         "companion_report.json")
