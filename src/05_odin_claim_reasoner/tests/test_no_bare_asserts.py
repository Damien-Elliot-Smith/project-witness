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
    def test_32_no_bare_asserts_in_runtime(self):
        offenders = []
        pkg = os.path.join(HERE, "odin_reasoner")
        for dirpath, _, names in os.walk(pkg):
            for n in names:
                if n.endswith(".py"):
                    offenders += _bare_asserts_in(os.path.join(dirpath, n))
        for top in ("odin.py", "selfcheck.py", "verify_release_manifest.py"):
            p = os.path.join(HERE, top)
            if os.path.isfile(p):
                offenders += _bare_asserts_in(p)
        self.assertEqual(offenders, [], f"bare asserts in runtime: {offenders}")


class TestReleaseShape(unittest.TestCase):
    def _read(self, name):
        with open(os.path.join(HERE, name), encoding="utf-8") as f:
            return f.read()

    def test_release_commands_doc_present_and_complete(self):
        path = os.path.join(HERE, "RELEASE_COMMANDS.md")
        self.assertTrue(os.path.isfile(path), "RELEASE_COMMANDS.md must exist")
        doc = self._read("RELEASE_COMMANDS.md")
        for cmd in ("python3 -m compileall -q .",
                    "python3 -m unittest discover -s tests -v",
                    "python3 -O -m unittest discover -s tests -v",
                    "python3 selfcheck.py",
                    "python3 -O selfcheck.py",
                    "python3 -W error::ResourceWarning -m unittest discover -s tests",
                    "sha256sum -c odin_claim_reasoner_v01.sha256",
                    "python3 verify_release_manifest.py"):
            self.assertIn(cmd, doc, f"RELEASE_COMMANDS.md missing: {cmd}")

    def test_34_manifest_verifier_present_static_and_passes(self):
        path = os.path.join(HERE, "verify_release_manifest.py")
        self.assertTrue(os.path.isfile(path))
        src = self._read("verify_release_manifest.py")
        tree = ast.parse(src)
        imported = set()
        spawn = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                f = node.func
                parts = []
                while isinstance(f, ast.Attribute):
                    parts.append(f.attr)
                    f = f.value
                if isinstance(f, ast.Name):
                    parts.append(f.id)
                name = ".".join(reversed(parts))
                if name in ("subprocess.run", "subprocess.Popen",
                            "subprocess.call", "os.system", "os.popen",
                            "os.execv", "os.spawnv", "os.fork"):
                    spawn.append(f"{name}:{node.lineno}")
        self.assertNotIn("subprocess", imported)
        self.assertEqual(spawn, [], f"manifest verifier spawns: {spawn}")
        import importlib.util as ilu
        spec = ilu.spec_from_file_location("verify_release_manifest", path)
        mod = ilu.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(mod.main([]), 0)

    def test_no_subprocess_orchestrator_gate(self):
        label = "optional convenience; not the authoritative freeze gate"
        for name in ("release_check.py", "release_check.sh"):
            p = os.path.join(HERE, name)
            if os.path.isfile(p):
                self.assertIn(label, self._read(name))


class TestHonesty(unittest.TestCase):
    def test_28_contradiction_detected_is_not_a_truth_claim(self):
        # The status vocabulary must not assert truth/falsity of contents.
        from odin_reasoner import versions
        statuses = {versions.REASONING_CONSISTENT,
                    versions.REASONING_CONTRADICTION_DETECTED,
                    versions.REASONING_INVALID_INPUT,
                    versions.CLAIM_ACCEPTED, versions.CLAIM_CONTRADICTED,
                    versions.CLAIM_INVALID}
        for s in statuses:
            self.assertNotIn("TRUE", s.upper())
            self.assertNotIn("FALSE", s.upper())
            self.assertNotIn("PROVEN", s.upper())
        # CONTRADICTION_DETECTED is explicitly structural, not a truth verdict.
        self.assertIn("CONTRADICTION", versions.REASONING_CONTRADICTION_DETECTED)

    def test_known_limitations_disclaim_truth(self):
        from odin_reasoner import versions
        joined = " ".join(versions.KNOWN_LIMITATIONS).lower()
        self.assertIn("does not prove claims true", joined)

    def test_readme_says_structured_only_and_not_truth(self):
        with open(os.path.join(HERE, "README.md"), encoding="utf-8") as f:
            readme = f.read().lower()
        self.assertIn("structured", readme)
        self.assertTrue("not" in readme and "true" in readme,
                        "README must disclaim proving truth")


if __name__ == "__main__":
    unittest.main()
