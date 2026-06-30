# tests/test_closure_grammar.py
# v0.1.3 release-blocker 2 repair: semantic closure validation.
#
# The forge: take a run whose final receipt is a normal CREATE/BLOCK/DRY_RUN/
# ERROR receipt, edit its post_session_state to CLOSED_BY_OPERATOR, RECOMPUTE
# the receipt hash, and build a fresh valid run seal over it. In v0.1.2 replay
# accepted this as PASS. It must not: only a real ALLOW_SESSION_CLOSE receipt
# (decision=ALLOW, reason=ALLOW_SESSION_CLOSE, request={'action_type':
# 'CLOSE_SESSION'}, executed=False, OPEN->CLOSED_BY_OPERATOR) may declare
# closure. These tests forge each receipt type and assert rejection at every
# layer: receipt construction, chain verification, seal validation, and replay.

import hashlib
import json
import os
import shutil
import unittest

from sentinel_core.canonical import canonical_json
from sentinel_core.errors import ReceiptError, ManifestError, ChainVerificationError
from sentinel_core.receipts import ReceiptChain, build_receipt
from sentinel_core.reason_codes import (
    ALLOW, BLOCK, DRY_RUN, ERROR,
    ALLOW_CREATE_DIRECTORY, ALLOW_SESSION_CLOSE, DRY_RUN_CREATE_DIRECTORY,
    BLOCK_PATH_TRAVERSAL, ERROR_POSTCONDITION_FAILED, CLOSE_SESSION_REQUEST,
    STAGE_RESULT, STAGE_SESSION_CLOSE,
)
from sentinel_core.replay import replay_from_path
from sentinel_core.run_seal import (
    build_run_seal, validate_run_seal, compute_run_seal_hash, RUN_SEAL_FIELD,
)
from sentinel_core.session import SESSION_OPEN, SESSION_CLOSED
from tests.helpers import make_request, new_kernel, temp_root, temp_runs


def _rehash(receipt_dict):
    payload = {k: v for k, v in receipt_dict.items() if k != "canonical_hash"}
    receipt_dict["canonical_hash"] = hashlib.sha256(
        canonical_json(payload).encode("utf-8")).hexdigest()
    return receipt_dict


