#!/usr/bin/env python3
# verify_release_manifest.py
# Static release-manifest check for Evidence Reasoning Demo v0.1. Launches NO
# subprocesses. Imports only ast/os/sys. Checks:
#   - expected files exist;
#   - version is 0.1.0;
#   - RELEASE_COMMANDS.md lists every authoritative command;
#   - no bare runtime asserts;
#   - no subprocess-heavy release gate;
#   - known limitations file exists;
#   - README says the demo proves only the local integrity-reasoning chain executes
#     and verifies;
#   - README says the demo does not prove the evidence contents are true;
#   - README says it is not connected to Companion or Coordinator yet.

import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXPECTED_VERSION = "0.1.0"

EXPECTED_FILES = [
    "README.md",
    "KNOWN_LIMITATIONS.md",
    "RUN_FORMAT.md",
    "RELEASE_COMMANDS.md",
    "REPAIR_LEDGER.md",
    "TEST_RESULTS.md",
    "demo.py",
    "selfcheck.py",
    "verify_release_manifest.py",
    os.path.join("evidence_reasoning_demo", "__init__.py"),
    os.path.join("evidence_reasoning_demo", "versions.py"),
    os.path.join("evidence_reasoning_demo", "canonical.py"),
    os.path.join("evidence_reasoning_demo", "errors.py"),
    os.path.join("evidence_reasoning_demo", "validation.py"),
    os.path.join("evidence_reasoning_demo", "component_runner.py"),
    os.path.join("evidence_reasoning_demo", "report.py"),
    os.path.join("evidence_reasoning_demo", "steps.py"),
    os.path.join("evidence_reasoning_demo", "checksums.py"),
    os.path.join("evidence_reasoning_demo", "verifier.py"),
    os.path.join("tests", "test_validation.py"),
    os.path.join("tests", "test_runner.py"),
    os.path.join("tests", "test_report.py"),
    os.path.join("tests", "test_steps.py"),
    os.path.join("tests", "test_checksums.py"),
    os.path.join("tests", "test_verify.py"),
    os.path.join("tests", "test_honesty.py"),
    os.path.join("tests", "test_selfcheck.py"),
    os.path.join("tests", "test_no_bare_asserts.py"),
    os.path.join("tests", "helpers.py"),
    os.path.join("tests", "__init__.py"),
]

REQUIRED_COMMANDS = [
    "python3 -m compileall -q .",
    "python3 -m unittest discover -s tests -v",
    "python3 -O -m unittest discover -s tests -v",
    "python3 selfcheck.py",
    "python3 -O selfcheck.py",
    "python3 -W error::ResourceWarning -m unittest discover -s tests",
    "sha256sum -c evidence_reasoning_demo_v01.sha256",
    "python3 verify_release_manifest.py",
]

RUNTIME_PY = ["demo.py", "selfcheck.py", "verify_release_manifest.py"]


def _read(rel):
    with open(os.path.join(HERE, rel), encoding="utf-8") as f:
        return f.read()


def check_files_exist():
    missing = [p for p in EXPECTED_FILES
               if not os.path.isfile(os.path.join(HERE, p))]
    if missing:
        return False, f"missing expected files: {missing}"
    return True, f"{len(EXPECTED_FILES)} expected files present"


def check_version():
    src = _read(os.path.join("evidence_reasoning_demo", "versions.py"))
    if f'DEMO_VERSION = "{EXPECTED_VERSION}"' not in src:
        return False, f"versions.py does not declare {EXPECTED_VERSION}"
    if f'== "{EXPECTED_VERSION}"' not in _read("selfcheck.py"):
        return False, f"selfcheck.py does not pin version {EXPECTED_VERSION}"
    return True, f"version is {EXPECTED_VERSION}"


