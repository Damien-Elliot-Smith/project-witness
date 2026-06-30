# tests/test_two_stage.py
# v0.2 two-stage INTENT/RESULT receipt model.
#
# Covers the behaviours the v0.2 repair adds on top of the existing guarantees:
# INTENT-before-mkdir durability, the RESULT-missing-after-INTENT incomplete
# state, the pairing invariants, and replay/append/close handling of all of it.

import hashlib
import json
import os
import shutil
import unittest
from unittest import mock

from sentinel_core.canonical import canonical_json
from sentinel_core.errors import (
    PersistenceFailure, ChainVerificationError, SessionClosedError,
)
from sentinel_core.journal import Journal
from sentinel_core.kernel import Kernel
from sentinel_core.manifest import build_manifest
from sentinel_core.persistence import (
    AtomicFileBackend, FailingTestBackend, FailAfterNWritesBackend,
)
from sentinel_core.receipts import ReceiptChain
from sentinel_core.reason_codes import (
    STAGE_INTENT, STAGE_RESULT, STAGE_SESSION_CLOSE,
    INTENT_CREATE_DIRECTORY, ALLOW_CREATE_DIRECTORY, ERROR_EXECUTION_FAILED,
    ERROR_POSTCONDITION_FAILED,
)
from sentinel_core.replay import (
    replay_from_path,
    VERDICT_PASS_STRICT, VERDICT_PASS_WITH_ENVIRONMENTAL_EXCEPTIONS,
    VERDICT_FAIL, VERDICT_REPLAY_INCOMPATIBLE,
)
from sentinel_core.run_loader import open_run_for_append
from tests.helpers import make_request, new_kernel, temp_root, temp_runs


def _rehash(rd):
    payload = {k: v for k, v in rd.items() if k != "canonical_hash"}
    rd["canonical_hash"] = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    return rd


