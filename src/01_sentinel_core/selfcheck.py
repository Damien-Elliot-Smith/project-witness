#!/usr/bin/env python3
# selfcheck.py
# Sentinel Core v0.2.2 self-check. Runs a fixed battery of gates and prints a
# pass/fail summary. Exits non-zero if any gate fails. Uses explicit raises and
# the require() helper — never a bare assert — so it behaves identically under
# python -O.

import ast
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from sentinel_core.errors import require, SentinelError  # noqa: E402


class GateFailure(SentinelError):
    pass


def _ok(condition, message):
    require(condition, message, GateFailure)


# ── Gate implementations ────────────────────────────────────────────────────

def gate_imports():
    import sentinel_core  # noqa
    from sentinel_core import (  # noqa
        versions, canonical, errors, action_schema, path_policy, decision,
        receipts, manifest, run_seal, journal, persistence, replay, kernel,
        reason_codes, session,
    )
    _ok(sentinel_core.PACKAGE_VERSION == "0.2.2", "Unexpected package version")


def gate_compileall():
    import compileall
    ok = compileall.compile_dir(os.path.join(HERE, "sentinel_core"), quiet=1, force=True)
    _ok(bool(ok), "compileall failed for sentinel_core")


# NOTE (v0.1.4): selfcheck NO LONGER launches the unit-test suite. In v0.1.2/3
# the unit_tests and unit_tests_-O gates ran `unittest discover` as a
# subprocess; that subprocess ran a test which spawned ANOTHER selfcheck
# subprocess, and the inherited capture pipes could deadlock (intermittently,
# typically on the second/-O pass). selfcheck is now purely internal,
# in-process invariant gates with NO subprocesses. The full release sequence
# (unit suites + selfcheck + -O + ResourceWarning + checksum) lives in
# release_check.py, which runs each step as an independent, timed subprocess
# and never lets a gate spawn another gate.


