# tests/test_kernel_create_text_file.py
# Move 62 red/blue suite for the second Sentinel action, CREATE_TEXT_FILE.
#
# One PASS (happy) case and the full set of hostile FAIL/BLOCK cases required by
# the Move 62 specification, plus dry-run parity, the content-hash postcondition
# guard, a no-crash check for unrepresentable (lone-surrogate) content, and a
# strict-replay check over a run that mixes ALLOW / BLOCK / DRY_RUN receipts.
import hashlib
import os
import shutil
import unittest

import sentinel_core.kernel as kmod
from sentinel_core.action_schema import ACTION_SCHEMA_VERSION, ACTION_CREATE_TEXT_FILE
from sentinel_core.reason_codes import (
    ALLOW, BLOCK, DRY_RUN, ERROR,
    ALLOW_CREATE_TEXT_FILE, DRY_RUN_CREATE_TEXT_FILE,
    BLOCK_TARGET_ALREADY_EXISTS, BLOCK_PARENT_MISSING, BLOCK_PATH_TRAVERSAL,
    BLOCK_ABSOLUTE_TARGET_NOT_ALLOWED, BLOCK_SYMLINK_RISK,
    BLOCK_OUTSIDE_ALLOWED_ROOT, BLOCK_SCHEMA_INVALID,
    ERROR_POSTCONDITION_FAILED,
)
from sentinel_core.replay import replay_from_path, VERDICT_PASS_STRICT
from tests.helpers import new_kernel, temp_root, temp_runs


def make_text_request(request_id, target_path, content="hello\n",
                      allowed_path_prefix=".", dry_run=False,
                      schema_version=ACTION_SCHEMA_VERSION):
    return {
        "request_id": request_id,
        "action_type": ACTION_CREATE_TEXT_FILE,
        "target_path": target_path,
        "content": content,
        "allowed_path_prefix": allowed_path_prefix,
        "dry_run": dry_run,
        "preconditions": ["parent_directory_exists", "path_absent", "path_inside_allowed_prefix"],
        "postconditions": ["file_exists", "file_content_hash_matches", "file_is_utf8_text"],
        "schema_version": schema_version,
    }


