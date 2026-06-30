#!/usr/bin/env python3
# verify_release_manifest.py
# Static release-metadata checker for Case Bundle v0.2. Imports only ast, os, sys.
# Launches NO subprocesses (no subprocess/os.system/etc). It checks file presence,
# the version string, the RELEASE_COMMANDS list, the absence of bare runtime
# asserts, the absence of a subprocess-heavy gate, and the required README and
# KNOWN_LIMITATIONS disclaimers.

import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

EXPECTED_FILES = [
    "README.md", "KNOWN_LIMITATIONS.md", "RUN_FORMAT.md", "RELEASE_COMMANDS.md",
    "REPAIR_LEDGER.md", "TEST_RESULTS.md", "case_bundle_v02.py", "selfcheck.py",
    "verify_release_manifest.py",
    os.path.join("case_bundle_v02_lib", "__init__.py"),
    os.path.join("case_bundle_v02_lib", "versions.py"),
    os.path.join("case_bundle_v02_lib", "canonical.py"),
    os.path.join("case_bundle_v02_lib", "errors.py"),
    os.path.join("case_bundle_v02_lib", "validation.py"),
    os.path.join("case_bundle_v02_lib", "input_verifiers.py"),
    os.path.join("case_bundle_v02_lib", "builder.py"),
    os.path.join("case_bundle_v02_lib", "manifest.py"),
    os.path.join("case_bundle_v02_lib", "checksums.py"),
    os.path.join("case_bundle_v02_lib", "verifier.py"),
    os.path.join("tests", "test_validation.py"),
    os.path.join("tests", "test_input_verifiers.py"),
    os.path.join("tests", "test_builder.py"),
    os.path.join("tests", "test_manifest.py"),
    os.path.join("tests", "test_checksums.py"),
    os.path.join("tests", "test_verify.py"),
    os.path.join("tests", "test_honesty.py"),
    os.path.join("tests", "test_selfcheck.py"),
    os.path.join("tests", "test_no_bare_asserts.py"),
]

AUTHORITATIVE_COMMANDS = [
    "python3 -m compileall -q .",
    "python3 -m unittest discover -s tests -v",
    "python3 -O -m unittest discover -s tests -v",
    "python3 selfcheck.py",
    "python3 -O selfcheck.py",
    "python3 -W error::ResourceWarning -m unittest discover -s tests",
    "sha256sum -c case_bundle_v02.sha256",
    "python3 verify_release_manifest.py",
]

RUNTIME_PY = [
    "case_bundle_v02.py", "selfcheck.py", "verify_release_manifest.py",
    os.path.join("case_bundle_v02_lib", "__init__.py"),
    os.path.join("case_bundle_v02_lib", "versions.py"),
    os.path.join("case_bundle_v02_lib", "canonical.py"),
    os.path.join("case_bundle_v02_lib", "errors.py"),
    os.path.join("case_bundle_v02_lib", "validation.py"),
    os.path.join("case_bundle_v02_lib", "input_verifiers.py"),
    os.path.join("case_bundle_v02_lib", "builder.py"),
    os.path.join("case_bundle_v02_lib", "manifest.py"),
    os.path.join("case_bundle_v02_lib", "checksums.py"),
    os.path.join("case_bundle_v02_lib", "verifier.py"),
]

SPAWN = {"subprocess.run", "subprocess.Popen", "subprocess.call",
         "subprocess.check_call", "subprocess.check_output", "os.system",
         "os.popen", "os.execv", "os.execve", "os.spawnv", "os.fork"}


def _fail(checks, msg):
    checks.append((False, msg))


def _ok(checks, msg):
    checks.append((True, msg))


def _read(rel):
    with open(os.path.join(HERE, rel), encoding="utf-8") as f:
        return f.read()


def _call_name(node):
    f = node.func
    parts = []
    while isinstance(f, ast.Attribute):
        parts.append(f.attr)
        f = f.value
    if isinstance(f, ast.Name):
        parts.append(f.id)
    return ".".join(reversed(parts))


