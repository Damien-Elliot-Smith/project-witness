import os

from companion_lib.errors import (FAILED_INPUT_VALIDATION, COMPANION_COMPLETED)
from companion_lib.coordinator_runner import FakeCoordinatorRunner
from tests._helpers import TempCase, RecordingRunner


class TestCliValidation(TempCase):
    def test_valid_args_accepted(self):
        self.assertEqual(self.run_companion().companion_status, COMPANION_COMPLETED)

    def test_missing_atlas_root_refused(self):
        roots = {k: os.path.join(self.work, k)
                 for k in __import__("companion_lib.versions", fromlist=["x"]).COMPONENT_ROOT_KEYS}
        roots["atlas_registry_root"] = os.path.join(self.work, "nonexistent_atlas")
        self.assertEqual(
            self.run_companion(component_roots=roots).companion_status,
            FAILED_INPUT_VALIDATION)

    def test_missing_coordinator_root_refused(self):
        self.assertEqual(
            self.run_companion(coordinator_root=os.path.join(self.work, "nope")).companion_status,
            FAILED_INPUT_VALIDATION)

    def test_missing_evidence_file_refused(self):
        self.assertEqual(
            self.run_companion(evidence_file=os.path.join(self.work, "no.txt")).companion_status,
            FAILED_INPUT_VALIDATION)

    def test_directory_evidence_refused(self):
        d = os.path.join(self.work, "evdir"); os.makedirs(d)
        self.assertEqual(self.run_companion(evidence_file=d).companion_status,
                         FAILED_INPUT_VALIDATION)

    def test_symlink_evidence_refused(self):
        link = os.path.join(self.work, "link.txt")
        os.symlink(self.evidence, link)
        self.assertEqual(self.run_companion(evidence_file=link).companion_status,
                         FAILED_INPUT_VALIDATION)

    def test_unsafe_case_id_refused(self):
        self.assertEqual(self.run_companion(case_id="../x").companion_status,
                         FAILED_INPUT_VALIDATION)

    def test_unsafe_evidence_id_refused(self):
        self.assertEqual(self.run_companion(evidence_id="a/b").companion_status,
                         FAILED_INPUT_VALIDATION)

    def test_unsafe_case_directory_name_refused(self):
        self.assertEqual(self.run_companion(case_directory_name="..").companion_status,
                         FAILED_INPUT_VALIDATION)

    def test_missing_component_root_refused(self):
        roots = {k: os.path.join(self.work, k)
                 for k in __import__("companion_lib.versions", fromlist=["x"]).COMPONENT_ROOT_KEYS}
        roots["odin_root"] = os.path.join(self.work, "no_odin")
        self.assertEqual(self.run_companion(component_roots=roots).companion_status,
                         FAILED_INPUT_VALIDATION)

    def test_non_empty_output_refused(self):
        out = os.path.join(self.work, "out"); os.makedirs(out)
        open(os.path.join(out, "junk"), "w").close()
        self.assertEqual(self.run_companion(out=out).companion_status,
                         FAILED_INPUT_VALIDATION)

    def test_companion_calls_coordinator_only(self):
        rec = RecordingRunner(FakeCoordinatorRunner())
        self.run_companion(runner=rec)
        self.assertEqual(rec.calls, ["run", "verify"])