class TestKernelCreateTextFile(unittest.TestCase):
    def setUp(self):
        self.root = temp_root()
        self.runs = temp_runs()
        self.outside = temp_root()
        self.kernel, self.run_path = new_kernel("tf_run", self.root, self.runs)
        os.mkdir(os.path.join(self.root, "docs"))

    def tearDown(self):
        for d in (self.root, self.runs, self.outside):
            shutil.rmtree(d, ignore_errors=True)

    # ── PASS ────────────────────────────────────────────────────────────────
    def test_pass_creates_utf8_file_inside_prefix(self):
        content = "hello world\n"
        r = self.kernel.process(make_text_request("R1", "docs/notes.txt", content, "docs"))
        self.assertEqual(r.decision, ALLOW)
        self.assertEqual(r.reason_code, ALLOW_CREATE_TEXT_FILE)
        self.assertTrue(r.executed)
        p = os.path.join(self.root, "docs", "notes.txt")
        self.assertTrue(os.path.isfile(p))
        self.assertFalse(os.path.islink(p))
        with open(p, "rb") as f:
            on_disk = f.read()
        self.assertEqual(on_disk.decode("utf-8"), content)
        # The created file hash is recorded in the receipt.
        self.assertEqual(r.detail["content_sha256"],
                         hashlib.sha256(content.encode("utf-8")).hexdigest())

    def test_dry_run_does_not_create(self):
        r = self.kernel.process(make_text_request("R1", "docs/ghost.txt", "x\n", "docs", dry_run=True))
        self.assertEqual(r.decision, DRY_RUN)
        self.assertEqual(r.reason_code, DRY_RUN_CREATE_TEXT_FILE)
        self.assertFalse(r.executed)
        self.assertFalse(os.path.exists(os.path.join(self.root, "docs", "ghost.txt")))

    # ── FAIL / BLOCK ──────────────────────────────────────────────────────────
    def test_block_target_already_exists(self):
        self.kernel.process(make_text_request("R1", "docs/a.txt", "one\n", "docs"))
        r = self.kernel.process(make_text_request("R2", "docs/a.txt", "two\n", "docs"))
        self.assertEqual(r.decision, BLOCK)
        self.assertEqual(r.reason_code, BLOCK_TARGET_ALREADY_EXISTS)
        # No overwrite: the original content is intact.
        with open(os.path.join(self.root, "docs", "a.txt")) as f:
            self.assertEqual(f.read(), "one\n")

    def test_block_parent_missing(self):
        r = self.kernel.process(make_text_request("R1", "nope/child.txt", "x\n", "."))
        self.assertEqual(r.decision, BLOCK)
        self.assertEqual(r.reason_code, BLOCK_PARENT_MISSING)

    def test_block_outside_allowed_prefix(self):
        # Target is inside the root but outside the narrower declared prefix.
        r = self.kernel.process(make_text_request("R1", "top.txt", "x\n", "docs"))
        self.assertEqual(r.decision, BLOCK)
        self.assertEqual(r.reason_code, BLOCK_OUTSIDE_ALLOWED_ROOT)

    def test_block_dotdot_traversal(self):
        r = self.kernel.process(make_text_request("R1", "../escape.txt", "x\n", "."))
        self.assertEqual(r.decision, BLOCK)
        self.assertEqual(r.reason_code, BLOCK_PATH_TRAVERSAL)

    def test_block_absolute_path_outside(self):
        r = self.kernel.process(make_text_request("R1", "/etc/pwn.txt", "x\n", "."))
        self.assertEqual(r.decision, BLOCK)
        self.assertEqual(r.reason_code, BLOCK_ABSOLUTE_TARGET_NOT_ALLOWED)

    def test_block_symlink_escape(self):
        os.symlink(self.outside, os.path.join(self.root, "link"))
        r = self.kernel.process(make_text_request("R1", "link/evil.txt", "x\n", "."))
        self.assertEqual(r.decision, BLOCK)
        self.assertEqual(r.reason_code, BLOCK_SYMLINK_RISK)
        self.assertFalse(os.path.exists(os.path.join(self.outside, "evil.txt")))

    def test_block_binary_content_nul(self):
        r = self.kernel.process(make_text_request("R1", "b.txt", "a\x00b", "."))
        self.assertEqual(r.decision, BLOCK)
        self.assertEqual(r.reason_code, BLOCK_SCHEMA_INVALID)
        self.assertFalse(os.path.exists(os.path.join(self.root, "b.txt")))

    def test_block_binary_content_non_string(self):
        req = make_text_request("R1", "b.txt", "x\n", ".")
        req["content"] = [1, 2, 3]  # not text
        r = self.kernel.process(req)
        self.assertEqual(r.decision, BLOCK)
        self.assertEqual(r.reason_code, BLOCK_SCHEMA_INVALID)

    def test_block_non_utf8_surrogate_content_no_crash(self):
        # A lone surrogate is not encodable UTF-8; must fail closed, not crash.
        r = self.kernel.process(make_text_request("R1", "s.txt", "x\udc80", "."))
        self.assertEqual(r.decision, BLOCK)
        self.assertEqual(r.reason_code, BLOCK_SCHEMA_INVALID)
        self.assertFalse(os.path.exists(os.path.join(self.root, "s.txt")))

    def test_block_missing_content_field(self):
        req = make_text_request("R1", "m.txt", "x\n", ".")
        del req["content"]
        r = self.kernel.process(req)
        self.assertEqual(r.decision, BLOCK)
        self.assertEqual(r.reason_code, BLOCK_SCHEMA_INVALID)

    def test_block_missing_allowed_path_prefix_field(self):
        req = make_text_request("R1", "m.txt", "x\n", ".")
        del req["allowed_path_prefix"]
        r = self.kernel.process(req)
        self.assertEqual(r.decision, BLOCK)
        self.assertEqual(r.reason_code, BLOCK_SCHEMA_INVALID)

    def test_block_absolute_allowed_path_prefix(self):
        # A request may not name an absolute prefix (would repoint the boundary).
        r = self.kernel.process(make_text_request("R1", "x.txt", "x\n", self.root))
        self.assertEqual(r.decision, BLOCK)
        self.assertEqual(r.reason_code, BLOCK_OUTSIDE_ALLOWED_ROOT)

    def test_error_content_hash_mismatch_after_write(self):
        # Inject a writer that persists different bytes than requested. The
        # post-write hash check must catch it and record a controlled ERROR.
        original = kmod.execute_create_text_file
        kmod.execute_create_text_file = lambda tgt, data: original(tgt, data + b"TAMPER")
        try:
            r = self.kernel.process(make_text_request("R1", "hm.txt", "genuine\n", "."))
        finally:
            kmod.execute_create_text_file = original
        self.assertEqual(r.decision, ERROR)
        self.assertEqual(r.reason_code, ERROR_POSTCONDITION_FAILED)
        self.assertFalse(r.executed)

    def test_mixed_run_replays_strict(self):
        k, run_path = new_kernel("mix", self.root, self.runs)
        os.mkdir(os.path.join(self.root, "d2"))
        k.process(make_text_request("A", "d2/a.txt", "hello\n", "d2"))       # ALLOW
        k.process(make_text_request("B", "d2/a.txt", "again\n", "d2"))       # exists
        k.process(make_text_request("C", "d2/g.txt", "x\n", "d2", dry_run=True))  # dry
        k.process(make_text_request("D", "../e.txt", "x\n", "."))            # traversal
        k.process(make_text_request("E", "nd/c.txt", "x\n", "."))           # parent missing
        k.process(make_text_request("F", "b.txt", "a\x00b", "."))           # binary NUL
        k.close_session()
        result = replay_from_path(run_path)
        self.assertTrue(result.ok, msg=result.report)
        self.assertEqual(result.verdict, VERDICT_PASS_STRICT)


if __name__ == "__main__":
    unittest.main()
