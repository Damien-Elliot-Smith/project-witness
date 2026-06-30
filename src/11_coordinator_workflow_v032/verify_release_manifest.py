#!/usr/bin/env python3
"""Static release-manifest checker for Coordinator Workflow v0.3.

Launches NO subprocesses. Verifies expected files exist, the version is 0.3.0,
RELEASE_COMMANDS.md lists every authoritative command, no runtime module uses a
bare assert or imports subprocess, and the README/limitations carry the required
statements.
"""

import ast
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

LIB_MODULES = (
    "__init__.py", "versions.py", "errors.py", "canonical.py", "checksums.py",
    "steps.py", "atlas_validation.py", "component_runners.py", "report.py",
    "workflow.py", "verifier.py", "fixtures.py",
)
TOP_SCRIPTS = ("coordinator_v03.py", "selfcheck.py", "verify_release_manifest.py")
TEST_FILES = (
    "test_atlas_validation.py", "test_workflow.py", "test_steps.py",
    "test_checksums.py", "test_verify.py", "test_honesty.py",
    "test_selfcheck.py", "test_no_bare_asserts.py", "test_real_runner.py",
)
DOCS = ("README.md", "KNOWN_LIMITATIONS.md", "RUN_FORMAT.md",
        "RELEASE_COMMANDS.md", "REPAIR_LEDGER.md", "TEST_RESULTS.md")

AUTHORITATIVE_COMMANDS = (
    "python3 -m compileall -q .",
    "python3 -m unittest discover -s tests -v",
    "python3 -O -m unittest discover -s tests -v",
    "python3 selfcheck.py",
    "python3 -O selfcheck.py",
    "python3 -W error::ResourceWarning -m unittest discover -s tests",
    "sha256sum -c coordinator_workflow_v032.sha256",
    "python3 verify_release_manifest.py",
)

# The freeze gate is fully in-process (it launches no subprocesses). v0.3.1 wires
# the real lower-component CLIs via subprocess in exactly ONE adapter module,
# component_runners.py; every other runtime module must stay subprocess-free.
import os as _os_for_allow
SUBPROCESS_ALLOWED = {_os_for_allow.path.join("coordinator_v03_lib", "component_runners.py")}


def _read(rel):
    with open(os.path.join(ROOT, rel), "r", encoding="utf-8") as handle:
        return handle.read()


def _runtime_py_files():
    files = [os.path.join("coordinator_v03_lib", m) for m in LIB_MODULES]
    files += list(TOP_SCRIPTS)
    return files


def _uses_subprocess(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "subprocess" or alias.name.startswith("subprocess."):
                    return True
        elif isinstance(node, ast.ImportFrom):
            if node.module == "subprocess":
                return True
    return False


def check_files(fails):
    for rel in DOCS + TOP_SCRIPTS:
        if not os.path.isfile(os.path.join(ROOT, rel)):
            fails.append("missing file: " + rel)
    for rel in LIB_MODULES:
        if not os.path.isfile(os.path.join(ROOT, "coordinator_v03_lib", rel)):
            fails.append("missing lib module: " + rel)
    for rel in TEST_FILES:
        if not os.path.isfile(os.path.join(ROOT, "tests", rel)):
            fails.append("missing test file: " + rel)


def check_version(fails):
    src = _read(os.path.join("coordinator_v03_lib", "versions.py"))
    if '"0.3.0"' not in src:
        fails.append("version 0.3.0 not found in versions.py")


def check_commands(fails):
    text = _read("RELEASE_COMMANDS.md")
    for cmd in AUTHORITATIVE_COMMANDS:
        if cmd not in text:
            fails.append("RELEASE_COMMANDS.md missing command: " + cmd)


def check_no_bare_asserts(fails):
    for rel in _runtime_py_files():
        tree = ast.parse(_read(rel))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                fails.append("bare runtime assert in %s (line %d)" % (rel, node.lineno))


def check_no_subprocess(fails):
    for rel in _runtime_py_files():
        tree = ast.parse(_read(rel))
        if _uses_subprocess(tree) and rel not in SUBPROCESS_ALLOWED:
            fails.append("unexpected subprocess import in " + rel)


def check_readme(fails):
    norm = " ".join(_read("README.md").lower().split())
    for ch in ("*", "`", "_", "#"):
        norm = norm.replace(ch, "")
    norm = " ".join(norm.split())
    required = (
        "extends coordinator v0.2 with atlas",
        "atlas is read-only",
        "does not modify atlas",
        "does not prove truth",
        "does not connect companion yet",
    )
    for phrase in required:
        if phrase not in norm:
            fails.append("README.md missing statement: " + phrase)


def check_known_limitations(fails):
    norm = " ".join(_read("KNOWN_LIMITATIONS.md").lower().split())
    for ch in ("*", "`", "_", "#"):
        norm = norm.replace(ch, "")
    norm = " ".join(norm.split())
    required = (
        "one workflow type only", "atlas is read-only", "does not modify atlas",
        "does not prove truth", "does not connect companion yet", "no llm",
        "no signing", "no external anchoring",
    )
    for phrase in required:
        if phrase not in norm:
            fails.append("KNOWN_LIMITATIONS.md missing statement: " + phrase)


def main():
    fails = []
    check_files(fails)
    check_version(fails)
    check_commands(fails)
    check_no_bare_asserts(fails)
    check_no_subprocess(fails)
    check_readme(fails)
    check_known_limitations(fails)
    if fails:
        for item in fails:
            print("FAIL: " + item)
        return 1
    print("verify_release_manifest: OK (launched no subprocesses)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
