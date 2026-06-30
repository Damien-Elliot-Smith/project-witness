import os

from unified_manifest_lib import canonical, verifier, versions
from unified_manifest_lib.errors import VerifyError
from tests._helpers import TempCase

COORD = versions.SOURCE_TYPE_COORDINATOR
COMP = versions.SOURCE_TYPE_COMPANION


class TestVerify(TempCase):
    def _out(self, companion=False):
        if companion:
            return self.build_output(COMP, self.companion_source())
        return self.build_output(COORD, self.coord_source())

    def _append(self, path):
        canonical.atomic_write_bytes(path, canonical.read_bytes(path) + b" ")

    def test_valid_verifies(self):
        self.assertTrue(verifier.verify(self._out()).ok)

    def test_mutated_manifest_fails(self):
        out = self._out(); self._append(os.path.join(out, "unified_case_manifest.json"))
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_mutated_source_index_fails(self):
        out = self._out(); self._append(os.path.join(out, "source_index.json"))
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_unknown_top_level_file_fails(self):
        out = self._out()
        canonical.atomic_write_bytes(os.path.join(out, "extra.txt"), b"x")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_invalid_source_status_fails(self):
        out = self._out(); self.edit_manifest(out, source_status="FAILED_SOURCE_VERIFY")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_invalid_case_id_fails(self):
        out = self._out(); self.edit_manifest(out, case_id="../bad")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_invalid_evidence_id_fails(self):
        out = self._out(); self.edit_manifest(out, evidence_id="a/b")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_wrong_workflow_type_fails(self):
        out = self._out(); self.edit_manifest(out, workflow_type="OTHER")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_wrong_action_type_fails(self):
        out = self._out(); self.edit_manifest(out, action_type="WRITE_FILE")
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_absolute_artifact_path_fails(self):
        out = self._out()
        man = canonical.load_json(os.path.join(out, "unified_case_manifest.json"))
        man["source_artifacts"][0]["relative_path"] = "/abs/workflow_report.json"
        canonical.write_canonical(os.path.join(out, "unified_case_manifest.json"), man)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_duplicate_artifact_id_fails(self):
        out = self._out()
        man = canonical.load_json(os.path.join(out, "unified_case_manifest.json"))
        man["source_artifacts"][1]["artifact_id"] = man["source_artifacts"][0]["artifact_id"]
        canonical.write_canonical(os.path.join(out, "unified_case_manifest.json"), man)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_duplicate_artifact_path_fails(self):
        out = self._out()
        man = canonical.load_json(os.path.join(out, "unified_case_manifest.json"))
        man["source_artifacts"][1]["relative_path"] = man["source_artifacts"][0]["relative_path"]
        canonical.write_canonical(os.path.join(out, "unified_case_manifest.json"), man)
        self.rebuild_checksums(out)
        with self.assertRaises(VerifyError):
            verifier.verify(out)

    def test_bad_status_in_manifest_fails(self):
        out = self._out(); self.edit_manifest(out, odin_reasoning_status="INVALID_INPUT")
        with self.assertRaises(VerifyError):
            verifier.verify(out)
