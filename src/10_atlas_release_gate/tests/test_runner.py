import os

from atlas_release_gate_lib.atlas_runner import FakeAtlasRunner, SubprocessAtlasRunner
from atlas_release_gate_lib.errors import (
    FAILED_REGISTRY_VERIFY, FAILED_EXPORT_VERIFY)
from tests._helpers import TempCase


class TestRunner(TempCase):
    def test_registry_verify_failure_refused(self):
        _, outcome = self.run_gate(runner=FakeAtlasRunner(fail_registry=True))
        self.assertEqual(outcome.status, FAILED_REGISTRY_VERIFY)

    def test_export_failure_refused(self):
        _, outcome = self.run_gate(runner=FakeAtlasRunner(fail_export=True))
        self.assertEqual(outcome.status, FAILED_EXPORT_VERIFY)

    def test_export_verify_failure_refused(self):
        _, outcome = self.run_gate(runner=FakeAtlasRunner(fail_export_verify=True))
        self.assertEqual(outcome.status, FAILED_EXPORT_VERIFY)

    def test_corrupt_export_refused(self):
        _, outcome = self.run_gate(runner=FakeAtlasRunner(corrupt_export=True))
        self.assertEqual(outcome.status, FAILED_EXPORT_VERIFY)

    def test_fake_export_produces_files(self):
        runner = FakeAtlasRunner()
        atlas_root = self.make_atlas()
        export_dir = os.path.join(self.work, "exp")
        self.assertTrue(runner.verify_registry(atlas_root).ok)
        self.assertTrue(runner.export_registry(atlas_root, export_dir).ok)
        for name in ("atlas_registry_copy.json", "atlas_summary.json",
                     "atlas_checksums.txt"):
            self.assertTrue(os.path.isfile(os.path.join(export_dir, name)))
        self.assertTrue(runner.verify_export(export_dir).ok)


class TestSubprocessRunnerArgv(TempCase):
    """The real-Atlas adapter must build the frozen Atlas Registry v0.1 argv
    shapes. These tests assert the shapes and the run wiring WITHOUT launching
    real Atlas (an executor is injected)."""

    def test_verify_registry_argv_shape(self):
        runner = SubprocessAtlasRunner()
        self.assertEqual(
            runner.verify_registry_argv(),
            ["atlas.py", "verify", "--registry", "registry/atlas_registry.json"])

    def test_export_registry_argv_shape(self):
        runner = SubprocessAtlasRunner()
        self.assertEqual(
            runner.export_registry_argv("/tmp/export_dir"),
            ["atlas.py", "export", "--registry", "registry/atlas_registry.json",
             "--out", "/tmp/export_dir"])

    def test_verify_export_argv_shape(self):
        runner = SubprocessAtlasRunner()
        self.assertEqual(
            runner.verify_export_argv("/tmp/export_dir"),
            ["atlas.py", "verify-export", "--export", "/tmp/export_dir"])

    def test_executor_receives_correct_argv_and_cwd(self):
        calls = []

        def fake_executor(cwd, full_argv):
            calls.append((cwd, full_argv))
            return (0, "ok", "")

        runner = SubprocessAtlasRunner(python_exe="python3", executor=fake_executor)
        self.assertTrue(runner.verify_registry("/atlas_root").ok)
        self.assertTrue(runner.export_registry("/atlas_root", "/exp").ok)
        self.assertTrue(runner.verify_export("/exp").ok)

        # verify_registry: cwd is the atlas root; argv carries the relative registry path
        self.assertEqual(calls[0][0], "/atlas_root")
        self.assertEqual(
            calls[0][1],
            ["python3", "atlas.py", "verify",
             "--registry", "registry/atlas_registry.json"])
        # export_registry: cwd is the atlas root; --out carries the export dir
        self.assertEqual(calls[1][0], "/atlas_root")
        self.assertEqual(
            calls[1][1],
            ["python3", "atlas.py", "export",
             "--registry", "registry/atlas_registry.json", "--out", "/exp"])
        # verify_export: --export carries the export dir
        self.assertEqual(
            calls[2][1],
            ["python3", "atlas.py", "verify-export", "--export", "/exp"])

    def test_nonzero_returncode_is_failure(self):
        runner = SubprocessAtlasRunner(executor=lambda cwd, argv: (1, "", "boom"))
        self.assertFalse(runner.verify_registry("/atlas_root").ok)

    def test_no_real_subprocess_in_default_suite(self):
        # Sanity: the injected executor path never imports/launches subprocess.
        seen = {"called": False}

        def exec_ok(cwd, argv):
            seen["called"] = True
            return (0, "", "")

        SubprocessAtlasRunner(executor=exec_ok).verify_registry("/x")
        self.assertTrue(seen["called"])
