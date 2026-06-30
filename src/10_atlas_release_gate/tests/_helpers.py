"""Shared test helpers."""

import os
import tempfile
import unittest

from atlas_release_gate_lib import gate, canonical, checksums
from atlas_release_gate_lib.atlas_runner import FakeAtlasRunner
from atlas_release_gate_lib.fixtures import make_fake_atlas_root


class TempCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.work = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def make_atlas(self, **kwargs):
        root = os.path.join(self.work, "atlas")
        make_fake_atlas_root(root, **kwargs)
        return root

    def run_gate(self, runner=None, **kwargs):
        atlas_root = self.make_atlas(**kwargs)
        out_dir = os.path.join(self.work, "out")
        outcome = gate.run_check(atlas_root, out_dir,
                                 runner if runner is not None else FakeAtlasRunner())
        return out_dir, outcome

    def rebuild_checksums(self, out_dir):
        paths = checksums.present_canonical_paths(out_dir)
        canonical.atomic_write_bytes(
            os.path.join(out_dir, "atlas_release_gate_checksums.txt"),
            checksums.build_checksums_text(out_dir, paths))
