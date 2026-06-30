"""Shared test helpers for Coordinator v0.3."""

import os
import tempfile
import unittest

from coordinator_v03_lib import workflow, canonical, checksums, fixtures
from coordinator_v03_lib.component_runners import FakeComponentRunner


class TempCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.work = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def atlas_root(self, **opts):
        root = os.path.join(self.work, "atlas")
        fixtures.make_fake_atlas_root(root, **opts)
        return root

    def make_request(self, atlas_opts=None, **request_kwargs):
        root = self.atlas_root(**(atlas_opts or {}))
        evidence = os.path.join(self.work, "evidence.txt")
        canonical.atomic_write_bytes(evidence, b"evidence")
        return fixtures.build_request(self.work, root, evidence, **request_kwargs)

    def run_wf(self, atlas_opts=None, runner=None, **request_kwargs):
        request = self.make_request(atlas_opts=atlas_opts, **request_kwargs)
        out_dir = os.path.join(self.work, "out")
        outcome = workflow.run_workflow(
            request, out_dir,
            runner if runner is not None else FakeComponentRunner())
        return out_dir, outcome

    def rebuild_checksums(self, out_dir):
        present = checksums.present_paths(out_dir)
        canonical.atomic_write_bytes(
            os.path.join(out_dir, "workflow_checksums.txt"),
            checksums.build_checksums_text(out_dir, present))
