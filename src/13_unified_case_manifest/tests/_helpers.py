"""Shared test helpers for Unified Case Manifest v0.1."""

import os
import tempfile
import unittest

from unified_manifest_lib import (canonical, checksums, manifest as manifest_mod,
                                 versions)
from tests import synthetic


class TempCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.work = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def coord_source(self, **kw):
        src = os.path.join(self.work, "coord_%d" % len(os.listdir(self.work)))
        synthetic.build_coordinator_source(src, **kw)
        return src

    def companion_source(self, **kw):
        src = os.path.join(self.work, "comp_%d" % len(os.listdir(self.work)))
        synthetic.build_companion_source(src, **kw)
        return src

    def build_output(self, source_type, source_run, out_name="out"):
        out = os.path.join(self.work, out_name)
        manifest, source_index = manifest_mod.build_manifest_data(
            source_type, source_run)
        os.makedirs(out, exist_ok=True)
        canonical.write_canonical(os.path.join(out, "unified_case_manifest.json"), manifest)
        canonical.write_canonical(os.path.join(out, "source_index.json"), source_index)
        canonical.atomic_write_bytes(
            os.path.join(out, "unified_manifest_checksums.txt"),
            checksums.build_checksums_text(out))
        return out

    def rebuild_checksums(self, out):
        canonical.atomic_write_bytes(
            os.path.join(out, "unified_manifest_checksums.txt"),
            checksums.build_checksums_text(out))

    def edit_manifest(self, out, **changes):
        path = os.path.join(out, "unified_case_manifest.json")
        man = canonical.load_json(path)
        man.update(changes)
        canonical.write_canonical(path, man)
        self.rebuild_checksums(out)
        return man
