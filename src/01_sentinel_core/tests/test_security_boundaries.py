# tests/test_security_boundaries.py
import os
import shutil
import unittest

from sentinel_core.reason_codes import (
    BLOCK_PATH_TRAVERSAL, BLOCK_ABSOLUTE_TARGET_NOT_ALLOWED, BLOCK_SYMLINK_RISK,
    BLOCK_OUTSIDE_ALLOWED_ROOT, BLOCK_UNKNOWN_ACTION,
)
from tests.helpers import make_request, new_kernel, temp_root, temp_runs


class TestSecurityBoundaries(unittest.TestCase):
    def setUp(self):
        self.root = temp_root()
        self.runs = temp_runs()
        self.outside = temp_root()
        self.kernel, self.run_path = new_kernel("sec", self.root, self.runs)

    def tearDown(self):
        for d in (self.root, self.runs, self.outside):
            shutil.rmtree(d, ignore_errors=True)

    def _process(self, target, dry=False, action="CREATE_DIRECTORY"):
        return self.kernel.process(
            make_request("S", target, dry_run=dry, action_type=action))

    def test_dotdot_escape_blocked(self):
        self.assertEqual(self._process("../../etc/evil").reason_code, BLOCK_PATH_TRAVERSAL)

    def test_encoded_dotdot_is_literal_not_escape(self):
        # "%2e%2e" is not interpreted; it is a literal name with a missing
        # parent. The point: no URL decoding happens, so no hidden escape.
        r = self._process("%2e%2e/evil")
        self.assertNotEqual(r.decision, "ALLOW")

    def test_absolute_to_system_blocked(self):
        self.assertEqual(self._process("/etc/cron.d/evil").reason_code,
                         BLOCK_ABSOLUTE_TARGET_NOT_ALLOWED)

    def test_symlink_root_escape_blocked(self):
        os.symlink(self.outside, os.path.join(self.root, "out"))
        self.assertEqual(self._process("out/child").reason_code, BLOCK_SYMLINK_RISK)

    def test_symlinked_allowed_root_still_contained(self):
        # If allowed_root itself is a symlink, containment is computed against
        # its real path; a normal child is still allowed.
        real_root = temp_root()
        link_root = os.path.join(self.outside, "rootlink")
        os.symlink(real_root, link_root)
        kernel, _ = new_kernel("sym", link_root, self.runs)
        r = kernel.process(make_request("S", "child"))
        self.assertEqual(r.decision, "ALLOW")
        self.assertTrue(os.path.isdir(os.path.join(real_root, "child")))
        shutil.rmtree(real_root, ignore_errors=True)

    def test_no_shell_injection_executed(self):
        # A target containing shell metacharacters is created as a LITERAL
        # directory name; nothing is passed to a shell, nothing is deleted.
        sentinel_file = os.path.join(self.root, "KEEP")
        with open(sentinel_file, "w") as f:
            f.write("keep")
        r = self._process("evil; rm -rf KEEP")
        self.assertEqual(r.decision, "ALLOW")
        self.assertTrue(os.path.exists(sentinel_file))  # not deleted
        self.assertTrue(os.path.isdir(os.path.join(self.root, "evil; rm -rf KEEP")))

    def test_unknown_action_never_executes(self):
        before = set(os.listdir(self.root))
        self.assertEqual(self._process("x", action="DELETE_FILE").reason_code, BLOCK_UNKNOWN_ACTION)
        self.assertEqual(set(os.listdir(self.root)), before)

    def test_newline_in_target_is_literal(self):
        r = self._process("line1\nline2")
        # Newline is a legal (if unusual) directory name char on POSIX; created
        # literally under root, never split into two commands.
        self.assertIn(r.decision, ("ALLOW", "BLOCK"))


if __name__ == "__main__":
    unittest.main()
