# tests/test_no_bare_asserts.py
import ast
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


def _bare_asserts_in(path):
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=path)
    return [f"{os.path.basename(path)}:{n.lineno}"
            for n in ast.walk(tree) if isinstance(n, ast.Assert)]


class TestNoBareAsserts(unittest.TestCase):
    def test_13_no_bare_asserts_in_runtime(self):
        # Runtime code = the histor_lite package + the CLI + selfcheck.
        offenders = []
        pkg = os.path.join(HERE, "histor_lite")
        for dirpath, _, names in os.walk(pkg):
            for n in names:
                if n.endswith(".py"):
                    offenders += _bare_asserts_in(os.path.join(dirpath, n))
        for top in ("histor_lite.py", "selfcheck.py", "release_check.py"):
            p = os.path.join(HERE, top)
            if os.path.isfile(p):
                offenders += _bare_asserts_in(p)
        self.assertEqual(offenders, [], f"bare asserts in runtime: {offenders}")


if __name__ == "__main__":
    unittest.main()
