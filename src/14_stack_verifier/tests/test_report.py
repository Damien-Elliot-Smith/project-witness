import os

from stack_verifier_lib import canonical, report as report_mod
from stack_verifier_lib.errors import CheckError
from tests._helpers import TempCase, COORD, COMP


def _rebuild_coord_checksums(coord_dir):
    from tests import synthetic
    paths = [p for p in synthetic._COORD_PATHS
             if os.path.isfile(os.path.join(coord_dir, p))]
    lines = ["%s  %s" % (synthetic._sha(os.path.join(coord_dir, p)), p) for p in paths]
    with open(os.path.join(coord_dir, "workflow_checksums.txt"), "wb") as h:
        h.write(("\n".join(lines) + "\n").encode("utf-8"))


class TestReport(TempCase):
    def test_valid_coordinator_accepted(self):
        r, _ = report_mod.build_stack_report(COORD, self.coord_source())
        self.assertEqual(r["stack_verification_status"], "STACK_VERIFIED")
        self.assertEqual(r["companion_status"], "NOT_APPLICABLE")

    def test_valid_companion_accepted(self):
        r, _ = report_mod.build_stack_report(COMP, self.companion_source())
        self.assertEqual(r["stack_verification_status"], "STACK_VERIFIED")
        self.assertEqual(r["companion_status"], "COMPANION_COMPLETED")

    def test_valid_source_plus_manifest(self):
        src = self.companion_source(); man = self.manifest_output(COMP, src)
        r, _ = report_mod.build_stack_report(COMP, src, man)
        self.assertEqual(r["manifest_status"], "MANIFEST_VERIFIED")

    def test_case_id_mismatch_refused(self):
        with self.assertRaises(CheckError):
            report_mod.build_stack_report(COORD, self.coord_source(manifest_case_id="case_x0000000000"))

    def test_evidence_id_mismatch_refused(self):
        with self.assertRaises(CheckError):
            report_mod.build_stack_report(COORD, self.coord_source(manifest_evidence_id="evidence_x"))

    def test_wrong_workflow_type_refused(self):
        src = self.coord_source()
        path = os.path.join(src, "workflow_report.json")
        rep = canonical.load_json(path); rep["workflow_type"] = "OTHER"
        canonical.write_canonical(path, rep); _rebuild_coord_checksums(src)
        with self.assertRaises(CheckError):
            report_mod.build_stack_report(COORD, src)

    def test_non_atlas_validated_refused(self):
        with self.assertRaises(CheckError):
            report_mod.build_stack_report(COORD, self.coord_source(atlas_validation_status="FAILED"))

    def test_non_registry_verified_refused(self):
        src = self.coord_source()
        path = os.path.join(src, "workflow_report.json")
        rep = canonical.load_json(path); rep["atlas_registry_status"] = "REGISTRY_NOT_VERIFIED"
        canonical.write_canonical(path, rep); _rebuild_coord_checksums(src)
        with self.assertRaises(CheckError):
            report_mod.build_stack_report(COORD, src)

    def test_bad_sentinel_refused(self):
        with self.assertRaises(CheckError):
            report_mod.build_stack_report(COORD, self.coord_source(sentinel_status="FAIL"))

    def test_bad_aletheia_refused(self):
        with self.assertRaises(CheckError):
            report_mod.build_stack_report(COORD, self.coord_source(aletheia_status="MISSING"))

    def test_bad_bridge_refused(self):
        with self.assertRaises(CheckError):
            report_mod.build_stack_report(COORD, self.coord_source(bridge_status="NOPE"))

    def test_odin_consistent_accepted(self):
        r, _ = report_mod.build_stack_report(COORD, self.coord_source(odin_status="CONSISTENT"))
        self.assertEqual(r["odin_reasoning_status"], "CONSISTENT")

    def test_odin_contradiction_accepted(self):
        r, _ = report_mod.build_stack_report(COORD, self.coord_source(odin_status="CONTRADICTION_DETECTED"))
        self.assertEqual(r["odin_reasoning_status"], "CONTRADICTION_DETECTED")

    def test_odin_invalid_input_refused(self):
        with self.assertRaises(CheckError):
            report_mod.build_stack_report(COORD, self.coord_source(odin_status="INVALID_INPUT"))

    def test_bad_case_bundle_refused(self):
        with self.assertRaises(CheckError):
            report_mod.build_stack_report(COORD, self.coord_source(case_bundle_status="UNBUNDLED"))

    def test_report_canonical(self):
        out = self.build_output(COORD, self.coord_source())
        self.assertTrue(canonical.is_canonical_bytes(
            canonical.read_bytes(os.path.join(out, "stack_verification_report.json"))))

    def test_steps_canonical(self):
        out = self.build_output(COORD, self.coord_source())
        self.assertTrue(canonical.is_canonical_bytes(
            canonical.read_bytes(os.path.join(out, "stack_verification_steps.json"))))
