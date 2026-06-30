import ast
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNTIME = [
    "one_command_demo.py", "verify_one_command_demo.py",
] + [os.path.join("one_command_demo_lib", m) for m in (
    "canonical.py", "checksums.py", "engine.py", "errors.py", "runner.py",
    "steps.py", "verifier.py", "versions.py")]


class TestNoBareAsserts(unittest.TestCase):
    def test_no_bare_runtime_asserts(self):
        for rel in RUNTIME:
            with open(os.path.join(ROOT, rel), encoding="utf-8") as h:
                tree = ast.parse(h.read())
            for node in ast.walk(tree):
                self.assertNotIsInstance(
                    node, ast.Assert,
                    "bare assert in %s line %s" % (rel, getattr(node, "lineno", "?")))

    def test_manifest_checker_passes(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "vrm", os.path.join(ROOT, "verify_release_manifest.py"))
        vrm = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(vrm)
        self.assertEqual(vrm.main(), 0)
