# tests/test_selfcheck.py
import ast
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


class TestSelfcheck(unittest.TestCase):
    def test_46_selfcheck_passes_in_process(self):
        import selfcheck
        self.assertEqual(selfcheck.main([]), 0)

    def test_selfcheck_imports_no_subprocess(self):
        with open(os.path.join(HERE, "selfcheck.py"), encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename="selfcheck.py")
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertNotIn("subprocess", imported)


if __name__ == "__main__":
    unittest.main()