def check_files(checks):
    missing = [f for f in EXPECTED_FILES
               if not os.path.isfile(os.path.join(HERE, f))]
    if missing:
        _fail(checks, f"missing expected files: {missing}")
    else:
        _ok(checks, "all expected files present")


def check_version(checks):
    src = _read(os.path.join("case_bundle_v02_lib", "versions.py"))
    if 'CASE_BUNDLE_VERSION = "0.2.0"' in src:
        _ok(checks, "version is 0.2.0")
    else:
        _fail(checks, "CASE_BUNDLE_VERSION is not 0.2.0")


def check_release_commands(checks):
    doc = _read("RELEASE_COMMANDS.md")
    missing = [c for c in AUTHORITATIVE_COMMANDS if c not in doc]
    if missing:
        _fail(checks, f"RELEASE_COMMANDS.md missing commands: {missing}")
    else:
        _ok(checks, "RELEASE_COMMANDS.md lists every authoritative command")


def check_no_bare_asserts(checks):
    offenders = []
    for rel in RUNTIME_PY:
        tree = ast.parse(_read(rel), filename=rel)
        for n in ast.walk(tree):
            if isinstance(n, ast.Assert):
                offenders.append(f"{rel}:{n.lineno}")
    if offenders:
        _fail(checks, f"bare runtime asserts: {offenders}")
    else:
        _ok(checks, "no bare runtime asserts in runtime modules")


def check_no_subprocess_gate(checks):
    # No runtime module nor the manifest verifier may import subprocess or call a
    # spawn primitive. Convenience wrappers must be labelled optional.
    bad = []
    for rel in RUNTIME_PY:
        tree = ast.parse(_read(rel), filename=rel)
        for n in ast.walk(tree):
            if isinstance(n, ast.Import) and any(
                    a.name.split(".")[0] == "subprocess" for a in n.names):
                bad.append(f"{rel}: imports subprocess")
            elif (isinstance(n, ast.ImportFrom) and n.module
                  and n.module.split(".")[0] == "subprocess"):
                bad.append(f"{rel}: imports subprocess")
            elif isinstance(n, ast.Call) and _call_name(n) in SPAWN:
                bad.append(f"{rel}:{n.lineno}: {_call_name(n)}")
    label = "optional convenience; not the authoritative freeze gate"
    for name in ("release_check.py", "release_check.sh"):
        p = os.path.join(HERE, name)
        if os.path.isfile(p) and label not in _read(name):
            bad.append(f"{name}: convenience wrapper not labelled optional")
    if bad:
        _fail(checks, f"subprocess-heavy gate concerns: {bad}")
    else:
        _ok(checks, "no subprocess-heavy release gate")


def check_known_limitations(checks):
    if os.path.isfile(os.path.join(HERE, "KNOWN_LIMITATIONS.md")):
        _ok(checks, "KNOWN_LIMITATIONS.md exists")
    else:
        _fail(checks, "KNOWN_LIMITATIONS.md missing")


def check_readme(checks):
    r = _read("README.md").lower()
    pairs = [
        ("packages verified" in r and "case records only" in r,
         "README says it packages verified case records only"),
        ("does not prove evidence contents are true" in r,
         "README says it does not prove evidence contents true"),
        ("does not prove odin claims are true" in r,
         "README says it does not prove ODIN claims true"),
        (("does not execute" in r) and ("reasoning" in r),
         "README says it does not execute actions or run reasoning"),
        ("coordinator" in r and "companion" in r,
         "README says it is not connected to Coordinator or Companion yet"),
    ]
    for cond, msg in pairs:
        checks.append((bool(cond), msg))


def main(argv=None):
    checks = []
    check_files(checks)
    check_version(checks)
    check_release_commands(checks)
    check_no_bare_asserts(checks)
    check_no_subprocess_gate(checks)
    check_known_limitations(checks)
    check_readme(checks)

    print("=" * 60)
    print("  verify_release_manifest.py — Case Bundle v0.2 (static)")
    print("=" * 60)
    ok = True
    for passed, msg in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {msg}")
        ok = ok and passed
    print("=" * 60)
    if ok:
        print("  MANIFEST OK — static release metadata verified.")
        return 0
    print("  MANIFEST FAILED.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
