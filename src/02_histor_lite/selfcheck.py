#!/usr/bin/env python3
# selfcheck.py
# Histor-lite v0.1.2 self-check: in-process invariant gates only.
#
# Like Sentinel, selfcheck NEVER launches the unit-test suite or any subprocess.
# It runs internal checks in-process. The full release sequence lives in
# release_check.py.

import ast
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from histor_lite.canonical import canonical_json, canonical_bytes, hash_file  # noqa: E402
from histor_lite.errors import require, ImportRefused, HistorLiteError  # noqa: E402
from histor_lite.sentinel_import import import_sentinel_run  # noqa: E402
from histor_lite.case_summary import verify_case, CASE_SUMMARY_NAME  # noqa: E402
from histor_lite import versions  # noqa: E402

# selfcheck builds its own minimal stub Sentinel root, so it does not depend on
# an external Sentinel checkout being present. The stub stands in for "the frozen
# verifier returned verdict X"; it does not reimplement Sentinel semantics.
sys.path.insert(0, os.path.join(HERE, "tests"))
from helpers import build_stub_sentinel_root, write_stub_run  # noqa: E402


def _ok(cond, msg):
    require(cond, msg, HistorLiteError)


def gate_imports():
    import histor_lite  # noqa: F401
    from histor_lite import canonical, errors, verifier, case_summary, sentinel_import  # noqa: F401
    _ok(versions.HISTOR_LITE_VERSION == "0.1.2", "Unexpected histor_lite version")


def gate_canonical_json():
    a = {"b": 1, "a": 2, "nested": {"y": 1, "x": 2}}
    out1 = canonical_json(a)
    out2 = canonical_json({"nested": {"x": 2, "y": 1}, "a": 2, "b": 1})
    _ok(out1 == out2, "canonical_json is not order-independent/deterministic")
    _ok(out1.endswith("\n"), "canonical_json must end with a newline")
    _ok('"a":2' in out1 and out1.index('"a"') < out1.index('"b"'),
        "canonical_json keys are not sorted")
    try:
        canonical_json({"x": float("nan")})
        _ok(False, "canonical_json must reject NaN")
    except HistorLiteError:
        pass


def gate_hash_file():
    d = tempfile.mkdtemp()
    try:
        p = os.path.join(d, "x.bin")
        with open(p, "wb") as f:
            f.write(b"hello")
        import hashlib
        _ok(hash_file(p) == hashlib.sha256(b"hello").hexdigest(),
            "hash_file digest mismatch")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def gate_valid_pass_strict_import():
    root = build_stub_sentinel_root()
    work = tempfile.mkdtemp()
    try:
        run = write_stub_run(os.path.join(work, "run.json"), "PASS_STRICT")
        out = os.path.join(work, "case")
        result = import_sentinel_run(sentinel_root=root, run_path=run, out_dir=out,
                                     now_utc="2026-01-01T00:00:00Z")
        _ok(result.import_status == versions.STATUS_IMPORTED,
            f"expected IMPORTED, got {result.import_status}")
        _ok(result.case_summary["sentinel_replay_verdict"] == "PASS_STRICT",
            "verdict not preserved")
        _ok(os.path.isfile(os.path.join(out, "case_summary.json")), "no case_summary.json")
        _ok(os.path.isfile(os.path.join(out, "sentinel_replay_report.txt")), "no report")
        _ok(os.path.isfile(os.path.join(out, "checksums.txt")), "no checksums.txt")
        # environmental-exceptions verdict must be preserved, not relabelled
        run2 = write_stub_run(os.path.join(work, "run2.json"),
                              "PASS_WITH_ENVIRONMENTAL_EXCEPTIONS")
        out2 = os.path.join(work, "case2")
        r2 = import_sentinel_run(sentinel_root=root, run_path=run2, out_dir=out2,
                                 now_utc="2026-01-01T00:00:00Z")
        _ok(r2.import_status == versions.STATUS_IMPORTED_WITH_ENVIRONMENTAL_EXCEPTIONS,
            "env-exceptions status not assigned")
        _ok(r2.case_summary["sentinel_replay_verdict"] == "PASS_WITH_ENVIRONMENTAL_EXCEPTIONS",
            "env-exceptions verdict not preserved exactly")
    finally:
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(work, ignore_errors=True)


