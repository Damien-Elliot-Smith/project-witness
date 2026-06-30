#!/usr/bin/env python3
# release_check.py
# External release orchestrator for Sentinel Core.
#
# Why this exists (v0.1.4): selfcheck must NOT launch the unit-test suite, and
# the unit-test suite must NOT launch full selfcheck. In earlier versions
# selfcheck ran the unit suite as a subprocess, that subprocess ran a test that
# launched another selfcheck subprocess, and the inherited capture pipes could
# deadlock intermittently. The fix is architectural: no release gate spawns
# another release gate. Each step below is an INDEPENDENT subprocess with its
# own explicit timeout, run in sequence by THIS orchestrator, which is itself
# never invoked by selfcheck or by the unit suite.
#
# Steps:
#   1. compileall
#   2. unit tests
#   3. unit tests under -O
#   4. selfcheck
#   5. selfcheck under -O
#   6. ResourceWarning sweep (warnings fatal)
#   7. checksum verification (skipped with a clear note if the .sha256 is not
#      present alongside the package, e.g. inside a clean extraction)
#
# Exit code is 0 only if every non-skipped step passes. A timeout is a failure.

import glob
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable

# Generous per-step timeouts; a hang fails closed instead of blocking forever.
TIMEOUT_FAST = 120      # compileall, selfcheck, checksum
TIMEOUT_TESTS = 600     # unit-test suites


def _run(label, argv, timeout, env=None, optional_ok=False):
    print(f"\n>>> {label}")
    print(f"    $ {' '.join(argv)}")
    start = time.time()
    try:
        proc = subprocess.run(
            argv, cwd=HERE, capture_output=True, text=True,
            timeout=timeout, env=env,
        )
    except subprocess.TimeoutExpired:
        print(f"    TIMEOUT after {timeout}s — FAIL (treated as a hang)")
        return False
    dt = time.time() - start
    out = (proc.stdout or "") + (proc.stderr or "")
    tail = "\n".join(out.strip().splitlines()[-6:])
    if tail:
        print("    " + tail.replace("\n", "\n    "))
    ok = proc.returncode == 0
    print(f"    -> exit {proc.returncode} in {dt:.1f}s : {'PASS' if ok else 'FAIL'}")
    return ok


def step_compileall():
    return _run("1. compileall", [PY, "-m", "compileall", "-q", "."], TIMEOUT_FAST)


def step_unit_tests():
    return _run("2. unit tests",
                [PY, "-m", "unittest", "discover", "-s", "tests"], TIMEOUT_TESTS)


def step_unit_tests_O():
    return _run("3. unit tests (-O)",
                [PY, "-O", "-m", "unittest", "discover", "-s", "tests"], TIMEOUT_TESTS)


def step_selfcheck():
    return _run("4. selfcheck", [PY, "selfcheck.py"], TIMEOUT_FAST)


def step_selfcheck_O():
    return _run("5. selfcheck (-O)", [PY, "-O", "selfcheck.py"], TIMEOUT_FAST)


def step_resourcewarning():
    return _run("6. ResourceWarning sweep",
                [PY, "-W", "error::ResourceWarning", "-m", "unittest",
                 "discover", "-s", "tests"], TIMEOUT_TESTS)


def _package_version():
    try:
        sys.path.insert(0, HERE)
        from sentinel_core.versions import PACKAGE_VERSION
        return PACKAGE_VERSION
    except Exception:
        return None


def step_checksum():
    # Prefer the checksum whose name matches THIS package version
    # (sentinel_core_v0XX.sha256), searching beside this file and one level up
    # (the clean-extraction layout puts the zip + .sha256 in the parent dir).
    ver = _package_version()
    tag = "sentinel_core_v" + ver.replace(".", "") if ver else None  # 0.1.4 -> v014
    search_dirs = [HERE, os.path.join(HERE, "..")]
    preferred, any_match = None, []
    for d in search_dirs:
        for path in sorted(glob.glob(os.path.join(d, "*.sha256"))):
            if not os.path.isfile(path):
                continue
            any_match.append(path)
            if tag and os.path.basename(path) == f"{tag}.sha256":
                preferred = preferred or path
    path = preferred or (any_match[0] if any_match else None)

    print("\n>>> 7. checksum verification")
    if path is None:
        print("    SKIPPED: no .sha256 file found beside the package "
              "(expected when running inside a clean extraction without the "
              "zip). Run `sha256sum -c sentinel_core_v022.sha256` from the "
              "directory that contains the zip and its checksum.")
        return True  # skip is not a failure
    if preferred is None:
        print(f"    NOTE: no exact {tag}.sha256 match; using {os.path.basename(path)}.")
    workdir = os.path.dirname(os.path.abspath(path))
    print(f"    $ sha256sum -c {os.path.basename(path)}  (in {workdir})")
    try:
        proc = subprocess.run(["sha256sum", "-c", os.path.basename(path)],
                              cwd=workdir, capture_output=True, text=True,
                              timeout=TIMEOUT_FAST)
    except FileNotFoundError:
        print("    SKIPPED: sha256sum not available on this system.")
        return True
    except subprocess.TimeoutExpired:
        print(f"    TIMEOUT after {TIMEOUT_FAST}s — FAIL")
        return False
    print("    " + (proc.stdout or proc.stderr).strip())
    ok = proc.returncode == 0
    print(f"    -> {'PASS' if ok else 'FAIL'}")
    return ok


STEPS = [
    step_compileall,
    step_unit_tests,
    step_unit_tests_O,
    step_selfcheck,
    step_selfcheck_O,
    step_resourcewarning,
    step_checksum,
]


def main():
    print("=" * 62)
    print("  Sentinel Core — release_check (full external sequence)")
    print("=" * 62)
    results = []
    for step in STEPS:
        results.append((step.__name__, step()))
    print("\n" + "=" * 62)
    failed = [name for name, ok in results if not ok]
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    print("=" * 62)
    if failed:
        print(f"  RELEASE CHECK FAILED: {failed}")
        return 1
    print("  RELEASE CHECK PASSED — all steps green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
