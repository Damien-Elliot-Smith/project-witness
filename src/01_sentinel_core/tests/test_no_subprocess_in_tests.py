# tests/test_no_subprocess_in_tests.py
# v0.2.1 harness-stability guard.
#
# The unit-test suite must spawn NO subprocesses: a spawned child under
# capture_output can leave an inherited pipe or lingering process that holds the
# interpreter open at shutdown, which intermittently hung the suite through
# v0.2.0. CLI behaviour is exercised in-process via sentinel.main(). This test
# parses every test module and fails if any imports or uses `subprocess`,
# preventing a silent regression.

import ast
import os
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS_DIR = os.path.join(HERE, "tests")


def _module_uses_subprocess(path):
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(a.name.split(".")[0] == "subprocess" for a in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] == "subprocess":
                return True
        elif isinstance(node, ast.Attribute):
            # catch `subprocess.run(...)` even if imported indirectly
            if isinstance(node.value, ast.Name) and node.value.id == "subprocess":
                return True
    return False


class TestNoSubprocessInTests(unittest.TestCase):
    def test_no_test_module_uses_subprocess(self):
        offenders = []
        for name in os.listdir(TESTS_DIR):
            if name.startswith("test_") and name.endswith(".py"):
                if _module_uses_subprocess(os.path.join(TESTS_DIR, name)):
                    offenders.append(name)
        self.assertEqual(
            offenders, [],
            f"These test modules use subprocess (shutdown-hang risk): {offenders}. "
            f"Invoke the CLI in-process via sentinel.main() instead.")


if __name__ == "__main__":
    unittest.main()
