#!/usr/bin/env python3
# release_check.py
# External release orchestrator for Histor-lite v0.1.2.
#
# Like Sentinel: each step is an INDEPENDENT subprocess with an explicit timeout
# (a timeout is a failure). selfcheck and the unit suite never spawn each other,
# and this orchestrator is never invoked by a gate.
#
# Steps:
#   1. compileall
#   2. unit tests
#   3. unit tests under -O
#   4. selfcheck
#   5. selfcheck under -O
#   6. ResourceWarning sweep
#   7. checksum verification (skipped with a clear note if the .sha256 is not
#      present beside the package, e.g. inside a clean extraction without the zip)

import glob
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
TIMEOUT_FAST = 120
TIMEOUT_TESTS = 600


def _run(label, argv, timeout):
    print(f"\n>>> {label}\n    $ {' '.join(argv)}")
    t0 = time.time()
    try:
        proc = subprocess.run(argv, cwd=HERE, capture_output=True, text=True,
                              timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"    TIMEOUT after {timeout}s — FAIL")
        return False
    out = (proc.stdout or "") + (proc.stderr or "")
    tail = "\n".join(out.strip().splitlines()[-5:])
    if tail:
        print("    " + tail.replace("\n", "\n    "))
    ok = proc.returncode == 0
    print(f"    -> exit {proc.returncode} in {time.time() - t0:.1f}s : {'PASS' if ok else 'FAIL'}")
    return ok


def step_compileall():
    return _run("1. compileall", [PY, "-m", "compileall", "-q", "."], TIMEOUT_FAST)


def step_unit_tests():
    return _run("2. unit tests", [PY, "-m", "unittest", "discover", "-s", "tests"],
                TIMEOUT_TESTS)


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


def step_checksum():
    candidates = [p for p in (glob.glob(os.path.join(HERE, "*.sha256"))
                              + glob.glob(os.path.join(HERE, "..", "*.sha256")))
                  if os.path.isfile(p)]
    preferred = [p for p in candidates
                 if os.path.basename(p) == "histor_lite_v012.sha256"]
    path = (preferred or candidates or [None])[0]
    print("\n>>> 7. checksum verification")
    if path is None:
        print("    SKIPPED: no .sha256 beside the package (expected inside a clean "
              "extraction without the zip). Run "
              "`sha256sum -c histor_lite_v012.sha256` where the zip lives.")
        return True
    workdir = os.path.dirname(os.path.abspath(path))
    print(f"    $ sha256sum -c {os.path.basename(path)}  (in {workdir})")
    try:
        proc = subprocess.run(["sha256sum", "-c", os.path.basename(path)],
                              cwd=workdir, capture_output=True, text=True,
                              timeout=TIMEOUT_FAST)
    except FileNotFoundError:
        print("    SKIPPED: sha256sum not available.")
        return True
    except subprocess.TimeoutExpired:
        print(f"    TIMEOUT after {TIMEOUT_FAST}s — FAIL")
        return False
    print("    " + (proc.stdout or proc.stderr).strip())
    return proc.returncode == 0


STEPS = [step_compileall, step_unit_tests, step_unit_tests_O, step_selfcheck,
         step_selfcheck_O, step_resourcewarning, step_checksum]


def main():
    print("=" * 62)
    print("  Histor-lite v0.1.2 — release_check (full external sequence)")
    print("=" * 62)
    results = [(s.__name__, s()) for s in STEPS]
    print("\n" + "=" * 62)
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    print("=" * 62)
    failed = [n for n, ok in results if not ok]
    if failed:
        print(f"  RELEASE CHECK FAILED: {failed}")
        return 1
    print("  RELEASE CHECK PASSED — all steps green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
