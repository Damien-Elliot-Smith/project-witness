"""Shared test helpers for Companion CLI v0.3."""

import os
import tempfile
import unittest

from companion_lib import engine, canonical, checksums, versions
from companion_lib.coordinator_runner import FakeCoordinatorRunner


class TempCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.work = self._tmp.name
        for k in versions.COMPONENT_ROOT_KEYS:
            os.makedirs(os.path.join(self.work, k), exist_ok=True)
        os.makedirs(os.path.join(self.work, "cases"), exist_ok=True)
        os.makedirs(os.path.join(self.work, "coordinator"), exist_ok=True)
        self.evidence = os.path.join(self.work, "evidence.txt")
        canonical.atomic_write_bytes(self.evidence, b"evidence")

    def tearDown(self):
        self._tmp.cleanup()

    def params(self, **overrides):
        roots = {k: os.path.join(self.work, k) for k in versions.COMPONENT_ROOT_KEYS}
        p = {
            "case_id": "case_001", "evidence_id": "evidence_001",
            "evidence_file": self.evidence,
            "allowed_root": os.path.join(self.work, "cases"),
            "case_directory_name": "case_001",
            "coordinator_root": os.path.join(self.work, "coordinator"),
            "out": os.path.join(self.work, "out"), "component_roots": roots,
        }
        p.update(overrides)
        return p

    def run_companion(self, runner=None, **overrides):
        runner = runner if runner is not None else FakeCoordinatorRunner()
        return engine.create_evidence_case(self.params(**overrides), runner)

    def rebuild_checksums(self, out_dir):
        present = checksums.present_paths(out_dir)
        canonical.atomic_write_bytes(
            os.path.join(out_dir, "companion_checksums.txt"),
            checksums.build_checksums_text(out_dir, present))


class RecordingRunner:
    """Wraps a fake runner and records which methods Companion calls."""
    def __init__(self, inner):
        self.inner = inner
        self.calls = []

    def run(self, request, coord_dir):
        self.calls.append("run")
        return self.inner.run(request, coord_dir)

    def verify(self, coord_dir):
        self.calls.append("verify")
        return self.inner.verify(coord_dir)