def gate_refuse_failed_replay():
    root = build_stub_sentinel_root()
    work = tempfile.mkdtemp()
    try:
        for verdict, reason in [("FAIL", "SENTINEL_REPLAY_FAIL"),
                                ("REPLAY_INCOMPATIBLE", "SENTINEL_REPLAY_INCOMPATIBLE")]:
            run = write_stub_run(os.path.join(work, f"{verdict}.json"), verdict)
            out = os.path.join(work, f"case_{verdict}")
            refused = False
            try:
                import_sentinel_run(sentinel_root=root, run_path=run, out_dir=out)
            except ImportRefused as e:
                refused = True
                _ok(e.reason == reason, f"wrong refusal reason for {verdict}: {e.reason}")
            _ok(refused, f"{verdict} was not refused")
            _ok(not os.path.isdir(out) or not os.path.isfile(
                os.path.join(out, "case_summary.json")),
                f"{verdict} wrote a case summary despite refusal")
    finally:
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(work, ignore_errors=True)


def gate_case_summary_verify():
    root = build_stub_sentinel_root()
    work = tempfile.mkdtemp()
    try:
        run = write_stub_run(os.path.join(work, "run.json"), "PASS_STRICT")
        out = os.path.join(work, "case")
        import_sentinel_run(sentinel_root=root, run_path=run, out_dir=out,
                            now_utc="2026-01-01T00:00:00Z")
        res = verify_case(out)
        _ok(res["integrity"] == "OK", "verify_case did not report OK on a clean case")
        # mutate case_summary.json -> verify must detect it
        sp = os.path.join(out, CASE_SUMMARY_NAME)
        with open(sp, "r+", encoding="utf-8") as f:
            data = f.read().replace("PASS_STRICT", "PASS_TAMPERED")
            f.seek(0); f.write(data); f.truncate()
        detected = False
        try:
            verify_case(out)
        except HistorLiteError:
            detected = True
        _ok(detected, "verify_case did not detect a mutated case_summary.json")
    finally:
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(work, ignore_errors=True)


def gate_no_bare_asserts():
    pkg = os.path.join(HERE, "histor_lite")
    offenders = []
    for dirpath, _, names in os.walk(pkg):
        for n in names:
            if n.endswith(".py"):
                p = os.path.join(dirpath, n)
                with open(p, encoding="utf-8") as fh:
                    tree = ast.parse(fh.read(), filename=p)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assert):
                        offenders.append(f"{n}:{node.lineno}")
    _ok(offenders == [], f"bare asserts in histor_lite/: {offenders}")


def gate_refuse_inconsistent_verdict():
    # Issue 1 guard: an accepted-looking PASS verdict with ok=False must be
    # refused as SENTINEL_VERDICT_INCONSISTENT, never imported.
    root = build_stub_sentinel_root()
    work = tempfile.mkdtemp()
    try:
        run = write_stub_run(os.path.join(work, "incon.json"), "PASS_STRICT", ok=False)
        refused = False
        try:
            import_sentinel_run(sentinel_root=root, run_path=run,
                                out_dir=os.path.join(work, "case"))
        except ImportRefused as e:
            refused = True
            _ok(e.reason == "SENTINEL_VERDICT_INCONSISTENT",
                f"wrong reason for inconsistent verdict: {e.reason}")
        _ok(refused, "PASS_STRICT with ok=False was not refused")
    finally:
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(work, ignore_errors=True)


GATES = [
    ("imports", gate_imports),
    ("canonical_json", gate_canonical_json),
    ("hash_file", gate_hash_file),
    ("valid_pass_strict_import", gate_valid_pass_strict_import),
    ("refuse_failed_replay", gate_refuse_failed_replay),
    ("refuse_inconsistent_verdict", gate_refuse_inconsistent_verdict),
    ("case_summary_verify", gate_case_summary_verify),
    ("no_bare_asserts", gate_no_bare_asserts),
]


def main(argv=None):
    import argparse
    argparse.ArgumentParser(prog="selfcheck",
                            description="Histor-lite v0.1.2 in-process gates.").parse_args(argv)
    print("=" * 60)
    print("  Histor-lite v0.1.2 — selfcheck (in-process gates)")
    print("=" * 60)
    passed = 0
    failed = []
    for name, fn in GATES:
        try:
            fn()
            print(f"  [PASS] {name}")
            passed += 1
        except Exception as e:  # noqa: BLE001
            print(f"  [FAIL] {name}: {e}")
            failed.append(name)
    print("=" * 60)
    print(f"  {passed}/{len(GATES)} gates passed")
    if failed:
        print(f"  FAILED: {failed}")
        return 1
    print("  ALL PASS — Histor-lite v0.1.2 selfcheck satisfied.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
