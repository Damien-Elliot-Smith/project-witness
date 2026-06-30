# tests/test_selfcheck.py
import ast
import os
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestSelfcheck(unittest.TestCase):
    def test_selfcheck_passes_in_process(self):
        # v0.1.4: run selfcheck IN-PROCESS. selfcheck no longer launches the
        # unit-test suite (or any subprocess), so calling it from inside the
        # unit suite cannot recurse or deadlock. This replaces the v0.1.3
        # subprocess invocation, which — combined with selfcheck's old
        # unit-test gates — produced an intermittent pipe-inheritance hang.
        import selfcheck
        rc = selfcheck.main([])
        self.assertEqual(rc, 0, "selfcheck.main([]) reported a failing gate")

    def test_selfcheck_has_no_subprocess_unit_gates(self):
        # Guard against regressing the deadlock: selfcheck must not import or
        # use subprocess, and must not contain unit-test gates that spawn the
        # suite. We assert structurally on the source.
        with open(os.path.join(HERE, "selfcheck.py"), encoding="utf-8") as f:
            src = f.read()
        tree = ast.parse(src, filename="selfcheck.py")
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertNotIn("subprocess", imported,
                         "selfcheck must not import subprocess (deadlock risk)")
        self.assertNotIn("unit_tests", _gate_names(tree),
                         "selfcheck must not contain a unit_tests gate")

    def test_no_bare_assert_in_runtime(self):
        pkg = os.path.join(HERE, "sentinel_core")
        offenders = []
        for dirpath, _, names in os.walk(pkg):
            for n in names:
                if n.endswith(".py"):
                    p = os.path.join(dirpath, n)
                    with open(p, encoding="utf-8") as fh:
                        tree = ast.parse(fh.read(), filename=p)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Assert):
                            offenders.append(f"{n}:{node.lineno}")
        self.assertEqual(offenders, [], f"Bare asserts found: {offenders}")


def _gate_names(tree):
    """Extract string gate names from the GATES list literal in selfcheck."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "GATES":
                    if isinstance(node.value, ast.List):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Tuple) and elt.elts:
                                first = elt.elts[0]
                                if isinstance(first, ast.Constant):
                                    names.add(first.value)
    return names


if __name__ == "__main__":
    unittest.main()