class TestTwoStage(unittest.TestCase):
    def setUp(self):
        self.root = temp_root()
        self.runs = temp_runs()

    def tearDown(self):
        for d in (self.root, self.runs):
            shutil.rmtree(d, ignore_errors=True)

    def _load(self, path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _write(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    # ── Happy path ─────────────────────────────────────────────────────────
    def test_valid_create_produces_intent_then_result(self):
        k, path = new_kernel("r", self.root, self.runs)
        result = k.process(make_request("R1", "made"))
        data = self._load(path)
        self.assertEqual([r["stage"] for r in data["receipts"]], [STAGE_INTENT, STAGE_RESULT])
        intent, res = data["receipts"]
        self.assertEqual(intent["reason_code"], INTENT_CREATE_DIRECTORY)
        self.assertEqual(intent["executed"], False)
        self.assertIsNone(intent["intent_receipt_id"])
        self.assertEqual(res["reason_code"], ALLOW_CREATE_DIRECTORY)
        self.assertEqual(res["executed"], True)
        self.assertEqual(res["intent_receipt_id"], 0)
        self.assertEqual(res["intent_hash"], intent["canonical_hash"])
        self.assertEqual(result.receipt_id, 1)

    def test_intent_is_persisted_before_mkdir(self):
        # Spy on mkdir: at the moment it is called, the INTENT must already be
        # on disk. We assert the file contains exactly the INTENT at that point.
        k, path = new_kernel("r", self.root, self.runs)
        seen = {}
        import sentinel_core.kernel as kmod
        real = kmod.execute_create_directory

        def spy(target):
            with open(path, encoding="utf-8") as f:
                seen["receipts_at_mkdir"] = json.load(f)["receipts"]
            return real(target)

        with mock.patch.object(kmod, "execute_create_directory", side_effect=spy):
            k.process(make_request("R1", "made"))
        stages = [r["stage"] for r in seen["receipts_at_mkdir"]]
        self.assertEqual(stages, [STAGE_INTENT])  # only the INTENT was on disk when mkdir ran

    # ── Failure rules ──────────────────────────────────────────────────────
    def test_intent_persistence_failure_means_no_directory(self):
        k = Kernel(Journal(FailingTestBackend(), ReceiptChain("r"), build_manifest("r", self.root)))
        with self.assertRaises(PersistenceFailure):
            k.process(make_request("R1", "nope"))
        self.assertFalse(os.path.exists(os.path.join(self.root, "nope")))
        self.assertEqual(k._journal.chain.next_id(), 0)

    def test_mkdir_failure_after_intent_produces_error_result(self):
        k, path = new_kernel("r", self.root, self.runs)
        import sentinel_core.kernel as kmod
        with mock.patch.object(kmod, "execute_create_directory",
                               side_effect=PersistenceFailure("boom")):
            res = k.process(make_request("R1", "made"))
        self.assertEqual(res.stage, STAGE_RESULT)
        self.assertEqual(res.reason_code, ERROR_EXECUTION_FAILED)
        self.assertEqual(res.intent_receipt_id, 0)
        self.assertEqual(k.session_state, "OPEN")
        # The run is complete (INTENT has a matching RESULT) and still replayable
        # after a clean close.
        k.close_session()
        ok, report = replay_from_path(path)
        self.assertTrue(ok, report)

    def test_postcondition_failure_after_intent_produces_error_result(self):
        k, path = new_kernel("r", self.root, self.runs)
        import sentinel_core.kernel as kmod
        real = kmod.os.path.isdir

        def lying(p):
            return False if os.path.basename(p) == "made" else real(p)

        with mock.patch("sentinel_core.kernel.os.path.isdir", side_effect=lying):
            res = k.process(make_request("R1", "made"))
        self.assertEqual(res.reason_code, ERROR_POSTCONDITION_FAILED)
        self.assertEqual(res.intent_receipt_id, 0)
        self.assertEqual(res.stage, STAGE_RESULT)

    def test_result_persistence_failure_leaves_incomplete_run(self):
        # INTENT write succeeds (#1), mkdir runs, RESULT write (#2) fails.
        run_path = os.path.join(self.runs, "r.json")
        backend = FailAfterNWritesBackend(AtomicFileBackend(run_path), n_ok=1)
        k = Kernel(Journal(backend, ReceiptChain("r"), build_manifest("r", self.root)))
        with self.assertRaises(PersistenceFailure):
            k.process(make_request("R1", "made"))
        self.assertTrue(os.path.isdir(os.path.join(self.root, "made")))  # side effect exists
        data = self._load(run_path)
        self.assertEqual([r["stage"] for r in data["receipts"]], [STAGE_INTENT])  # RESULT missing
        # The incomplete run is detected and refused for append AND replay.
        with self.assertRaises(ChainVerificationError):
            open_run_for_append(run_path)
        ok, report = replay_from_path(run_path, allow_open=True)
        self.assertFalse(ok)
        self.assertIn("RESULT_MISSING_AFTER_INTENT", report)

    # ── Append / close refuse unresolved intent ────────────────────────────
    def _make_incomplete_run(self):
        run_path = os.path.join(self.runs, "inc.json")
        backend = FailAfterNWritesBackend(AtomicFileBackend(run_path), n_ok=1)
        k = Kernel(Journal(backend, ReceiptChain("inc"), build_manifest("inc", self.root)))
        try:
            k.process(make_request("R1", "made"))
        except PersistenceFailure:
            pass
        return run_path

    def test_append_refuses_unresolved_intent(self):
        run_path = self._make_incomplete_run()
        with self.assertRaises(ChainVerificationError):
            open_run_for_append(run_path)

    def test_close_refuses_unresolved_intent_in_memory(self):
        # An in-memory kernel that has emitted an INTENT but not its RESULT must
        # refuse to close. We simulate by committing only an INTENT through a
        # backend that fails the RESULT write, then attempting close on a fresh
        # loader is impossible (it refuses to load), so we assert the in-memory
        # guard via a kernel whose RESULT failed.
        run_path = os.path.join(self.runs, "r.json")
        backend = FailAfterNWritesBackend(AtomicFileBackend(run_path), n_ok=1)
        k = Kernel(Journal(backend, ReceiptChain("r"), build_manifest("r", self.root)))
        with self.assertRaises(PersistenceFailure):
            k.process(make_request("R1", "made"))
        # The INTENT is committed in memory but unresolved; close must refuse.
        with self.assertRaises(SessionClosedError):
            k.close_session()

    # ── Replay pairing invariants ──────────────────────────────────────────
    def _valid_closed_run(self):
        k, path = new_kernel("r", self.root, self.runs)
        k.process(make_request("A", "a"))
        k.process(make_request("B", "b"))
        k.close_session()
        return path

    def test_replay_valid_two_stage_passes(self):
        ok, report = replay_from_path(self._valid_closed_run())
        self.assertTrue(ok, report)

    # ── v0.2.2 replay verdict categories ───────────────────────────────────
    def test_clean_run_is_pass_strict(self):
        result = replay_from_path(self._valid_closed_run())
        self.assertTrue(result.ok)
        self.assertEqual(result.verdict, VERDICT_PASS_STRICT)
        self.assertIn("PASS_STRICT", result.report)
        self.assertNotIn("MATCH*", result.report)

    def _genuine_execution_error_run(self):
        # A real mkdir failure (not forged): inject a failing executor for ONE
        # action so the kernel records ERROR_EXECUTION_FAILED, then close.
        import sentinel_core.kernel as kmod
        k, path = new_kernel("r", self.root, self.runs)
        with mock.patch.object(kmod, "execute_create_directory",
                               side_effect=PersistenceFailure("disk full (injected)")):
            res = k.process(make_request("A", "boom"))
        self.assertEqual(res.reason_code, ERROR_EXECUTION_FAILED)
        k.close_session()
        return path

    def test_genuine_execution_error_run_is_pass_with_env_exceptions(self):
        result = replay_from_path(self._genuine_execution_error_run())
        self.assertTrue(result.ok)  # exit code 0: the run is accepted
        self.assertEqual(result.verdict, VERDICT_PASS_WITH_ENVIRONMENTAL_EXCEPTIONS)
        self.assertIn("MATCH*", result.report)
        self.assertIn("structurally verified", result.report)
        self.assertNotIn("PASS_STRICT", result.report)

    def test_genuine_postcondition_error_run_is_pass_with_env_exceptions(self):
        import sentinel_core.kernel as kmod
        real_isdir = kmod.os.path.isdir
        k, path = new_kernel("r", self.root, self.runs)

        def lying(p):
            return False if os.path.basename(p) == "ghost" else real_isdir(p)

        with mock.patch("sentinel_core.kernel.os.path.isdir", side_effect=lying):
            res = k.process(make_request("A", "ghost"))
        self.assertEqual(res.reason_code, ERROR_POSTCONDITION_FAILED)
        k.close_session()
        result = replay_from_path(path)
        self.assertTrue(result.ok)
        self.assertEqual(result.verdict, VERDICT_PASS_WITH_ENVIRONMENTAL_EXCEPTIONS)

    def test_forged_error_run_reports_env_exceptions_not_strict(self):
        # The reported attack: take a CLEAN successful run and mutate its success
        # RESULT into ERROR_EXECUTION_FAILED, recomputing the receipt hash, the
        # next prior_hash, the close-receipt hash, and the run seal. Under the
        # unkeyed-hash limitation (L4) this is structurally accepted, but the
        # verdict MUST be PASS_WITH_ENVIRONMENTAL_EXCEPTIONS, never PASS_STRICT.
        from sentinel_core.run_seal import compute_run_seal_hash
        k, path = new_kernel("r", self.root, self.runs)
        k.process(make_request("A", "made"))
        k.close_session()

        data = self._load(path)
        # Receipts: [INTENT(0), RESULT(1) success, SESSION_CLOSE(2)]
        forged = data["receipts"][1]
        forged["decision"] = "ERROR"
        forged["reason_code"] = ERROR_EXECUTION_FAILED
        forged["executed"] = False
        _rehash(forged)
        close = data["receipts"][2]
        close["prior_hash"] = forged["canonical_hash"]
        _rehash(close)
        seal = dict(data["run_seal"])
        seal["final_receipt_hash"] = close["canonical_hash"]
        seal["seal_hash"] = compute_run_seal_hash(seal)
        data["run_seal"] = seal
        self._write(path, data)

        result = replay_from_path(path)
        self.assertEqual(result.verdict, VERDICT_PASS_WITH_ENVIRONMENTAL_EXCEPTIONS)
        self.assertNotEqual(result.verdict, VERDICT_PASS_STRICT)
        self.assertTrue(result.ok)  # exit 0 is acceptable; the verdict carries the honesty

    def test_incompatible_version_is_replay_incompatible_verdict(self):
        # An older version vector must yield the REPLAY_INCOMPATIBLE verdict.
        from sentinel_core.manifest import compute_manifest_hash
        runs2 = temp_runs()
        rp = os.path.join(runs2, "old.json")
        m = {"impl_version": "0.1.3", "receipt_schema_version": "0.1.1",
             "action_schema_version": "1.1.0", "policy_version": "0.1.1",
             "reason_registry_version": "0.1.0", "session_version": "0.1.0",
             "manifest_version": "0.1.0", "run_id": "old", "allowed_root": runs2,
             "initial_session_state": "OPEN"}
        m["manifest_hash"] = compute_manifest_hash(m)
        with open(rp, "w", encoding="utf-8") as f:
            json.dump({"manifest": m, "receipts": [], "run_seal": None}, f)
        result = replay_from_path(rp, allow_open=True)
        self.assertFalse(result.ok)
        self.assertEqual(result.verdict, VERDICT_REPLAY_INCOMPATIBLE)
        shutil.rmtree(runs2, ignore_errors=True)

    def test_structural_failure_is_fail_verdict(self):
        path = self._valid_closed_run()
        data = self._load(path)
        data["receipts"][1]["executed"] = False  # tamper without rehash
        self._write(path, data)
        result = replay_from_path(path)
        self.assertFalse(result.ok)
        self.assertEqual(result.verdict, VERDICT_FAIL)

    def test_replay_missing_result_fails(self):
        path = self._valid_closed_run()
        data = self._load(path)
        # Remove the RESULT of the first action (index 1). Renumber? No — we
        # delete it to simulate loss; chain becomes non-contiguous -> fail.
        del data["receipts"][1]
        self._write(path, data)
        ok, _ = replay_from_path(path)
        self.assertFalse(ok)

    def test_replay_missing_intent_fails(self):
        path = self._valid_closed_run()
        data = self._load(path)
        del data["receipts"][0]  # delete an INTENT; its RESULT now dangles
        self._write(path, data)
        ok, _ = replay_from_path(path)
        self.assertFalse(ok)

    def test_replay_duplicate_result_fails(self):
        path = self._valid_closed_run()
        data = self._load(path)
        data["receipts"].insert(2, dict(data["receipts"][1]))  # duplicate a RESULT
        self._write(path, data)
        ok, _ = replay_from_path(path)
        self.assertFalse(ok)

    def test_mutating_intent_target_fails(self):
        path = self._valid_closed_run()
        data = self._load(path)
        data["receipts"][0]["request"]["target_path"] = "evil"  # mutate INTENT
        self._write(path, data)
        ok, _ = replay_from_path(path)
        self.assertFalse(ok)

    def test_mutating_result_outcome_fails(self):
        path = self._valid_closed_run()
        data = self._load(path)
        data["receipts"][1]["executed"] = False  # mutate RESULT outcome
        self._write(path, data)
        ok, _ = replay_from_path(path)
        self.assertFalse(ok)

    def test_result_with_wrong_intent_hash_fails(self):
        path = self._valid_closed_run()
        data = self._load(path)
        data["receipts"][1]["intent_hash"] = "b" * 64
        _rehash(data["receipts"][1])  # recompute so only the linkage is wrong
        self._write(path, data)
        ok, _ = replay_from_path(path)
        self.assertFalse(ok)

    def test_second_result_for_same_intent_fails(self):
        # Forge a chain: INTENT(0), RESULT(1)->0, RESULT(2)->0 again.
        path = self._valid_closed_run()
        data = self._load(path)
        dup = dict(data["receipts"][1])  # RESULT referencing INTENT 0
        dup["receipt_id"] = 2
        data["receipts"] = data["receipts"][:2] + [dup]
        # Don't bother rehashing perfectly; either hash or pairing check fails.
        self._write(path, data)
        ok, _ = replay_from_path(path)
        self.assertFalse(ok)

    # ── Preserved guarantees still hold ────────────────────────────────────
    def test_authoritative_root_still_enforced(self):
        k, _ = new_kernel("r", self.root, self.runs)
        attack = make_request("R1", "x")
        attack["allowed_root"] = temp_root()  # self-declared root
        res = k.process(attack)
        self.assertEqual(res.reason_code, "BLOCK_SCHEMA_INVALID")
        self.assertEqual(res.stage, STAGE_RESULT)

    def test_deleted_final_receipt_still_fails(self):
        path = self._valid_closed_run()
        data = self._load(path)
        data["receipts"] = data["receipts"][:-1]  # drop close
        self._write(path, data)
        ok, _ = replay_from_path(path)
        self.assertFalse(ok)

    def test_deleted_seal_still_fails(self):
        path = self._valid_closed_run()
        data = self._load(path)
        data["run_seal"] = None
        self._write(path, data)
        ok, _ = replay_from_path(path)
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
