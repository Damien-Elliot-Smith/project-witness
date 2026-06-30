# tests/test_selfcheck.py
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


class TestSelfcheck(unittest.TestCase):
    def test_12_selfcheck_passes_in_process(self):
        import selfcheck
        rc = selfcheck.main([])
        self.assertEqual(rc, 0, "selfcheck.main([]) reported a failing gate")

    def test_selfcheck_imports_no_subprocess(self):
        import ast
        with open(os.path.join(HERE, "selfcheck.py"), encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename="selfcheck.py")
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertNotIn("subprocess", imported,
                         "selfcheck must not import subprocess")


if __name__ == "__main__":
    unittest.main()
