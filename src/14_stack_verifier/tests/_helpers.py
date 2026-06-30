"""Shared test helpers for Stack Verifier v0.1."""

import os
import tempfile
import unittest

from stack_verifier_lib import (canonical, checksums, report as report_mod,
                              steps as steps_mod, versions)
from tests import synthetic

COORD = versions.SOURCE_TYPE_COORDINATOR
COMP = versions.SOURCE_TYPE_COMPANION


class TempCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.work = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def _name(self, prefix):
        return os.path.join(self.work, "%s_%d" % (prefix, len(os.listdir(self.work))))

    def coord_source(self, **kw):
        src = self._name("coord"); synthetic.build_coordinator_source(src, **kw)
        return src

    def companion_source(self, **kw):
        src = self._name("comp"); synthetic.build_companion_source(src, **kw)
        return src

    def manifest_output(self, source_type, source_run, **kw):
        man = self._name("man")
        synthetic.build_unified_manifest_output(man, source_type, source_run, **kw)
        return man

    def build_output(self, source_type, source_run, manifest_run=None):
        out = self._name("out")
        report, _ = report_mod.build_stack_report(source_type, source_run, manifest_run)
        os.makedirs(out, exist_ok=True)
        canonical.write_canonical(os.path.join(out, "stack_verification_report.json"), report)
        canonical.write_canonical(os.path.join(out, "stack_verification_steps.json"),
                                  steps_mod.build_steps(steps_mod.all_completed()))
        canonical.atomic_write_bytes(
            os.path.join(out, "stack_verification_checksums.txt"),
            checksums.build_checksums_text(out))
        return out

    def rebuild_checksums(self, out):
        canonical.atomic_write_bytes(
            os.path.join(out, "stack_verification_checksums.txt"),
            checksums.build_checksums_text(out))

    def edit_report(self, out, **changes):
        path = os.path.join(out, "stack_verification_report.json")
        rep = canonical.load_json(path)
        rep.update(changes)
        canonical.write_canonical(path, rep)
        self.rebuild_checksums(out)
        return rep