def gate_no_bare_assert():
    offenders = []
    targets = [os.path.join(HERE, "sentinel_core"), os.path.join(HERE, "selfcheck.py"),
               os.path.join(HERE, "sentinel.py")]
    py_files = []
    for t in targets:
        if os.path.isdir(t):
            for dirpath, _, names in os.walk(t):
                py_files.extend(os.path.join(dirpath, n) for n in names if n.endswith(".py"))
        elif t.endswith(".py"):
            py_files.append(t)
    for path in py_files:
        with open(path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                offenders.append(f"{os.path.relpath(path, HERE)}:{node.lineno}")
    _ok(not offenders, f"Bare assert statements found: {offenders}")


def _new_kernel(run_id, root, runs):
    from sentinel_core.journal import Journal
    from sentinel_core.kernel import Kernel
    from sentinel_core.manifest import build_manifest
    from sentinel_core.persistence import AtomicFileBackend
    from sentinel_core.receipts import ReceiptChain
    run_path = os.path.join(runs, f"{run_id}.json")
    return Kernel(Journal(AtomicFileBackend(run_path), ReceiptChain(run_id),
                          build_manifest(run_id, root))), run_path


def _req(rid, target, dry=False, action="CREATE_DIRECTORY"):
    return {
        "request_id": rid, "action_type": action, "target_path": target,
        "dry_run": dry,
        "preconditions": ["target_absent", "parent_exists", "inside_allowed_root"],
        "postconditions": ["target_exists", "target_is_directory"],
        "schema_version": "1.1.0",
    }


def _req_text(rid, target, content="hello\n", prefix=".", dry=False):
    return {
        "request_id": rid, "action_type": "CREATE_TEXT_FILE", "target_path": target,
        "content": content, "allowed_path_prefix": prefix, "dry_run": dry,
        "preconditions": ["parent_directory_exists", "path_absent", "path_inside_allowed_prefix"],
        "postconditions": ["file_exists", "file_content_hash_matches", "file_is_utf8_text"],
        "schema_version": "1.1.0",
    }


def gate_valid_workflow():
    root = tempfile.mkdtemp(); runs = tempfile.mkdtemp()
    try:
        k, _ = _new_kernel("wf", root, runs)
        r = k.process(_req("A", "demo"))
        _ok(r.decision == "ALLOW" and r.executed, "Valid CREATE_DIRECTORY did not ALLOW+execute")
        _ok(os.path.isdir(os.path.join(root, "demo")), "Directory was not created")
    finally:
        shutil.rmtree(root, ignore_errors=True); shutil.rmtree(runs, ignore_errors=True)


def gate_dry_run_no_create():
    root = tempfile.mkdtemp(); runs = tempfile.mkdtemp()
    try:
        k, _ = _new_kernel("dr", root, runs)
        r = k.process(_req("A", "ghost", dry=True))
        _ok(r.decision == "DRY_RUN", "Dry-run did not yield DRY_RUN")
        _ok(not os.path.exists(os.path.join(root, "ghost")), "Dry-run created a directory")
    finally:
        shutil.rmtree(root, ignore_errors=True); shutil.rmtree(runs, ignore_errors=True)


def gate_traversal_blocked():
    root = tempfile.mkdtemp(); runs = tempfile.mkdtemp()
    try:
        k, _ = _new_kernel("tv", root, runs)
        r = k.process(_req("A", "../escape"))
        _ok(r.reason_code == "BLOCK_PATH_TRAVERSAL", "Traversal not blocked")
    finally:
        shutil.rmtree(root, ignore_errors=True); shutil.rmtree(runs, ignore_errors=True)


def gate_outside_root_blocked():
    root = tempfile.mkdtemp(); runs = tempfile.mkdtemp(); outside = tempfile.mkdtemp()
    try:
        k, _ = _new_kernel("or", root, runs)
        r = k.process(_req("A", os.path.join(outside, "x")))
        _ok(r.reason_code == "BLOCK_ABSOLUTE_TARGET_NOT_ALLOWED", "Outside-root not blocked")
    finally:
        for d in (root, runs, outside):
            shutil.rmtree(d, ignore_errors=True)


def gate_text_file_valid_workflow():
    root = tempfile.mkdtemp(); runs = tempfile.mkdtemp()
    try:
        k, _ = _new_kernel("tfwf", root, runs)
        r = k.process(_req_text("A", "note.txt", "hello world\n"))
        _ok(r.decision == "ALLOW" and r.reason_code == "ALLOW_CREATE_TEXT_FILE" and r.executed,
            "Valid CREATE_TEXT_FILE did not ALLOW+execute")
        p = os.path.join(root, "note.txt")
        _ok(os.path.isfile(p) and not os.path.islink(p), "Text file was not created as a regular file")
        with open(p, "rb") as f:
            _ok(f.read().decode("utf-8") == "hello world\n", "Text file content mismatch")
    finally:
        shutil.rmtree(root, ignore_errors=True); shutil.rmtree(runs, ignore_errors=True)


def gate_text_file_dry_run_no_create():
    root = tempfile.mkdtemp(); runs = tempfile.mkdtemp()
    try:
        k, _ = _new_kernel("tfdr", root, runs)
        r = k.process(_req_text("A", "ghost.txt", "x\n", dry=True))
        _ok(r.decision == "DRY_RUN" and r.reason_code == "DRY_RUN_CREATE_TEXT_FILE",
            "Text-file dry-run did not yield DRY_RUN")
        _ok(not os.path.exists(os.path.join(root, "ghost.txt")), "Text-file dry-run created a file")
    finally:
        shutil.rmtree(root, ignore_errors=True); shutil.rmtree(runs, ignore_errors=True)


def gate_text_file_traversal_blocked():
    root = tempfile.mkdtemp(); runs = tempfile.mkdtemp()
    try:
        k, _ = _new_kernel("tftv", root, runs)
        r = k.process(_req_text("A", "../escape.txt", "x\n"))
        _ok(r.reason_code == "BLOCK_PATH_TRAVERSAL", "Text-file traversal not blocked")
    finally:
        shutil.rmtree(root, ignore_errors=True); shutil.rmtree(runs, ignore_errors=True)


def gate_text_file_target_exists_blocked():
    root = tempfile.mkdtemp(); runs = tempfile.mkdtemp()
    try:
        k, _ = _new_kernel("tfex", root, runs)
        k.process(_req_text("A", "a.txt", "one\n"))
        r = k.process(_req_text("B", "a.txt", "two\n"))
        _ok(r.reason_code == "BLOCK_TARGET_ALREADY_EXISTS", "Text-file overwrite not blocked")
        with open(os.path.join(root, "a.txt")) as f:
            _ok(f.read() == "one\n", "Text-file was overwritten")
    finally:
        shutil.rmtree(root, ignore_errors=True); shutil.rmtree(runs, ignore_errors=True)


def gate_text_file_binary_content_blocked():
    root = tempfile.mkdtemp(); runs = tempfile.mkdtemp()
    try:
        k, _ = _new_kernel("tfbin", root, runs)
        r = k.process(_req_text("A", "b.txt", "a\x00b"))
        _ok(r.reason_code == "BLOCK_SCHEMA_INVALID", "Binary (NUL) content not blocked")
        _ok(not os.path.exists(os.path.join(root, "b.txt")), "Binary-content file was created")
    finally:
        shutil.rmtree(root, ignore_errors=True); shutil.rmtree(runs, ignore_errors=True)


def _build_closed_run(root, runs, run_id="sc"):
    k, run_path = _new_kernel(run_id, root, runs)
    k.process(_req("A", "demo"))
    k.process(_req("B", "demo/output"))
    k.close_session()
    return run_path


def gate_replay_valid():
    from sentinel_core.replay import replay_from_path
    root = tempfile.mkdtemp(); runs = tempfile.mkdtemp()
    try:
        path = _build_closed_run(root, runs)
        ok, report = replay_from_path(path)
        _ok(ok, f"Valid replay failed: {report}")
    finally:
        shutil.rmtree(root, ignore_errors=True); shutil.rmtree(runs, ignore_errors=True)


def gate_deleted_final_receipt_fails():
    from sentinel_core.replay import replay_from_path
    root = tempfile.mkdtemp(); runs = tempfile.mkdtemp()
    try:
        path = _build_closed_run(root, runs)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        data["receipts"] = data["receipts"][:-1]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        ok, _ = replay_from_path(path)
        _ok(not ok, "Deleted final receipt did not fail replay")
    finally:
        shutil.rmtree(root, ignore_errors=True); shutil.rmtree(runs, ignore_errors=True)


def gate_deleted_seal_fails():
    from sentinel_core.replay import replay_from_path
    from sentinel_core.run_seal import RUN_SEAL_FIELD
    root = tempfile.mkdtemp(); runs = tempfile.mkdtemp()
    try:
        path = _build_closed_run(root, runs)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        data[RUN_SEAL_FIELD] = None
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        ok, _ = replay_from_path(path)
        _ok(not ok, "Deleted run_seal did not fail replay")
    finally:
        shutil.rmtree(root, ignore_errors=True); shutil.rmtree(runs, ignore_errors=True)


def gate_hostile_json_fails():
    from sentinel_core.replay import replay_from_path
    runs = tempfile.mkdtemp()
    try:
        path = os.path.join(runs, "hostile.json")
        with open(path, "w") as f:
            f.write("{garbage ::: not json")
        ok, _ = replay_from_path(path)
        _ok(not ok, "Hostile JSON did not fail closed")
        bomb = os.path.join(runs, "bomb.json")
        with open(bomb, "w") as f:
            f.write("[" * 200000 + "]" * 200000)
        ok2, _ = replay_from_path(bomb)
        _ok(not ok2, "Deeply nested JSON did not fail closed")
    finally:
        shutil.rmtree(runs, ignore_errors=True)


def gate_append_integrity():
    from sentinel_core.run_loader import open_run_for_append
    from sentinel_core.errors import SessionClosedError, ChainVerificationError
    root = tempfile.mkdtemp(); runs = tempfile.mkdtemp()
    try:
        # Attack 1: closed run, deleted seal.
        path = _build_closed_run(root, runs, run_id="ai1")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        data["run_seal"] = None
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        before = sorted(os.listdir(root))
        try:
            open_run_for_append(path)
            _ok(False, "Deleted-seal closed run was opened for append")
        except SessionClosedError:
            pass
        _ok(sorted(os.listdir(root)) == before, "Filesystem changed on refused append")

        # Attack 2: open run with deleted first receipt.
        k, path2 = _new_kernel("ai2", root, runs)
        k.process(_req("A", "ai2_a"))
        k.process(_req("B", "ai2_b"))
        with open(path2, encoding="utf-8") as f:
            data2 = json.load(f)
        data2["receipts"] = data2["receipts"][1:]
        with open(path2, "w", encoding="utf-8") as f:
            json.dump(data2, f)
        before = sorted(os.listdir(root))
        try:
            open_run_for_append(path2)
            _ok(False, "Broken-chain open run was opened for append")
        except ChainVerificationError:
            pass
        _ok(sorted(os.listdir(root)) == before, "Filesystem changed on refused append")
    finally:
        shutil.rmtree(root, ignore_errors=True); shutil.rmtree(runs, ignore_errors=True)


def gate_forged_closure_fails():
    # A CREATE receipt forged to CLOSED_BY_OPERATOR with a recomputed hash and a
    # valid seal must NOT pass replay (v0.1.3 blocker-2 repair).
    import hashlib
    from sentinel_core.canonical import canonical_json
    from sentinel_core.run_seal import compute_run_seal_hash
    from sentinel_core.replay import replay_from_path
    root = tempfile.mkdtemp(); runs = tempfile.mkdtemp()
    try:
        k, path = _new_kernel("forge", root, runs)
        k.process(_req("A", "made"))
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        final = data["receipts"][-1]
        final["post_session_state"] = "CLOSED_BY_OPERATOR"
        payload = {kk: vv for kk, vv in final.items() if kk != "canonical_hash"}
        final["canonical_hash"] = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
        seal = {
            "seal_version": "0.1.0", "run_id": data["manifest"]["run_id"],
            "manifest_hash": data["manifest"]["manifest_hash"],
            "receipt_count": len(data["receipts"]),
            "final_receipt_id": final["receipt_id"],
            "final_receipt_hash": final["canonical_hash"],
            "final_session_state": "CLOSED_BY_OPERATOR",
        }
        seal["seal_hash"] = compute_run_seal_hash(seal)
        data["run_seal"] = seal
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        ok, _ = replay_from_path(path)
        _ok(not ok, "Forged-closure run passed replay")
    finally:
        shutil.rmtree(root, ignore_errors=True); shutil.rmtree(runs, ignore_errors=True)


def gate_two_stage_intent_result():
    # A valid CREATE produces INTENT then RESULT; the INTENT is persisted before
    # mkdir; and a run with an unresolved INTENT fails replay.
    import hashlib
    from sentinel_core.replay import replay_from_path
    root = tempfile.mkdtemp(); runs = tempfile.mkdtemp()
    try:
        k, path = _new_kernel("two_stage", root, runs)
        result = k.process(_req("A", "made"))
        _ok(result.stage == "RESULT" and result.intent_receipt_id == 0,
            "ALLOW did not yield a RESULT resolving INTENT #0")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        _ok(data["receipts"][0]["stage"] == "INTENT", "First receipt is not an INTENT")
        _ok(data["receipts"][1]["stage"] == "RESULT", "Second receipt is not a RESULT")
        k.close_session()
        ok, _ = replay_from_path(path)
        _ok(ok, "Valid two-stage run failed replay")

        # Unresolved INTENT (drop the RESULT and the close) -> replay fails.
        k2, path2 = _new_kernel("pending", root, runs)
        k2.process(_req("A", "made2"))
        with open(path2, encoding="utf-8") as f:
            d2 = json.load(f)
        d2["receipts"] = d2["receipts"][:1]  # keep only the INTENT
        with open(path2, "w", encoding="utf-8") as f:
            json.dump(d2, f)
        ok2, _ = replay_from_path(path2, allow_open=True)
        _ok(not ok2, "Run with unresolved INTENT passed replay")
    finally:
        shutil.rmtree(root, ignore_errors=True); shutil.rmtree(runs, ignore_errors=True)


def gate_replay_verdict_categories():
    # A clean run is PASS_STRICT; a run leaning on an environmental ERROR
    # (structurally verified, not re-derived) is PASS_WITH_ENVIRONMENTAL_EXCEPTIONS
    # — never plain strict PASS.
    from sentinel_core.replay import (
        replay_from_path, VERDICT_PASS_STRICT,
        VERDICT_PASS_WITH_ENVIRONMENTAL_EXCEPTIONS,
    )
    from sentinel_core.errors import PersistenceFailure
    import sentinel_core.kernel as kmod
    from unittest import mock
    root = tempfile.mkdtemp(); runs = tempfile.mkdtemp()
    try:
        k, path = _new_kernel("strict", root, runs)
        k.process(_req("A", "ok")); k.close_session()
        r = replay_from_path(path)
        _ok(r.verdict == VERDICT_PASS_STRICT,
            f"clean run verdict was {r.verdict}, expected PASS_STRICT")

        k2, path2 = _new_kernel("env", root, runs)
        with mock.patch.object(kmod, "execute_create_directory",
                               side_effect=PersistenceFailure("injected")):
            k2.process(_req("A", "boom"))
        k2.close_session()
        r2 = replay_from_path(path2)
        _ok(r2.verdict == VERDICT_PASS_WITH_ENVIRONMENTAL_EXCEPTIONS,
            f"environmental-ERROR run verdict was {r2.verdict}, "
            f"expected PASS_WITH_ENVIRONMENTAL_EXCEPTIONS")
        _ok(r2.ok, "environmental-ERROR run should still be accepted (exit 0)")
    finally:
        shutil.rmtree(root, ignore_errors=True); shutil.rmtree(runs, ignore_errors=True)


GATES = [
    ("imports", gate_imports),
    ("compileall", gate_compileall),
    ("no_bare_assert", gate_no_bare_assert),
    ("valid_workflow", gate_valid_workflow),
    ("dry_run_no_create", gate_dry_run_no_create),
    ("traversal_blocked", gate_traversal_blocked),
    ("outside_root_blocked", gate_outside_root_blocked),
    ("text_file_valid_workflow", gate_text_file_valid_workflow),
    ("text_file_dry_run_no_create", gate_text_file_dry_run_no_create),
    ("text_file_traversal_blocked", gate_text_file_traversal_blocked),
    ("text_file_target_exists_blocked", gate_text_file_target_exists_blocked),
    ("text_file_binary_content_blocked", gate_text_file_binary_content_blocked),
    ("replay_valid", gate_replay_valid),
    ("deleted_final_receipt_fails", gate_deleted_final_receipt_fails),
    ("deleted_seal_fails", gate_deleted_seal_fails),
    ("hostile_json_fails", gate_hostile_json_fails),
    ("append_integrity", gate_append_integrity),
    ("forged_closure_fails", gate_forged_closure_fails),
    ("two_stage_intent_result", gate_two_stage_intent_result),
    ("replay_verdict_categories", gate_replay_verdict_categories),
]


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(
        prog="selfcheck",
        description="Sentinel Core v0.2.2 internal-invariant self-check gates.")
    parser.add_argument(
        "--skip-unit-gates", action="store_true",
        help="Accepted for backward compatibility and now a no-op: as of "
             "v0.1.4 selfcheck contains NO unit-test gates (it never launches "
             "the unit suite). The full release sequence lives in "
             "release_check.py. This flag is retained so existing invocations "
             "keep working and exit 0.")
    args = parser.parse_args(argv)
    # args.skip_unit_gates is intentionally ignored; there are no unit gates.

    print("=" * 62)
    print("  Sentinel Core v0.2.2 — selfcheck (internal invariant gates)")
    print("=" * 62)
    passed = 0
    failed = []
    for name, fn in GATES:
        try:
            fn()
            print(f"  [PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            failed.append(name)
    print("=" * 62)
    print(f"  {passed}/{len(GATES)} gates passed")
    if failed:
        print(f"  FAILED gates: {failed}")
        print("=" * 62)
        return 1
    print("  ALL PASS — Sentinel Core v0.2.2 selfcheck satisfied.")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    sys.exit(main())
