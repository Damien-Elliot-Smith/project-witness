import ast
import os

import verify_release_manifest as vrm
from tests._helpers import TempCase

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _runtime_files():
    return ([os.path.join(ROOT, "companion_lib", m) for m in vrm.LIB_MODULES]
            + [os.path.join(ROOT, s) for s in vrm.TOP_SCRIPTS])


class TestManifestAndAsserts(TempCase):
    def test_no_bare_runtime_asserts(self):
        offenders = []
        for path in _runtime_files():
            with open(path, "r", encoding="utf-8") as handle:
                tree = ast.parse(handle.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Assert):
                    offenders.append("%s:%d" % (path, node.lineno))
        self.assertEqual(offenders, [])

    def test_manifest_checker_passes(self):
        self.assertEqual(vrm.main(), 0)

    def test_subprocess_only_in_adapter(self):
        for path in _runtime_files():
            rel = os.path.relpath(path, ROOT)
            with open(path, "r", encoding="utf-8") as handle:
                tree = ast.parse(handle.read())
            if vrm._uses_subprocess(tree):
                self.assertIn(rel, vrm.SUBPROCESS_ALLOWED,
                              "unexpected subprocess import in %s" % rel)
