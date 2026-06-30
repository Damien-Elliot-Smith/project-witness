#!/usr/bin/env python3
"""Static release-manifest checker for Companion CLI v0.3. Launches NO
subprocesses."""

import ast
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

LIB_MODULES = (
    "__init__.py", "versions.py", "errors.py", "canonical.py", "checksums.py",
    "steps.py", "validation.py", "fixtures.py", "coordinator_output.py",
    "coordinator_runner.py", "request_builder.py", "report.py", "engine.py",
    "verifier.py",
)
TOP_SCRIPTS = ("companion.py", "selfcheck.py", "verify_release_manifest.py")
TEST_FILES = (
    "test_cli.py", "test_request.py", "test_companion.py", "test_steps.py",
    "test_checksums.py", "test_verify.py", "test_honesty.py",
    "test_selfcheck.py", "test_no_bare_asserts.py", "test_request_hygiene.py",
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
    "sha256sum -c companion_cli_v031.sha256",
    "python3 verify_release_manifest.py",
)

# subprocess is permitted only in the documented runtime adapter, never in the
# freeze gate (tests + selfcheck are fully in-process and never construct it).
SUBPROCESS_ALLOWED = {"companion_lib/coordinator_runner.py"}


def _read(rel):
    with open(os.path.join(ROOT, rel), "r", encoding="utf-8") as handle:
        return handle.read()


def _runtime_py_files():
    return [os.path.join("companion_lib", m) for m in LIB_MODULES] + list(TOP_SCRIPTS)


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
        if not os.path.isfile(os.path.join(ROOT, "companion_lib", rel)):
            fails.append("missing lib module: " + rel)
    for rel in TEST_FILES:
        if not os.path.isfile(os.path.join(ROOT, "tests", rel)):
            fails.append("missing test file: " + rel)


def check_version(fails):
    if '"0.3.0"' not in _read(os.path.join("companion_lib", "versions.py")):
        fails.append("version 0.3.0 not found in versions.py")


def check_commands(fails):
    text = _read("RELEASE_COMMANDS.md")
    for cmd in AUTHORITATIVE_COMMANDS:
        if cmd not in text:
            fails.append("RELEASE_COMMANDS.md missing command: " + cmd)


def check_no_bare_asserts(fails):
    for rel in _runtime_py_files():
        for node in ast.walk(ast.parse(_read(rel))):
            if isinstance(node, ast.Assert):
                fails.append("bare runtime assert in %s (line %d)" % (rel, node.lineno))


def check_no_subprocess(fails):
    for rel in _runtime_py_files():
        if _uses_subprocess(ast.parse(_read(rel))) and rel not in SUBPROCESS_ALLOWED:
            fails.append("unexpected subprocess import in " + rel)


def _norm(rel):
    norm = " ".join(_read(rel).lower().split())
    for ch in ("*", "`", "_", "#"):
        norm = norm.replace(ch, "")
    return " ".join(norm.split())


def check_readme(fails):
    norm = _norm("README.md")
    required = (
        "wraps coordinator workflow v0.3",
        "atlas is read-only",
        "does not modify atlas",
        "does not add atlas terms",
        "does not prove truth",
        "does not call lower components directly",
    )
    for phrase in required:
        if phrase not in norm:
            fails.append("README.md missing statement: " + phrase)


def check_known_limitations(fails):
    norm = _norm("KNOWN_LIMITATIONS.md")
    required = (
        "one workflow type only", "atlas is read-only", "does not modify atlas",
        "does not add atlas terms", "does not prove truth",
        "does not call lower components directly", "no llm", "no signing",
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
