#!/usr/bin/env python3
"""Static release-manifest checker for Atlas Release Gate v0.1.

Launches NO subprocesses. Verifies expected files exist, the version is 0.1.0,
RELEASE_COMMANDS.md lists every authoritative command, no runtime module uses a
bare assert, the only module permitted to import subprocess is the Atlas runner,
and the README/limitations carry the required boundary statements.
"""

import ast
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

LIB_MODULES = (
    "__init__.py", "versions.py", "errors.py", "canonical.py", "validation.py",
    "checksums.py", "feature_checks.py", "documentation_checks.py",
    "atlas_runner.py", "report.py", "steps.py", "gate.py", "verifier.py",
    "fixtures.py",
)
TOP_SCRIPTS = ("atlas_release_gate.py", "selfcheck.py", "verify_release_manifest.py")
TEST_FILES = (
    "test_validation.py", "test_documentation_checks.py", "test_feature_checks.py",
    "test_runner.py", "test_steps.py", "test_report.py", "test_checksums.py",
    "test_verify.py", "test_honesty.py", "test_selfcheck.py",
    "test_no_bare_asserts.py",
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
    "sha256sum -c atlas_release_gate_v01.sha256",
    "python3 verify_release_manifest.py",
)

# Modules permitted to import subprocess (none in the freeze gate path).
SUBPROCESS_ALLOWED = {os.path.join("atlas_release_gate_lib", "atlas_runner.py")}


def _read(rel):
    with open(os.path.join(ROOT, rel), "r", encoding="utf-8") as handle:
        return handle.read()


def _runtime_py_files():
    files = [os.path.join("atlas_release_gate_lib", m) for m in LIB_MODULES]
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
        if not os.path.isfile(os.path.join(ROOT, "atlas_release_gate_lib", rel)):
            fails.append("missing lib module: " + rel)
    for rel in TEST_FILES:
        if not os.path.isfile(os.path.join(ROOT, "tests", rel)):
            fails.append("missing test file: " + rel)


def check_version(fails):
    src = _read(os.path.join("atlas_release_gate_lib", "versions.py"))
    if '"0.1.0"' not in src:
        fails.append("version 0.1.0 not found in versions.py")


def check_commands(fails):
    text = _read("RELEASE_COMMANDS.md")
    for cmd in AUTHORITATIVE_COMMANDS:
        if cmd not in text:
            fails.append("RELEASE_COMMANDS.md missing authoritative command: " + cmd)


def check_no_bare_asserts(fails):
    for rel in _runtime_py_files():
        tree = ast.parse(_read(rel))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                fails.append("bare runtime assert in " + rel +
                             " (line %d)" % node.lineno)


def check_no_subprocess_gate(fails):
    for rel in _runtime_py_files():
        tree = ast.parse(_read(rel))
        if _uses_subprocess(tree) and rel not in SUBPROCESS_ALLOWED:
            fails.append("unexpected subprocess import in " + rel)


def check_readme(fails):
    norm = " ".join(_read("README.md").lower().split())
    required = (
        "atlas release gate v0.1 checks whether an atlas registry v0.1 release",
        "does not modify the registry",
        "does not run workflows",
        "does not prove truth",
        "does not connect atlas to coordinator or companion",
    )
    for phrase in required:
        if phrase not in norm:
            fails.append("README.md missing statement: " + phrase)


def check_known_limitations(fails):
    norm = " ".join(_read("KNOWN_LIMITATIONS.md").lower().split())
    required = (
        "checks atlas registry v0.1",
        "does not modify",
        "does not run workflows",
        "does not prove truth",
        "no llm",
        "no signing",
        "no external anchoring",
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
    check_no_subprocess_gate(fails)
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
