# tests/test_path_policy.py
import os
import shutil
import tempfile
import unittest

from sentinel_core.path_policy import evaluate_create_directory
from sentinel_core.reason_codes import (
    BLOCK_EMPTY_PATH, BLOCK_ALLOWED_ROOT_MISSING, BLOCK_ALLOWED_ROOT_NOT_DIRECTORY,
    BLOCK_ABSOLUTE_TARGET_NOT_ALLOWED, BLOCK_PATH_TRAVERSAL, BLOCK_PARENT_MISSING,
    BLOCK_PARENT_NOT_DIRECTORY, BLOCK_SYMLINK_RISK, BLOCK_TARGET_ALREADY_EXISTS,
)


class TestPathPolicy(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="sentinel_policy_")
        self.outside = tempfile.mkdtemp(prefix="sentinel_outside_")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)
        shutil.rmtree(self.outside, ignore_errors=True)

    def test_valid_target_under_root_ok(self):
        res = evaluate_create_directory("demo", self.root)
        self.assertTrue(res.ok)
        self.assertEqual(res.resolved_target, os.path.join(os.path.realpath(self.root), "demo"))

    def test_empty_path_blocked(self):
        res = evaluate_create_directory("", self.root)
        self.assertFalse(res.ok)
        self.assertEqual(res.reason_code, BLOCK_EMPTY_PATH)

    def test_missing_root_blocked(self):
        res = evaluate_create_directory("demo", os.path.join(self.root, "nonexistent_root"))
        self.assertFalse(res.ok)
        self.assertEqual(res.reason_code, BLOCK_ALLOWED_ROOT_MISSING)

    def test_root_not_directory_blocked(self):
        filepath = os.path.join(self.root, "afile")
        with open(filepath, "w") as f:
            f.write("x")
        res = evaluate_create_directory("demo", filepath)
        self.assertFalse(res.ok)
        self.assertEqual(res.reason_code, BLOCK_ALLOWED_ROOT_NOT_DIRECTORY)

    def test_dotdot_traversal_blocked(self):
        res = evaluate_create_directory("../escape", self.root)
        self.assertFalse(res.ok)
        self.assertEqual(res.reason_code, BLOCK_PATH_TRAVERSAL)

    def test_deep_dotdot_traversal_blocked(self):
        res = evaluate_create_directory("a/b/../../../escape", self.root)
        self.assertFalse(res.ok)
        self.assertEqual(res.reason_code, BLOCK_PATH_TRAVERSAL)

    def test_absolute_outside_blocked(self):
        res = evaluate_create_directory(os.path.join(self.outside, "x"), self.root)
        self.assertFalse(res.ok)
        self.assertEqual(res.reason_code, BLOCK_ABSOLUTE_TARGET_NOT_ALLOWED)

    def test_absolute_inside_root_allowed(self):
        target = os.path.join(self.root, "inside_abs")
        res = evaluate_create_directory(target, self.root)
        self.assertTrue(res.ok)

    def test_parent_missing_blocked(self):
        res = evaluate_create_directory("nope/child", self.root)
        self.assertFalse(res.ok)
        self.assertEqual(res.reason_code, BLOCK_PARENT_MISSING)

    def test_parent_not_directory_blocked(self):
        with open(os.path.join(self.root, "afile"), "w") as f:
            f.write("x")
        res = evaluate_create_directory("afile/child", self.root)
        self.assertFalse(res.ok)
        self.assertEqual(res.reason_code, BLOCK_PARENT_NOT_DIRECTORY)

    def test_target_already_exists_blocked(self):
        os.mkdir(os.path.join(self.root, "exists"))
        res = evaluate_create_directory("exists", self.root)
        self.assertFalse(res.ok)
        self.assertEqual(res.reason_code, BLOCK_TARGET_ALREADY_EXISTS)

    def test_symlink_parent_escape_blocked(self):
        # A symlink inside root pointing outside; target under the symlink must
        # be blocked as a symlink risk, not silently followed.
        link = os.path.join(self.root, "link")
        os.symlink(self.outside, link)
        res = evaluate_create_directory("link/child", self.root)
        self.assertFalse(res.ok)
        self.assertEqual(res.reason_code, BLOCK_SYMLINK_RISK)

    def test_symlink_at_target_name_treated_as_exists(self):
        # A pre-placed symlink at the exact target name is treated as existing
        # (lexists), so we never follow it. Fail closed.
        link = os.path.join(self.root, "linktarget")
        os.symlink(self.outside, link)
        res = evaluate_create_directory("linktarget", self.root)
        self.assertFalse(res.ok)
        self.assertEqual(res.reason_code, BLOCK_TARGET_ALREADY_EXISTS)

    def test_no_shell_metacharacters_executed(self):
        # The policy is pure path logic; a target with shell metacharacters is
        # treated as a literal directory name, never interpreted by a shell.
        # Parent is the existing root, target absent -> ALLOW as a literal name.
        res = evaluate_create_directory("x; rm -rf /", self.root)
        self.assertTrue(res.ok)
        # The resolved target is a literal child of root, proving no shell split.
        self.assertTrue(res.resolved_target.startswith(os.path.realpath(self.root) + os.sep))


if __name__ == "__main__":
    unittest.main()