class TestClosureGrammar(unittest.TestCase):
    def setUp(self):
        self.root = temp_root()
        self.runs = temp_runs()

    def tearDown(self):
        for d in (self.root, self.runs):
            shutil.rmtree(d, ignore_errors=True)

    # ── A genuine close still works end to end ─────────────────────────────
    def test_create_close_replay_passes(self):
        kernel, run_path = new_kernel("ok", self.root, self.runs)
        kernel.process(make_request("R0", "d0"))
        kernel.process(make_request("R1", "d1"))
        close_receipt = kernel.close_session()
        self.assertEqual(close_receipt.reason_code, ALLOW_SESSION_CLOSE)
        self.assertEqual(close_receipt.post_session_state, SESSION_CLOSED)
        self.assertFalse(close_receipt.executed)
        self.assertEqual(close_receipt.request, CLOSE_SESSION_REQUEST)
        ok, report = replay_from_path(run_path)
        self.assertTrue(ok, report)

    # ── Forge each receipt type into a closure ─────────────────────────────
    def _forge_final_to_closed(self, run_path):
        """Edit the final receipt's post_session_state to CLOSED, rehash, and
        build a valid seal over the forged final receipt. Returns the on-disk
        data dict (already written)."""
        with open(run_path, encoding="utf-8") as f:
            data = json.load(f)
        final = data["receipts"][-1]
        final["post_session_state"] = SESSION_CLOSED
        _rehash(final)
        # Build a seal that is itself internally valid over the forged receipt,
        # bypassing build_run_seal's own guard by assembling the seal directly.
        seal = {
            "seal_version": "0.1.0",
            "run_id": data["manifest"]["run_id"],
            "manifest_hash": data["manifest"]["manifest_hash"],
            "receipt_count": len(data["receipts"]),
            "final_receipt_id": final["receipt_id"],
            "final_receipt_hash": final["canonical_hash"],
            "final_session_state": SESSION_CLOSED,
        }
        seal["seal_hash"] = compute_run_seal_hash(seal)
        data[RUN_SEAL_FIELD] = seal
        with open(run_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return data

    def _build_single(self, kind):
        kernel, run_path = new_kernel(f"forge_{kind}", self.root, self.runs)
        if kind == "create":
            kernel.process(make_request("R0", "made"))
        elif kind == "block":
            kernel.process(make_request("R0", "../escape"))  # BLOCK_PATH_TRAVERSAL
        elif kind == "dry_run":
            kernel.process(make_request("R0", "ghost", dry_run=True))
        elif kind == "error":
            # Force an ERROR_POSTCONDITION_FAILED via surgical isdir lie.
            from unittest import mock
            real_isdir = os.path.isdir

            def lying(p):
                return False if os.path.basename(p) == "made" else real_isdir(p)
            with mock.patch("sentinel_core.kernel.os.path.isdir", side_effect=lying):
                kernel.process(make_request("R0", "made"))
        else:
            raise ValueError(kind)
        return run_path

    def _assert_forged_closure_rejected(self, kind, expect_reason):
        run_path = self._build_single(kind)
        # Sanity: the final receipt is the expected non-close type.
        with open(run_path, encoding="utf-8") as f:
            pre = json.load(f)
        self.assertEqual(pre["receipts"][-1]["reason_code"], expect_reason)
        self.assertEqual(pre["receipts"][-1]["post_session_state"], SESSION_OPEN)
        # Forge it into a closure with recomputed hash + valid seal.
        self._forge_final_to_closed(run_path)
        # Replay must FAIL — the forged closure cannot be reconstructed as a
        # valid receipt (construction rejects the grammar violation).
        ok, report = replay_from_path(run_path)
        self.assertFalse(ok, f"Forged {kind} closure passed replay:\n{report}")

    def test_forged_create_closure_fails_replay(self):
        self._assert_forged_closure_rejected("create", ALLOW_CREATE_DIRECTORY)

    def test_forged_block_closure_fails_replay(self):
        self._assert_forged_closure_rejected("block", BLOCK_PATH_TRAVERSAL)

    def test_forged_dry_run_closure_fails_replay(self):
        self._assert_forged_closure_rejected("dry_run", DRY_RUN_CREATE_DIRECTORY)

    def test_forged_error_closure_fails_replay(self):
        self._assert_forged_closure_rejected("error", ERROR_POSTCONDITION_FAILED)

    # ── Receipt-construction-level rejections ──────────────────────────────
    def test_build_create_receipt_with_closed_post_state_raises(self):
        with self.assertRaises(ReceiptError):
            build_receipt(
                receipt_id=0, prior_hash="GENESIS", run_id="x",
                manifest_hash="a" * 64,
                pre_session_state=SESSION_OPEN, post_session_state=SESSION_CLOSED,
                stage=STAGE_RESULT,
                request=make_request("R", "d"),
                decision=ALLOW, reason_code=ALLOW_CREATE_DIRECTORY,
                detail={}, executed=True, intent_receipt_id=None, intent_hash=None)

    def test_close_receipt_with_executed_true_raises(self):
        with self.assertRaises(ReceiptError):
            build_receipt(
                receipt_id=0, prior_hash="GENESIS", run_id="x",
                manifest_hash="a" * 64,
                pre_session_state=SESSION_OPEN, post_session_state=SESSION_CLOSED,
                stage=STAGE_SESSION_CLOSE,
                request=dict(CLOSE_SESSION_REQUEST),
                decision=ALLOW, reason_code=ALLOW_SESSION_CLOSE,
                detail={}, executed=True)  # executed must be False

    def test_close_receipt_with_wrong_request_raises(self):
        with self.assertRaises(ReceiptError):
            build_receipt(
                receipt_id=0, prior_hash="GENESIS", run_id="x",
                manifest_hash="a" * 64,
                pre_session_state=SESSION_OPEN, post_session_state=SESSION_CLOSED,
                stage=STAGE_SESSION_CLOSE,
                request={"action_type": "CREATE_DIRECTORY"},  # wrong request
                decision=ALLOW, reason_code=ALLOW_SESSION_CLOSE,
                detail={}, executed=False)

    def test_close_reason_without_closing_raises(self):
        # ALLOW_SESSION_CLOSE reason but post stays OPEN -> invalid.
        with self.assertRaises(ReceiptError):
            build_receipt(
                receipt_id=0, prior_hash="GENESIS", run_id="x",
                manifest_hash="a" * 64,
                pre_session_state=SESSION_OPEN, post_session_state=SESSION_OPEN,
                stage=STAGE_SESSION_CLOSE,
                request=dict(CLOSE_SESSION_REQUEST),
                decision=ALLOW, reason_code=ALLOW_SESSION_CLOSE,
                detail={}, executed=False)

    # ── Seal-level rejections ──────────────────────────────────────────────
    def test_build_run_seal_rejects_non_close_final(self):
        # A receipts list whose final entry is a CREATE receipt forged to CLOSED
        # must be refused by build_run_seal.
        kernel, run_path = new_kernel("seal_forge", self.root, self.runs)
        kernel.process(make_request("R0", "made"))
        with open(run_path, encoding="utf-8") as f:
            data = json.load(f)
        final = data["receipts"][-1]
        final["post_session_state"] = SESSION_CLOSED
        _rehash(final)
        with self.assertRaises(ManifestError):
            build_run_seal(data["manifest"], data["receipts"])

    def test_validate_run_seal_rejects_non_close_final(self):
        run_path = self._build_single("create")
        self._forge_final_to_closed(run_path)
        with open(run_path, encoding="utf-8") as f:
            data = json.load(f)
        with self.assertRaises(ManifestError):
            validate_run_seal(data, require_closed=True)

    # ── Chain-verification-level rejection (defence in depth) ──────────────
    def test_verify_chain_rejects_forged_closure_via_direct_construction(self):
        # Build a legitimate chain, then attempt to load a forged version.
        kernel, run_path = new_kernel("chain_forge", self.root, self.runs)
        kernel.process(make_request("R0", "made"))
        with open(run_path, encoding="utf-8") as f:
            data = json.load(f)
        final = data["receipts"][-1]
        final["post_session_state"] = SESSION_CLOSED
        _rehash(final)
        # from_receipts_list reconstructs each receipt -> construction grammar
        # check fires before verify_chain is even reached.
        with self.assertRaises((ChainVerificationError, ReceiptError)):
            ReceiptChain.from_receipts_list(data["manifest"]["run_id"], data["receipts"])


if __name__ == "__main__":
    unittest.main()
