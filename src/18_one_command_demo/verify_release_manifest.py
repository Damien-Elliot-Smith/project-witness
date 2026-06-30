#!/usr/bin/env python3
"""Release manifest checker for One-Command Demo Script v0.1.

Confirms the package's files, version, authoritative commands, truth-boundary
sentence, known limitations, and the absence of bare runtime asserts. It launches
no subprocesses and does not run the Connected Demo.
"""

import ast
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

DOCS = ("README.md", "RUN_FORMAT.md", "KNOWN_LIMITATIONS.md",
        "RELEASE_COMMANDS.md", "ONE_COMMAND_DEMO_SCRIPT.md")
TOP_SCRIPTS = ("one_command_demo.py", "verify_one_command_demo.py",
               "verify_release_manifest.py")
LIB_MODULES = ("__init__.py", "canonical.py", "checksums.py", "engine.py",
               "errors.py", "runner.py", "steps.py", "verifier.py", "versions.py")
TEST_FILES = ("__init__.py", "_helpers.py", "test_wrapper.py",
              "test_checksums_and_verify.py", "test_cli.py",
              "test_no_bare_asserts.py")

AUTHORITATIVE_COMMANDS = (
    "python3 -m compileall -q .",
    "python3 -m unittest discover -s tests -v",
    "python3 -O -m unittest discover -s tests -v",
    "python3 one_command_demo.py selfcheck",
    "python3 -O one_command_demo.py selfcheck",
    "python3 -W error::ResourceWarning -m unittest discover -s tests -v",
    "sha256sum -c one_command_demo_script_v01.sha256",
    "python3 verify_release_manifest.py",
)

TRUTH_SENTENCE = (
    "one-command demo script v0.1 runs and verifies the frozen project witness "
    "connected demo v0.1. it does not prove evidence contents are true, does not "
    "prove odin claims are true, and does not verify external reality.")


def _read(rel):
    with open(os.path.join(ROOT, rel), "r", encoding="utf-8") as handle:
        return handle.read()


def _norm(rel):
    norm = _read(rel).lower()
    for ch in ("*", "`", "_", "#", "\n", "\r", "\t"):
        norm = norm.replace(ch, " ")
    return " ".join(norm.split())


def check_files(fails):
    for rel in DOCS + TOP_SCRIPTS:
        if not os.path.isfile(os.path.join(ROOT, rel)):
            fails.append("missing file: " + rel)
    for rel in LIB_MODULES:
        if not os.path.isfile(os.path.join(ROOT, "one_command_demo_lib", rel)):
            fails.append("missing lib module: " + rel)
    for rel in TEST_FILES:
        if not os.path.isfile(os.path.join(ROOT, "tests", rel)):
            fails.append("missing test file: " + rel)


def check_version(fails):
    if '"0.1.0"' not in _read(os.path.join("one_command_demo_lib", "versions.py")):
        fails.append("version 0.1.0 not found in versions.py")


def check_commands(fails):
    text = _read("RELEASE_COMMANDS.md")
    for cmd in AUTHORITATIVE_COMMANDS:
        if cmd not in text:
            fails.append("RELEASE_COMMANDS.md missing command: " + cmd)


def check_truth_sentence(fails):
    if TRUTH_SENTENCE not in _norm("README.md"):
        fails.append("README.md missing exact truth-boundary sentence")


def check_known_limitations(fails):
    norm = _norm("KNOWN_LIMITATIONS.md")
    for phrase in ("does not prove evidence contents are true",
                   "does not verify external reality",
                   "does not sign or externally anchor",
                   "whole-folder fabrication remains possible under unkeyed hashes"):
        if phrase not in norm:
            fails.append("KNOWN_LIMITATIONS.md missing statement: " + phrase)


def check_no_bare_asserts(fails):
    runtime = [os.path.join("one_command_demo_lib", m) for m in LIB_MODULES] \
        + ["one_command_demo.py", "verify_one_command_demo.py"]
    for rel in runtime:
        for node in ast.walk(ast.parse(_read(rel))):
            if isinstance(node, ast.Assert):
                fails.append("bare runtime assert in %s line %d"
                             % (rel, node.lineno))


def main():
    fails = []
    check_files(fails)
    check_version(fails)
    check_commands(fails)
    check_truth_sentence(fails)
    check_known_limitations(fails)
    check_no_bare_asserts(fails)
    if fails:
        for f in fails:
            print("FAIL  " + f)
        print("verify_release_manifest: %d failure(s)" % len(fails))
        return 1
    print("verify_release_manifest: OK (launched no subprocesses)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