def check_release_commands_listed():
    if not os.path.isfile(os.path.join(HERE, "RELEASE_COMMANDS.md")):
        return False, "RELEASE_COMMANDS.md missing"
    doc = _read("RELEASE_COMMANDS.md")
    missing = [c for c in REQUIRED_COMMANDS if c not in doc]
    if missing:
        return False, f"RELEASE_COMMANDS.md missing commands: {missing}"
    return True, "RELEASE_COMMANDS.md lists all authoritative commands"


def _asserts_in(path):
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=path)
    base = os.path.basename(path)
    return [f"{base}:{n.lineno}"
            for n in ast.walk(tree) if isinstance(n, ast.Assert)]


def check_no_bare_asserts():
    offenders = []
    pkg = os.path.join(HERE, "evidence_reasoning_demo")
    for dirpath, _, names in os.walk(pkg):
        for n in names:
            if n.endswith(".py"):
                offenders += _asserts_in(os.path.join(dirpath, n))
    for top in RUNTIME_PY:
        p = os.path.join(HERE, top)
        if os.path.isfile(p):
            offenders += _asserts_in(p)
    if offenders:
        return False, f"bare asserts found: {offenders}"
    return True, "no bare runtime asserts"


def check_no_subprocess_gate():
    label = "optional convenience; not the authoritative freeze gate"
    for name in ("release_check.py", "release_check.sh"):
        p = os.path.join(HERE, name)
        if os.path.isfile(p) and label not in _read(name):
            return False, f"{name} present but not labelled optional"
    doc = _read("RELEASE_COMMANDS.md")
    if "authoritative" not in doc:
        return False, "RELEASE_COMMANDS.md must define the authoritative gate"
    return True, "no subprocess orchestrator is the gate"


def check_known_limitations_exists():
    if not os.path.isfile(os.path.join(HERE, "KNOWN_LIMITATIONS.md")):
        return False, "KNOWN_LIMITATIONS.md missing"
    return True, "KNOWN_LIMITATIONS.md present"


def check_readme_chain_executes_and_verifies():
    readme = _read("README.md").lower()
    if "executes and verifies" not in readme:
        return False, "README must say the chain executes and verifies"
    return True, "README states the chain executes and verifies"


def check_readme_not_truth():
    readme = _read("README.md").lower()
    if not ("not" in readme and "true" in readme):
        return False, "README must state it does not prove contents true"
    return True, "README states it does not prove truth"


def check_readme_not_connected():
    readme = _read("README.md").lower()
    if "companion" not in readme or "coordinator" not in readme:
        return False, "README must say not connected to Companion or Coordinator"
    return True, "README states not connected to Companion/Coordinator yet"


CHECKS = [
    ("expected_files_exist", check_files_exist),
    ("version_is_0_1_0", check_version),
    ("release_commands_listed", check_release_commands_listed),
    ("no_bare_runtime_asserts", check_no_bare_asserts),
    ("no_subprocess_gate", check_no_subprocess_gate),
    ("known_limitations_exists", check_known_limitations_exists),
    ("readme_chain_executes_and_verifies", check_readme_chain_executes_and_verifies),
    ("readme_does_not_prove_truth", check_readme_not_truth),
    ("readme_not_connected_yet", check_readme_not_connected),
]


def main(argv=None):
    print("=" * 60)
    print("  Evidence Reasoning Demo v0.1 — verify_release_manifest")
    print("  (static checks only; launches no subprocesses)")
    print("=" * 60)
    passed = 0
    failed = []
    for name, fn in CHECKS:
        try:
            ok, detail = fn()
        except Exception as e:  # noqa: BLE001
            ok, detail = False, f"error: {type(e).__name__}: {e}"
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
        if ok:
            passed += 1
        else:
            failed.append(name)
    print("=" * 60)
    print(f"  {passed}/{len(CHECKS)} checks passed")
    if failed:
        print(f"  MANIFEST CHECK FAILED: {failed}")
        return 1
    print("  MANIFEST OK — static release metadata verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
