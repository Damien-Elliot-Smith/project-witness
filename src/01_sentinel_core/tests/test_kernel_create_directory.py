# tests/test_kernel_create_directory.py
import os
import shutil
import unittest

from sentinel_core.errors import SessionClosedError
from sentinel_core.reason_codes import (
    ALLOW, BLOCK, DRY_RUN,
    ALLOW_CREATE_DIRECTORY, DRY_RUN_CREATE_DIRECTORY,
    BLOCK_TARGET_ALREADY_EXISTS, BLOCK_PARENT_MISSING, BLOCK_PARENT_NOT_DIRECTORY,
    BLOCK_PATH_TRAVERSAL, BLOCK_ABSOLUTE_TARGET_NOT_ALLOWED, BLOCK_SYMLINK_RISK,
    BLOCK_UNKNOWN_ACTION, BLOCK_SCHEMA_INVALID, BLOCK_EMPTY_PATH,
)
from tests.helpers import make_request, new_kernel, temp_root, temp_runs


class TestKernelCreateDirectory(unittest.TestCase):
    def setUp(self):
        self.root = temp_root()
        self.runs = temp_runs()
        self.outside = temp_root()
        self.kernel, self.run_path = new_kernel("k_run", self.root, self.runs)

    def tearDown(self):
        for d in (self.root, self.runs, self.outside):
            shutil.rmtree(d, ignore_errors=True)

    def _req(self, rid, target, dry=False, action="CREATE_DIRECTORY"):
        return make_request(rid, target, dry_run=dry, action_type=action)

    def test_valid_create_succeeds_and_executes(self):
        r = self.kernel.process(self._req("R1", "demo"))
        self.assertEqual(r.decision, ALLOW)
        self.assertEqual(r.reason_code, ALLOW_CREATE_DIRECTORY)
        self.assertTrue(r.executed)
        self.assertTrue(os.path.isdir(os.path.join(self.root, "demo")))

    def test_nested_create_after_parent_created(self):
        self.kernel.process(self._req("R1", "demo"))
        r = self.kernel.process(self._req("R2", "demo/output"))
        self.assertEqual(r.decision, ALLOW)
        self.assertTrue(os.path.isdir(os.path.join(self.root, "demo", "output")))

    def test_dry_run_does_not_create(self):
        r = self.kernel.process(self._req("R1", "ghost", dry=True))
        self.assertEqual(r.decision, DRY_RUN)
        self.assertEqual(r.reason_code, DRY_RUN_CREATE_DIRECTORY)
        self.assertFalse(r.executed)
        self.assertFalse(os.path.exists(os.path.join(self.root, "ghost")))

    def test_target_already_exists_blocks(self):
        os.mkdir(os.path.join(self.root, "exists"))
        r = self.kernel.process(self._req("R1", "exists"))
        self.assertEqual(r.decision, BLOCK)
        self.assertEqual(r.reason_code, BLOCK_TARGET_ALREADY_EXISTS)
        self.assertFalse(r.executed)

    def test_parent_missing_blocks(self):
        r = self.kernel.process(self._req("R1", "nope/child"))
        self.assertEqual(r.reason_code, BLOCK_PARENT_MISSING)

    def test_parent_not_directory_blocks(self):
        with open(os.path.join(self.root, "afile"), "w") as f:
            f.write("x")
        r = self.kernel.process(self._req("R1", "afile/child"))
        self.assertEqual(r.reason_code, BLOCK_PARENT_NOT_DIRECTORY)

    def test_traversal_blocks(self):
        r = self.kernel.process(self._req("R1", "../escape"))
        self.assertEqual(r.reason_code, BLOCK_PATH_TRAVERSAL)

    def test_absolute_outside_blocks(self):
        r = self.kernel.process(self._req("R1", os.path.join(self.outside, "x")))
        self.assertEqual(r.reason_code, BLOCK_ABSOLUTE_TARGET_NOT_ALLOWED)

    def test_symlink_escape_blocks(self):
        os.symlink(self.outside, os.path.join(self.root, "link"))
        r = self.kernel.process(self._req("R1", "link/child"))
        self.assertEqual(r.reason_code, BLOCK_SYMLINK_RISK)

    def test_empty_path_blocks(self):
        r = self.kernel.process(self._req("R1", ""))
        self.assertEqual(r.reason_code, BLOCK_EMPTY_PATH)

    def test_unknown_action_blocks(self):
        r = self.kernel.process(self._req("R1", "x", action="DELETE_FILE"))
        self.assertEqual(r.reason_code, BLOCK_UNKNOWN_ACTION)

    def test_malformed_schema_blocks(self):
        r = self.kernel.process({"not": "a valid request"})
        self.assertEqual(r.reason_code, BLOCK_SCHEMA_INVALID)

    def test_natural_language_blocks(self):
        r = self.kernel.process("make me a folder somewhere")
        self.assertEqual(r.reason_code, BLOCK_SCHEMA_INVALID)

    def test_every_request_produces_receipt(self):
        # v0.2: an ALLOW produces an INTENT+RESULT pair (2); a BLOCK and a
        # DRY_RUN each produce one self-contained RESULT. So allow+block+dry
        # appends 2+1+1 = 4 receipts.
        before = self.kernel._journal.chain.next_id()
        r_allow = self.kernel.process(self._req("A", "d1"))
        r_block = self.kernel.process(self._req("B", "exists/child"))  # block (parent missing)
        r_dry = self.kernel.process(self._req("C", "d2", dry=True))
        after = self.kernel._journal.chain.next_id()
        self.assertEqual(after - before, 4)
        # The returned receipts are the RESULT receipts; the ALLOW one resolves
        # an INTENT, the others are self-contained.
        self.assertEqual(r_allow.stage, "RESULT")
        self.assertEqual(r_allow.intent_receipt_id, 0)
        self.assertIsNone(r_block.intent_receipt_id)
        self.assertIsNone(r_dry.intent_receipt_id)

    def test_closed_session_refuses(self):
        self.kernel.process(self._req("A", "d1"))
        self.kernel.close_session()
        with self.assertRaises(SessionClosedError):
            self.kernel.process(self._req("B", "d2"))

    def test_close_emits_final_receipt(self):
        self.kernel.process(self._req("A", "d1"))
        r = self.kernel.close_session()
        self.assertEqual(r.decision, ALLOW)
        self.assertFalse(r.executed)
        self.assertEqual(self.kernel.session_state, "CLOSED_BY_OPERATOR")


if __name__ == "__main__":
    unittest.main()
