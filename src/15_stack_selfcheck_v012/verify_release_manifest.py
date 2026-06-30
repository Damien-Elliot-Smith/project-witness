#!/usr/bin/env python3
"""Static release-manifest checker for Stack Verifier v0.1. Launches NO
subprocesses."""

import ast
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

LIB_MODULES = (
    "__init__.py", "versions.py", "canonical.py", "errors.py", "validation.py",
    "inventory_reader.py", "component_checks.py", "sidecar_checks.py",
    "documentation_checks.py", "legacy_documentation.py",
    "stack_verifier_reader.py", "report.py",
    "steps.py", "checksums.py", "verifier.py",
)
TOP_SCRIPTS = ("stack_selfcheck.py", "selfcheck.py", "verify_release_manifest.py")
TEST_FILES = (
    "test_inventory_reader.py", "test_component_checks.py", "test_sidecar_checks.py",
    "test_documentation_checks.py", "test_stack_verifier_reader.py", "test_report.py",
    "test_steps.py", "test_checksums.py", "test_verify.py", "test_honesty.py",
    "test_selfcheck.py", "test_no_bare_asserts.py", "test_legacy_documentation.py",
    "test_truth_boundary_model.py",
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
    "sha256sum -c stack_selfcheck_v012.sha256",
    "python3 verify_release_manifest.py",
)


def _read(rel):
    with open(os.path.join(ROOT, rel), "r", encoding="utf-8") as handle:
        return handle.read()


def _runtime_files():
    return [os.path.join("stack_selfcheck_lib", m) for m in LIB_MODULES] + list(TOP_SCRIPTS)


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


def _norm(rel):
    norm = " ".join(_read(rel).lower().split())
    for ch in ("*", "`", "_", "#"):
        norm = norm.replace(ch, "")
    return " ".join(norm.split())


def check_files(fails):
    for rel in DOCS + TOP_SCRIPTS:
        if not os.path.isfile(os.path.join(ROOT, rel)):
            fails.append("missing file: " + rel)
    for rel in LIB_MODULES:
        if not os.path.isfile(os.path.join(ROOT, "stack_selfcheck_lib", rel)):
            fails.append("missing lib module: " + rel)
    for rel in TEST_FILES:
        if not os.path.isfile(os.path.join(ROOT, "tests", rel)):
            fails.append("missing test file: " + rel)


def check_version(fails):
    if '"0.1.2"' not in _read(os.path.join("stack_selfcheck_lib", "versions.py")):
        fails.append("version 0.1.2 not found in versions.py")


def check_commands(fails):
    text = _read("RELEASE_COMMANDS.md")
    for cmd in AUTHORITATIVE_COMMANDS:
        if cmd not in text:
            fails.append("RELEASE_COMMANDS.md missing command: " + cmd)


def check_no_bare_asserts(fails):
    for rel in _runtime_files():
        for node in ast.walk(ast.parse(_read(rel))):
            if isinstance(node, ast.Assert):
                fails.append("bare runtime assert in %s (line %d)" % (rel, node.lineno))


def check_no_subprocess(fails):
    for rel in _runtime_files():
        if _uses_subprocess(ast.parse(_read(rel))):
            fails.append("subprocess import in runtime file: " + rel)


def check_readme(fails):
    norm = _norm("README.md")
    required = (
        "checks frozen stack inventory",
        "does not run workflows",
        "does not call frozen components during the freeze gate",
        "does not copy evidence contents",
        "does not prove truth",
        "optional stack verifier output may be cross-checked",
        "legacy frozen components may omit",
        "accepts equivalent truth-boundary wording",
    )
    for phrase in required:
        if phrase not in norm:
            fails.append("README.md missing statement: " + phrase)


def check_known_limitations(fails):
    norm = _norm("KNOWN_LIMITATIONS.md")
    required = (
        "one stack inventory only",
        "optional one stack verifier output only",
        "does not run workflows",
        "does not call frozen components during the freeze gate",
        "does not copy evidence contents", "does not prove truth",
        "does not verify external reality", "does not sign",
        "does not externally anchor", "does not merge cases",
        "does not provide search", "does not provide gui", "does not use llm",
        "does not prove the stack works in the real world",
        "legacy documentation allowances are recorded and never silently passed",
        "the truth-boundary phrase model is deterministic and does not weaken truth-claim refusal",
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
