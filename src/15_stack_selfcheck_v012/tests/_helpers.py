"""Shared test helpers for Stack Selfcheck v0.1."""

import os
import tempfile
import unittest

from stack_selfcheck_lib import (canonical, checksums, report as report_mod,
                              steps as steps_mod)
from tests import synthetic


class TempCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.work = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def inventory(self, **kw):
        return synthetic.build_inventory(self.work, **kw)

    def component_root(self, cid):
        return os.path.join(self.work, "components", cid)

    def set_component_doc(self, cid, name, text):
        path = os.path.join(self.component_root(cid), name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def build_output(self, inv, stack_verifier_run=None, out_name="out"):
        out = os.path.join(self.work, out_name)
        report, _ = report_mod.build_selfcheck_report(inv, stack_verifier_run)
        os.makedirs(out, exist_ok=True)
        canonical.write_canonical(os.path.join(out, "stack_selfcheck_report.json"), report)
        canonical.write_canonical(os.path.join(out, "stack_selfcheck_steps.json"),
                                  steps_mod.build_steps(steps_mod.all_completed()))
        canonical.atomic_write_bytes(
            os.path.join(out, "stack_selfcheck_checksums.txt"),
            checksums.build_checksums_text(out))
        return out

    def rebuild_checksums(self, out):
        canonical.atomic_write_bytes(
            os.path.join(out, "stack_selfcheck_checksums.txt"),
            checksums.build_checksums_text(out))

    def edit_report(self, out, **changes):
        path = os.path.join(out, "stack_selfcheck_report.json")
        rep = canonical.load_json(path)
        rep.update(changes)
        canonical.write_canonical(path, rep)
        self.rebuild_checksums(out)
        return rep
